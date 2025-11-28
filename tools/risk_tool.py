from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import yfinance as yf

class RiskInput(BaseModel):
    risk_level: str = Field(description="Risk level: low, medium, or high")
    investment_type: str = Field(description="Investment type: stock or mutual_fund")
    amount: Optional[float] = Field(default=None, description="Investment amount")

class RiskAversionTool(BaseTool):
    name: str = "risk_advisor"
    description: str = "Provides investment recommendations based on user's risk tolerance"
    args_schema: type[BaseModel] = RiskInput
    
    # Indian stock recommendations by risk level
    STOCK_RECOMMENDATIONS = {
        "low": [
            {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking", "reason": "Stable banking leader with consistent performance"},
            {"ticker": "ITC.NS", "name": "ITC Ltd", "sector": "FMCG", "reason": "Diversified FMCG giant with steady dividends"},
            {"ticker": "TCS.NS", "name": "TCS", "sector": "IT Services", "reason": "Blue-chip IT company with global presence"},
            {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Conglomerate", "reason": "Diversified business with strong fundamentals"},
            {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever", "sector": "FMCG", "reason": "Market leader in consumer goods"},
        ],
        "medium": [
            {"ticker": "INFY.NS", "name": "Infosys", "sector": "IT Services", "reason": "Strong IT player with growth potential"},
            {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking", "reason": "Growing private bank with good returns"},
            {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance", "sector": "NBFC", "reason": "Leading NBFC with strong growth"},
            {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "sector": "Paints", "reason": "Market leader with pricing power"},
            {"ticker": "MARUTI.NS", "name": "Maruti Suzuki", "sector": "Automobile", "reason": "Auto sector leader with market dominance"},
        ],
        "high": [
            {"ticker": "ADANIENT.NS", "name": "Adani Enterprises", "sector": "Conglomerate", "reason": "High growth potential in infrastructure"},
            {"ticker": "ZOMATO.NS", "name": "Zomato", "sector": "Food Tech", "reason": "Growing food delivery platform"},
            {"ticker": "PAYTM.NS", "name": "Paytm", "sector": "Fintech", "reason": "Digital payments leader with expansion plans"},
            {"ticker": "NYKAA.NS", "name": "Nykaa", "sector": "E-commerce", "reason": "Beauty e-commerce with strong brand"},
            {"ticker": "POLICYBZR.NS", "name": "PB Fintech", "sector": "Insurtech", "reason": "Insurance aggregator with tech edge"},
        ]
    }
    
    MUTUAL_FUND_RECOMMENDATIONS = {
        "low": [
            {"name": "HDFC Liquid Fund", "category": "Liquid Fund", "risk": "Very Low", "returns": "4-5%", "reason": "Safe parking for emergency funds"},
            {"name": "ICICI Prudential Equity & Debt Fund", "category": "Balanced Advantage", "risk": "Low", "returns": "8-10%", "reason": "Balanced mix of equity and debt"},
            {"name": "SBI Magnum Gilt Fund", "category": "Gilt Fund", "risk": "Low", "returns": "6-7%", "reason": "Government securities, very safe"},
            {"name": "Axis Banking & PSU Debt Fund", "category": "Debt Fund", "risk": "Low", "returns": "6-8%", "reason": "Quality debt instruments"},
        ],
        "medium": [
            {"name": "HDFC Index Fund - Nifty 50", "category": "Index Fund", "risk": "Medium", "returns": "10-12%", "reason": "Tracks Nifty 50, diversified exposure"},
            {"name": "Mirae Asset Large Cap Fund", "category": "Large Cap", "risk": "Medium", "returns": "11-13%", "reason": "Quality large-cap stocks"},
            {"name": "Parag Parikh Flexi Cap Fund", "category": "Flexi Cap", "risk": "Medium", "returns": "12-15%", "reason": "Flexible allocation across market caps"},
            {"name": "ICICI Prudential Bluechip Fund", "category": "Large Cap", "risk": "Medium", "returns": "10-12%", "reason": "Established blue-chip companies"},
        ],
        "high": [
            {"name": "Axis Small Cap Fund", "category": "Small Cap", "risk": "High", "returns": "15-20%", "reason": "High growth small companies"},
            {"name": "SBI Small Cap Fund", "category": "Small Cap", "risk": "High", "returns": "15-18%", "reason": "Aggressive small-cap exposure"},
            {"name": "Quant Mid Cap Fund", "category": "Mid Cap", "risk": "High", "returns": "14-18%", "reason": "Mid-cap growth opportunities"},
            {"name": "PGIM India Midcap Opportunities Fund", "category": "Mid Cap", "risk": "High", "returns": "13-17%", "reason": "Quality mid-cap picks"},
        ]
    }
    
    def _run(self, risk_level: str, investment_type: str, amount: float = None) -> str:
        """Provide investment recommendations based on risk profile."""
        try:
            risk_level = risk_level.lower()
            investment_type = investment_type.lower()
            
            if risk_level not in ["low", "medium", "high"]:
                return """❌ Invalid risk level. Please specify:
• **Low** - Capital preservation, minimal volatility
• **Medium** - Balanced growth with moderate risk
• **High** - Aggressive growth, can handle volatility"""
            
            # Risk profile description
            risk_profiles = {
                "low": {
                    "emoji": "🛡️",
                    "title": "Conservative Investor",
                    "description": "You prioritize capital safety over high returns",
                    "allocation": "70% Debt, 30% Equity",
                    "horizon": "1-3 years",
                    "volatility": "Low (5-10% fluctuation)"
                },
                "medium": {
                    "emoji": "⚖️",
                    "title": "Balanced Investor",
                    "description": "You seek growth with manageable risk",
                    "allocation": "50% Equity, 50% Debt",
                    "horizon": "3-5 years",
                    "volatility": "Medium (10-20% fluctuation)"
                },
                "high": {
                    "emoji": "🚀",
                    "title": "Aggressive Investor",
                    "description": "You can handle volatility for higher returns",
                    "allocation": "80% Equity, 20% Debt",
                    "horizon": "5+ years",
                    "volatility": "High (20-40% fluctuation)"
                }
            }
            
            profile = risk_profiles[risk_level]
            
            response = f"""{profile['emoji']} **{profile['title']}**

{profile['description']}

**Your Risk Profile:**
📊 Recommended Allocation: {profile['allocation']}
⏰ Investment Horizon: {profile['horizon']}
📈 Expected Volatility: {profile['volatility']}

"""
            
            if investment_type == "stock":
                recommendations = self.STOCK_RECOMMENDATIONS[risk_level]
                response += f"""**🔍 Recommended Stocks for {profile['title']}:**

"""
                for i, stock in enumerate(recommendations[:5], 1):
                    response += f"""{i}. **{stock['name']}** ({stock['ticker']})
   📂 Sector: {stock['sector']}
   💡 Why: {stock['reason']}

"""
                
                response += """**⚠️ Important Guidelines:**
• Diversify across 5-8 stocks minimum
• Invest only surplus funds (not emergency money)
• Review portfolio quarterly
• Don't panic sell during market dips
• Consider SIP for rupee cost averaging

💡 Use: "Check HDFCBANK stock" for detailed analysis"""
            
            elif investment_type == "mutual_fund" or investment_type == "mutualfund":
                recommendations = self.MUTUAL_FUND_RECOMMENDATIONS[risk_level]
                response += f"""**📊 Recommended Mutual Funds for {profile['title']}:**

"""
                for i, fund in enumerate(recommendations, 1):
                    response += f"""{i}. **{fund['name']}**
   📂 Category: {fund['category']}
   ⚠️ Risk: {fund['risk']}
   📈 Expected Returns: {fund['returns']} p.a.
   💡 Why: {fund['reason']}

"""
                
                response += """**⚠️ Important Guidelines:**
• Start with SIP (Systematic Investment Plan)
• Minimum investment: ₹500-1000/month
• Stay invested for recommended horizon
• Review annually, don't churn frequently
• Consider tax implications (LTCG/STCG)

💡 Tip: Diversify across 3-4 funds from different categories"""
            
            else:
                return "❌ Invalid investment type. Choose 'stock' or 'mutual_fund'"
            
            # Add amount-specific advice
            if amount:
                response += f"""

**💰 For Your Investment of ₹{amount:,.0f}:**
"""
                if risk_level == "low":
                    response += f"""• Debt Funds: ₹{amount*0.7:,.0f} (70%)
• Large Cap Equity: ₹{amount*0.3:,.0f} (30%)"""
                elif risk_level == "medium":
                    response += f"""• Equity Funds: ₹{amount*0.5:,.0f} (50%)
• Debt Funds: ₹{amount*0.5:,.0f} (50%)"""
                else:
                    response += f"""• Equity Funds: ₹{amount*0.8:,.0f} (80%)
• Debt/Liquid: ₹{amount*0.2:,.0f} (20%)"""
            
            response += """

📞 **Disclaimer:** These are general recommendations. Consult a SEBI registered advisor for personalized advice. Past performance doesn't guarantee future returns."""
            
            return response
        
        except Exception as e:
            return f"⚠️ Error generating recommendations: {str(e)}"

risk_tool = RiskAversionTool()