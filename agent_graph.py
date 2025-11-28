from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict, Annotated, Literal
import operator
from tools.income_tool import income_tool
from tools.fraud_tool import fraud_tool
from tools.stock_tool import stock_tool
from tools.goal_tool import goal_tool
from tools.risk_tool import risk_tool
from tools.investment_intelligence_tool import investment_intelligence_tool
from database import db_conn, db_manager
import os
import config
import re

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
- Comprehensive stock and mutual fund analysis
- Goal-based financial planning
- Risk-based investment recommendations
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
    elif any(word in message for word in ['goal', 'target', 'save for', 'saving for', 'allocate']):
        state['intent'] = 'goal'
    elif 'is' in message and 'good' in message and any(word in message for word in ['stock', 'share', 'company']):
        state['intent'] = 'stock_analysis'
    elif 'is' in message and 'good' in message and any(word in message for word in ['mutual fund', 'mf', 'fund']):
        state['intent'] = 'mutual_fund_analysis'
    elif any(word in message for word in ['stock', 'share', 'equity', 'nse', 'bse']) and 'check' in message:
        state['intent'] = 'stock'
    elif any(word in message for word in ['suggest', 'recommend', 'investment', 'where to invest', 'should i invest']):
        state['intent'] = 'investment_recommendation'
    elif any(word in message for word in ['dashboard', 'summary', 'overview', 'report']):
        state['intent'] = 'dashboard'
    elif any(word in message for word in ['expense', 'spent', 'paid for', 'bought']):
        state['intent'] = 'expense'
    elif any(word in message for word in ['risk', 'risk profile', 'risk level']):
        state['intent'] = 'risk_profile'
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
        
        elif intent == 'goal':
            # Parse goal-related commands
            message_lower = message.lower()
            
            if 'create' in message_lower or 'new' in message_lower or 'set' in message_lower:
                # Extract goal name and amount
                # Pattern: "create goal NAME with target AMOUNT"
                match = re.search(r'(?:create|new|set)\s+goal\s+(.+?)\s+(?:with\s+)?(?:target|amount|of)?\s*₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', message, re.IGNORECASE)
                if match:
                    goal_name = match.group(1).strip()
                    target_amount = float(match.group(2).replace(',', ''))
                    result = goal_tool._run(telegram_id, 'create', goal_name=goal_name, target_amount=target_amount)
                else:
                    result = "Please specify goal name and target amount.\n\nExample: 'Create goal Emergency Fund with target 100000'"
            
            elif 'allocate' in message_lower or 'add' in message_lower:
                # Pattern: "allocate AMOUNT to GOAL"
                match = re.search(r'(?:allocate|add)\s+₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s+(?:to|for)\s+(.+)', message, re.IGNORECASE)
                if match:
                    amount = float(match.group(1).replace(',', ''))
                    goal_name = match.group(2).strip()
                    result = goal_tool._run(telegram_id, 'allocate', goal_name=goal_name, allocation_amount=amount)
                else:
                    result = "Please specify amount and goal name.\n\nExample: 'Allocate 5000 to Emergency Fund'"
            
            elif 'delete' in message_lower or 'remove' in message_lower:
                match = re.search(r'(?:delete|remove)\s+(?:goal\s+)?(.+)', message, re.IGNORECASE)
                if match:
                    goal_name = match.group(1).strip()
                    result = goal_tool._run(telegram_id, 'delete', goal_name=goal_name)
                else:
                    result = "Please specify goal name to delete.\n\nExample: 'Delete goal Emergency Fund'"
            
            else:
                # List goals
                result = goal_tool._run(telegram_id, 'list')
            
            state['response'] = result
        
        elif intent == 'stock_analysis':
            # Comprehensive stock analysis
            tickers = re.findall(r'\b([A-Z]{2,10})\b', message.upper())
            if tickers:
                result = investment_intelligence_tool._run(tickers[0], 'stock_analysis')
            else:
                result = "Please specify a stock ticker.\n\nExample: 'Is RELIANCE a good stock?'"
            state['response'] = result
        
        elif intent == 'mutual_fund_analysis':
            # Extract fund name
            match = re.search(r'is\s+(.+?)\s+(?:a\s+)?good', message, re.IGNORECASE)
            if match:
                fund_name = match.group(1).strip()
                result = investment_intelligence_tool._run(fund_name, 'mutual_fund_analysis')
            else:
                result = "Please specify the mutual fund name.\n\nExample: 'Is HDFC Top 100 a good mutual fund?'"
            state['response'] = result
        
        elif intent == 'stock':
            # Quick stock check
            tickers = re.findall(r'\b([A-Z]{2,10})\b', message.upper())
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
        
        elif intent == 'investment_recommendation':
            # Ask for risk profile if not set
            c = db_conn.cursor()
            c.execute("SELECT risk_profile FROM users WHERE telegram_id=?", (telegram_id,))
            user = c.fetchone()
            
            # Check if user specified risk in message
            risk_level = None
            if 'low risk' in message.lower() or 'conservative' in message.lower() or 'safe' in message.lower():
                risk_level = 'low'
            elif 'high risk' in message.lower() or 'aggressive' in message.lower():
                risk_level = 'high'
            elif 'medium risk' in message.lower() or 'moderate' in message.lower() or 'balanced' in message.lower():
                risk_level = 'medium'
            elif user and user[0]:
                risk_level = user[0]
            
            if not risk_level:
                state['response'] = """🎯 Investment Recommendations

To provide personalized recommendations, I need to know your risk tolerance:

Choose your risk level:

🛡️ Low Risk - Safety first, minimal volatility
   • Best for: Conservative investors
   • Returns: 6-10% annually
   • Suitable if you can't handle market swings

⚖️ Medium Risk - Balanced approach
   • Best for: Most investors
   • Returns: 10-15% annually
   • Suitable for 3-5 year goals

🚀 High Risk - Maximum growth potential
   • Best for: Aggressive investors
   • Returns: 15-25% annually
   • Suitable if you can handle volatility

Reply with: "I want low/medium/high risk investments" """
            else:
                # Determine investment type
                if 'stock' in message.lower():
                    result = risk_tool._run(risk_level, 'stock')
                elif 'mutual fund' in message.lower() or 'mf' in message.lower():
                    result = risk_tool._run(risk_level, 'mutual_fund')
                else:
                    # Ask what they want
                    risk_upper = risk_level.upper()
                    result = f"""You have a {risk_upper} RISK profile.

What would you like recommendations for?

📊 Stocks - Direct equity investment
💼 Mutual Funds - Professionally managed funds

Reply: "Suggest stocks" or "Suggest mutual funds" """
                
                state['response'] = result
        
        elif intent == 'risk_profile':
            # Set risk profile
            if 'low' in message.lower() or 'conservative' in message.lower():
                risk_level = 'low'
            elif 'high' in message.lower() or 'aggressive' in message.lower():
                risk_level = 'high'
            else:
                risk_level = 'medium'
            
            c = db_conn.cursor()
            c.execute("UPDATE users SET risk_profile=? WHERE telegram_id=?", (risk_level, telegram_id))
            db_conn.commit()
            
            risk_upper = risk_level.upper()
            state['response'] = f"""✅ Risk profile updated to {risk_upper}!

Now I can provide personalized investment recommendations.

Try asking:
• "Suggest some stocks"
• "Recommend mutual funds"
• "Where should I invest?" """
        
        elif intent == 'expense':
            # Extract amount from message
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
            
            c.execute("""SELECT SUM(amount) FROM transactions 
                         WHERE telegram_id=? AND type='goal_allocation' 
                         AND date > date('now', '-30 days')""", (telegram_id,))
            goal_allocation = c.fetchone()[0] or 0
            
            c.execute("""SELECT COUNT(*), SUM(current_amount), SUM(target_amount) 
                         FROM goals WHERE telegram_id=? AND status='active'""", (telegram_id,))
            goal_stats = c.fetchone()
            active_goals = goal_stats[0] or 0
            goal_saved = goal_stats[1] or 0
            goal_target = goal_stats[2] or 0
            
            true_expense = expense
            savings = income - true_expense - goal_allocation
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
            
            fire_emoji = '🔥' * min(int(rate/20), 5)
            
            if rate > 40:
                status_msg = "🎉 Excellent! You're saving well!"
            elif rate > 20:
                status_msg = "💪 Good progress! Keep building that buffer!"
            else:
                status_msg = "⚠️ Try to increase your savings rate for financial security."
            
            goal_progress = f"📊 {(goal_saved/goal_target*100):.1f}% complete" if goal_target > 0 else ""
            
            state['response'] = f"""📊 Your Financial Dashboard (Last 30 Days)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Income: ₹{income:,.0f} ({income_count} entries)
💸 Expenses: ₹{true_expense:,.0f} ({expense_count} entries)
🎯 Goal Allocations: ₹{goal_allocation:,.0f}
💵 Net Savings: ₹{savings:,.0f}

📈 Savings Rate: {rate:.1f}%
{fire_emoji}

{status_msg}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Financial Goals: {active_goals} active
💰 Goal Progress: ₹{goal_saved:,.0f} / ₹{goal_target:,.0f}
{goal_progress}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Quick Actions:
• "Show my goals" - View goal details
• "Create goal [name] with target [amount]"
• "Suggest investments" - Get recommendations
• "Check [STOCK] stock" - Analyze stocks"""
        
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
        import traceback
        traceback.print_exc()
    
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
        import traceback
        traceback.print_exc()
        return f"⚠️ Sorry, I encountered an error: {str(e)}\n\nPlease try again!"