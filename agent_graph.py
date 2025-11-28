"""Multi-agent graph for routing and handling financial advice requests."""

from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, Annotated, Literal
import operator
from tools.income_tool import income_tool
from tools.fraud_tool import fraud_tool
from tools.stock_tool import stock_tool
from database import db_conn, db_manager
import os
import config

# Define agent state
class AgentState(TypedDict):
    telegram_id: int
    message: str
    intent: str
    response: str
    tool_calls: Annotated[list, operator.add]

# Initialize Claude
llm = ChatAnthropic(
    model="claude-3-opus-20240229",
    anthropic_api_key=config.ANTHROPIC_API_KEY,
    temperature=0.7
)

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are KaroBuddy, a friendly financial coach for people with irregular incomes in India.

You help with:
- Income tracking and savings recommendations
- Fraud/scam detection for investment opportunities
- Stock analysis for Indian markets
- General financial advice

Be concise (2-3 sentences max), encouraging, and use emojis sparingly.
Always prioritize user safety and financial security.

Context: User #{telegram_id} is asking about {intent}"""),
    ("human", "{message}"),
])

# Define workflow nodes
def route_intent(state: AgentState) -> AgentState:
    """Determine user intent from message."""
    message = state['message'].lower()
    
    # Check for specific intents
    if any(word in message for word in ['earned', 'got paid', 'income', 'salary', 'received money']):
        state['intent'] = 'income'
    elif any(word in message for word in ['scam', 'fraud', 'guarantee', 'double', 'risk-free', 'suspicious', 'ponzi']):
        state['intent'] = 'fraud'
    elif any(word in message for word in ['stock', 'share', 'equity', 'nse', 'bse']):
        state['intent'] = 'stock'
    elif any(word in message for word in ['dashboard', 'summary', 'overview', 'report']):
        state['intent'] = 'dashboard'
    elif any(word in message for word in ['expense', 'spent', 'paid for', 'bought']):
        state['intent'] = 'expense'
    else:
        state['intent'] = 'general'
    
    return state

def call_agent(state: AgentState) -> AgentState:
    """Call appropriate tool based on intent."""
    telegram_id = state['telegram_id']
    message = state['message']
    intent = state['intent']
    
    try:
        if intent == 'income':
            result = income_tool._run(telegram_id, message)
            state['response'] = result
        
        elif intent == 'fraud':
            result = fraud_tool._run(message)
            state['response'] = result
        
        elif intent == 'stock':
            # Extract ticker from message
            import re
            # Look for stock symbols (2-5 uppercase letters)
            tickers = re.findall(r'\b([A-Z]{2,5})\b', message.upper())
            if tickers:
                result = stock_tool._run(tickers[0])
                state['response'] = result
            else:
                state['response'] = """Please provide a stock ticker symbol.

Examples:
• RELIANCE.NS (Reliance Industries)
• TCS.NS (Tata Consultancy Services)
• INFY.NS (Infosys)
• HDFCBANK.NS (HDFC Bank)

Just say: "Check RELIANCE" or "Analyze TCS stock" """
        
        elif intent == 'expense':
            # Extract amount from message
            import re
            amounts = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', message.replace(',', ''))
            if amounts:
                amount = float(amounts[0])
                # Log expense
                c = db_conn.cursor()
                from datetime import datetime
                c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                             VALUES (?, ?, 'expense', 'General', ?, ?)""",
                          (telegram_id, amount, message, datetime.now().date().isoformat()))
                db_conn.commit()
                
                state['response'] = f"""✅ Logged ₹{amount:,.0f} as expense!

💡 Tip: Track your expenses regularly to understand your spending patterns.

Use /dashboard to see your financial overview."""
            else:
                state['response'] = "Please specify the amount. Example: 'Spent 2500 on groceries'"
        
        elif intent == 'dashboard':
            # Generate dashboard
            c = db_conn.cursor()
            c.execute("""SELECT SUM(amount) FROM transactions 
                         WHERE telegram_id=? AND type='income' 
                         AND date > date('now', '-30 days')""", (telegram_id,))
            income = c.fetchone()[0] or 0
            
            c.execute("""SELECT SUM(amount) FROM transactions 
                         WHERE telegram_id=? AND type='expense' 
                         AND date > date('now', '-30 days')""", (telegram_id,))
            expense = c.fetchone()[0] or 0
            
            savings = income - expense
            rate = (savings/income*100) if income > 0 else 0
            
            # Get transaction counts
            c.execute("""SELECT COUNT(*) FROM transactions 
                         WHERE telegram_id=? AND type='income' 
                         AND date > date('now', '-30 days')""", (telegram_id,))
            income_count = c.fetchone()[0]
            
            c.execute("""SELECT COUNT(*) FROM transactions 
                         WHERE telegram_id=? AND type='expense' 
                         AND date > date('now', '-30 days')""", (telegram_id,))
            expense_count = c.fetchone()[0]
            
            state['response'] = f"""📊 **Your Financial Dashboard** (Last 30 Days)

💰 Income: ₹{income:,.0f} ({income_count} entries)
💸 Expenses: ₹{expense:,.0f} ({expense_count} entries)
💵 Net Savings: ₹{savings:,.0f}

📈 Savings Rate: {rate:.1f}%
{'🔥' * min(int(rate/20), 5)}

{
    "🎉 Excellent! You're saving well!" if rate > 40 
    else "💪 Good progress! Keep building that buffer!" if rate > 20
    else "⚠️ Try to increase your savings rate for financial security."
}

💡 Tip: Aim for at least 20% savings rate with irregular income."""
        
        else:
            # General conversation with Claude
            formatted_prompt = prompt.format_messages(
                telegram_id=telegram_id,
                intent=intent,
                message=message
            )
            response = llm.invoke(formatted_prompt)
            state['response'] = response.content
        
        # Save conversation to database
        db_manager.save_conversation(telegram_id, message, state['response'], intent)
    
    except Exception as e:
        state['response'] = f"⚠️ Oops! Something went wrong: {str(e)}\n\nPlease try again or contact support."
        print(f"Error in call_agent: {e}")
    
    return state

# Build graph
workflow = StateGraph(AgentState)

workflow.add_node("route_intent", route_intent)
workflow.add_node("call_agent", call_agent)

workflow.set_entry_point("route_intent")
workflow.add_edge("route_intent", "call_agent")
workflow.add_edge("call_agent", END)

# Compile graph
graph = workflow.compile()

# Runner function
async def run_agent_graph(telegram_id: int, message: str, intent: str = None) -> str:
    """Execute the agent graph."""
    initial_state = {
        "telegram_id": telegram_id,
        "message": message,
        "intent": intent or "general",
        "response": "",
        "tool_calls": []
    }
    
    try:
        result = graph.invoke(initial_state)
        return result['response']
    except Exception as e:
        print(f"Error in run_agent_graph: {e}")
        return f"⚠️ Sorry, I encountered an error: {str(e)}\n\nPlease try again!"