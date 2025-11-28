from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import db_conn
import re
from datetime import datetime

class IncomeInput(BaseModel):
    telegram_id: int = Field(description="User's telegram ID")
    message: str = Field(description="User's message about income")

class IncomeAnalyzerTool(BaseTool):
    name: str = "income_analyzer"
    description: str = "Analyzes income and suggests how much to save based on volatility"
    args_schema: type[BaseModel] = IncomeInput
    
    def _run(self, telegram_id: int, message: str) -> str:
        """Analyze income and provide savings recommendations."""
        # Extract amount from message
        amounts = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', message.replace(',', ''))
        if not amounts:
            return "I couldn't find an amount. Please tell me like: 'I earned ₹25000' or 'Got paid 25000'"
        
        amount = float(amounts[0])
        
        # Get last 30 days income
        c = db_conn.cursor()
        c.execute("""SELECT amount FROM transactions 
                     WHERE telegram_id=? AND type='income' 
                     AND date > date('now', '-30 days')""", (telegram_id,))
        past_incomes = [row[0] for row in c.fetchall()]
        
        # Log this income
        c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, date)
                     VALUES (?, ?, 'income', 'Freelance', ?)""",
                  (telegram_id, amount, datetime.now().date().isoformat()))
        db_conn.commit()
        
        # Calculate volatility and recommendation
        if len(past_incomes) < 2:
            save_percent = 50
            reasoning = "Save 50% until I learn your income pattern 📊"
            volatility_text = "Building your profile..."
        else:
            past_incomes.append(amount)
            avg = sum(past_incomes) / len(past_incomes)
            volatility = (max(past_incomes) - min(past_incomes)) / avg if avg > 0 else 0
            
            if volatility > 0.5:
                save_percent = 70
                reasoning = f"⚠️ High income volatility ({volatility:.1%}). Save 70% (₹{amount*0.7:.0f})"
                volatility_text = "High volatility detected"
            elif volatility > 0.3:
                save_percent = 60
                reasoning = f"💡 Moderate volatility ({volatility:.1%}). Save 60% (₹{amount*0.6:.0f})"
                volatility_text = "Moderate income variation"
            else:
                save_percent = 40
                reasoning = f"✅ Stable income! Save 40% (₹{amount*0.4:.0f})"
                volatility_text = "Stable income pattern"
        
        safe_spending = amount * (1 - save_percent/100)
        savings_amount = amount * save_percent / 100
        
        # Calculate 30-day average
        if past_incomes:
            avg_income = sum(past_incomes) / len(past_incomes)
        else:
            avg_income = amount
        
        return f"""✅ Logged ₹{amount:,.0f} as income!

{reasoning}

💵 Safe to spend: ₹{safe_spending:,.0f}
💰 Should save: ₹{savings_amount:,.0f}

📊 Your 30-day average: ₹{avg_income:,.0f}
📈 Income entries: {len(past_incomes)}

💡 Tip: With irregular income, building a 3-6 month buffer is crucial!"""

# Create instance
income_tool = IncomeAnalyzerTool()
