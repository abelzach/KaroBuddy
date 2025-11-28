from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import yfinance as yf

class StockInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol like RELIANCE, TCS, INFY")

class StockScreenerTool(BaseTool):
    name: str = "stock_screener"
    description: str = "Analyzes Indian stocks using fundamental metrics and quality checks"
    args_schema: type[BaseModel] = StockInput
    
    def _run(self, ticker: str) -> str:
        """Analyze a stock using fundamental metrics."""
        try:
            # Try NSE first, then BSE
            stock = yf.Ticker(f"{ticker}.NS")
            info = stock.info
            
            # If NSE fails, try BSE
            if not info or 'regularMarketPrice' not in info:
                stock = yf.Ticker(f"{ticker}.BO")
                info = stock.info
            
            # Check if we got valid data
            if not info or 'regularMarketPrice' not in info:
                return f"❌ Couldn't fetch data for {ticker}. Please check the ticker symbol or try with .NS or .BO suffix (e.g., RELIANCE.NS)"
            
            # Get key metrics with safe defaults
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            pe = info.get('trailingPE', info.get('forwardPE', 999))
            debt_equity = info.get('debtToEquity', 999) / 100 if info.get('debtToEquity') else 999
            roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
            market_cap = info.get('marketCap', 0) / 10000000  # In crores
            sector = info.get('sector', 'Unknown')
            company_name = info.get('longName', ticker.upper())
            
            # Buffett-style quality scoring
            score = 0
            flags = []
            
            # Valuation check
            if pe < 20 and pe > 0:
                score += 3
                flags.append(f"✅ Attractive valuation (P/E: {pe:.1f})")
            elif pe < 30 and pe > 0:
                score += 2
                flags.append(f"🟡 Fair valuation (P/E: {pe:.1f})")
            elif pe > 0:
                flags.append(f"⚠️ Expensive (P/E: {pe:.1f})")
            else:
                flags.append(f"⚠️ P/E not available")
            
            # Debt check
            if debt_equity < 0.5:
                score += 3
                flags.append(f"✅ Very low debt (D/E: {debt_equity:.2f})")
            elif debt_equity < 1.0:
                score += 2
                flags.append(f"🟡 Manageable debt (D/E: {debt_equity:.2f})")
            elif debt_equity < 999:
                flags.append(f"⚠️ High debt (D/E: {debt_equity:.2f})")
            else:
                flags.append(f"⚠️ Debt data not available")
            
            # Profitability check
            if roe > 20:
                score += 3
                flags.append(f"✅ Excellent ROE ({roe:.1f}%)")
            elif roe > 15:
                score += 2
                flags.append(f"🟡 Good ROE ({roe:.1f}%)")
            elif roe > 0:
                flags.append(f"⚠️ Weak ROE ({roe:.1f}%)")
            else:
                flags.append(f"⚠️ ROE not available")
            
            # Generate recommendation
            if score >= 7:
                recommendation = "🟢 STRONG BUY"
                advice = "High-quality company at reasonable price"
            elif score >= 5:
                recommendation = "🟡 HOLD/ACCUMULATE"
                advice = "Good company, wait for better entry"
            else:
                recommendation = "🔴 AVOID FOR NOW"
                advice = "Quality or valuation concerns"
            
            return f"""📊 {company_name}
Ticker: {ticker.upper()}

{recommendation}
{advice}

**Current Price:** ₹{current_price:,.2f}

**Fundamentals:**
{chr(10).join(flags)}

💼 Sector: {sector}
💰 Market Cap: ₹{market_cap:,.0f} Cr

**Quality Score: {score}/9**

⚠️ Disclaimer: This is basic screening based on available data. Always do detailed research and consult a financial advisor before investing!"""
        
        except Exception as e:
            return f"""❌ Error analyzing {ticker}: {str(e)}

Please check:
• Ticker symbol is correct
• Try adding .NS for NSE or .BO for BSE
• Example: RELIANCE.NS or TCS.BO

Common tickers:
• RELIANCE.NS, TCS.NS, INFY.NS
• HDFCBANK.NS, ICICIBANK.NS
• ITC.NS, SBIN.NS"""

# Create instance
stock_tool = StockScreenerTool()

