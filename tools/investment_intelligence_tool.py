from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import yfinance as yf
from datetime import datetime, timedelta

class InvestmentInput(BaseModel):
    query: str = Field(description="Investment query - stock ticker, mutual fund name, or sector")
    analysis_type: str = Field(description="Type: stock_analysis, mutual_fund_analysis, sector_analysis, or top_performers")

class InvestmentIntelligenceTool(BaseTool):
    name: str = "investment_intelligence"
    description: str = "Provides comprehensive analysis of stocks and mutual funds with clear buy/hold/sell recommendations"
    args_schema: type[BaseModel] = InvestmentInput
    
    def _analyze_stock_comprehensive(self, ticker: str) -> str:
        """Provide comprehensive stock analysis with clear recommendation."""
        try:
            # Try NSE first
            stock = yf.Ticker(f"{ticker}.NS")
            info = stock.info
            
            # If NSE fails, try BSE
            if not info or 'regularMarketPrice' not in info:
                stock = yf.Ticker(f"{ticker}.BO")
                info = stock.info
            
            if not info or 'regularMarketPrice' not in info:
                return f"❌ Unable to fetch data for {ticker}. Please verify the ticker symbol."
            
            # Extract comprehensive data
            company_name = info.get('longName', ticker.upper())
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            previous_close = info.get('previousClose', current_price)
            day_change = ((current_price - previous_close) / previous_close * 100) if previous_close else 0
            
            # Valuation metrics
            pe_ratio = info.get('trailingPE', info.get('forwardPE', 0))
            pb_ratio = info.get('priceToBook', 0)
            market_cap = info.get('marketCap', 0) / 10000000  # In crores
            
            # Profitability metrics
            roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
            profit_margin = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
            
            # Financial health
            debt_equity = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0
            current_ratio = info.get('currentRatio', 0)
            
            # Growth metrics
            revenue_growth = info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0
            earnings_growth = info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0
            
            # Dividend
            dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
            
            # Other info
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            # Get historical data for trend analysis
            hist = stock.history(period="1y")
            if not hist.empty:
                year_high = hist['High'].max()
                year_low = hist['Low'].min()
                price_from_high = ((current_price - year_high) / year_high * 100)
                price_from_low = ((current_price - year_low) / year_low * 100)
            else:
                year_high = year_low = current_price
                price_from_high = price_from_low = 0
            
            # Scoring system (out of 100)
            score = 0
            analysis_points = []
            
            # 1. Valuation (25 points)
            if 0 < pe_ratio < 15:
                score += 25
                analysis_points.append("✅ Excellent valuation - Trading at attractive P/E")
            elif 15 <= pe_ratio < 25:
                score += 18
                analysis_points.append("🟡 Fair valuation - Reasonably priced")
            elif 25 <= pe_ratio < 35:
                score += 10
                analysis_points.append("⚠️ Slightly expensive - P/E above market average")
            elif pe_ratio >= 35:
                score += 0
                analysis_points.append("🔴 Overvalued - Very high P/E ratio")
            else:
                analysis_points.append("⚠️ P/E data not available")
            
            # 2. Profitability (25 points)
            if roe > 20:
                score += 25
                analysis_points.append("✅ Excellent profitability - ROE > 20%")
            elif roe > 15:
                score += 18
                analysis_points.append("🟡 Good profitability - Healthy ROE")
            elif roe > 10:
                score += 10
                analysis_points.append("⚠️ Moderate profitability - Average ROE")
            else:
                analysis_points.append("🔴 Weak profitability - Low ROE")
            
            # 3. Financial Health (25 points)
            if debt_equity < 0.5:
                score += 25
                analysis_points.append("✅ Strong balance sheet - Very low debt")
            elif debt_equity < 1.0:
                score += 18
                analysis_points.append("🟡 Healthy finances - Manageable debt")
            elif debt_equity < 2.0:
                score += 10
                analysis_points.append("⚠️ Moderate debt levels - Monitor closely")
            else:
                analysis_points.append("🔴 High debt burden - Financial risk")
            
            # 4. Growth (25 points)
            avg_growth = (revenue_growth + earnings_growth) / 2 if (revenue_growth and earnings_growth) else 0
            if avg_growth > 20:
                score += 25
                analysis_points.append("✅ Strong growth momentum - Expanding rapidly")
            elif avg_growth > 10:
                score += 18
                analysis_points.append("🟡 Steady growth - Consistent expansion")
            elif avg_growth > 0:
                score += 10
                analysis_points.append("⚠️ Slow growth - Limited expansion")
            else:
                analysis_points.append("🔴 Declining growth - Concerning trend")
            
            # Generate recommendation
            if score >= 80:
                recommendation = "🟢 **STRONG BUY**"
                action = "Excellent opportunity to invest"
                risk_level = "Low to Medium Risk"
            elif score >= 60:
                recommendation = "🟡 **BUY/ACCUMULATE**"
                action = "Good for long-term investment"
                risk_level = "Medium Risk"
            elif score >= 40:
                recommendation = "🟠 **HOLD**"
                action = "Wait for better entry point"
                risk_level = "Medium to High Risk"
            else:
                recommendation = "🔴 **AVOID/SELL**"
                action = "Not recommended at current levels"
                risk_level = "High Risk"
            
            # Build comprehensive response
            analysis_date = datetime.now().strftime('%d %B %Y, %I:%M %p')
            
            suitable_for = (
                "• Conservative to Moderate investors\n• Long-term wealth creation\n• Portfolio core holding" if score >= 80
                else "• Moderate investors\n• 3-5 year investment horizon\n• Diversified portfolio component" if score >= 60
                else "• Existing investors (hold position)\n• Wait for better valuations\n• Monitor quarterly results" if score >= 40
                else "• Not recommended for new investment\n• Consider exiting if holding\n• High risk, uncertain returns"
            )
            
            action_steps = (
                "1. Consider buying in tranches\n2. Set target allocation (max 10% of portfolio)\n3. Monitor quarterly results\n4. Review after 6 months" if score >= 80
                else "1. Add to watchlist\n2. Wait for price correction\n3. Buy on dips\n4. Maintain stop-loss" if score >= 60
                else "1. Hold existing position\n2. Don't add more\n3. Review fundamentals quarterly\n4. Exit if score drops further" if score >= 40
                else "1. Avoid new investment\n2. Consider booking losses if holding\n3. Reallocate to better opportunities\n4. Monitor for turnaround signs"
            )
            
            response = f"""📊 **COMPREHENSIVE STOCK ANALYSIS**

**{company_name}** ({ticker.upper()})
{sector} | {industry}

{recommendation}
{action}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**📈 PRICE INFORMATION**
Current Price: ₹{current_price:,.2f}
Day Change: {day_change:+.2f}% {'📈' if day_change > 0 else '📉'}
52-Week High: ₹{year_high:,.2f} ({price_from_high:+.1f}%)
52-Week Low: ₹{year_low:,.2f} ({price_from_low:+.1f}%)

**💰 VALUATION METRICS**
P/E Ratio: {pe_ratio:.2f}
P/B Ratio: {pb_ratio:.2f}
Market Cap: ₹{market_cap:,.0f} Cr

**📊 PROFITABILITY**
ROE: {roe:.2f}%
Profit Margin: {profit_margin:.2f}%
Dividend Yield: {dividend_yield:.2f}%

**💪 FINANCIAL HEALTH**
Debt/Equity: {debt_equity:.2f}
Current Ratio: {current_ratio:.2f}

**🚀 GROWTH METRICS**
Revenue Growth: {revenue_growth:+.2f}%
Earnings Growth: {earnings_growth:+.2f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔍 DETAILED ANALYSIS**

{chr(10).join(analysis_points)}

**📊 Investment Score: {score}/100**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**💡 INVESTMENT RECOMMENDATION**

{recommendation}

**Risk Level:** {risk_level}

**Suitable For:**
{suitable_for}

**Action Steps:**
{action_steps}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **DISCLAIMER:** This analysis is based on available financial data and should not be considered as financial advice. Always consult a SEBI registered investment advisor before making investment decisions. Past performance is not indicative of future results.

Analysis Date: {analysis_date}"""
            
            return response
        
        except Exception as e:
            return f"⚠️ Error analyzing stock: {str(e)}\n\nPlease verify the ticker symbol and try again."
    
    def _analyze_mutual_fund(self, fund_name: str) -> str:
        """Provide mutual fund analysis and recommendation."""
        # This is a template - in production, integrate with MF API
        return f"""📊 **MUTUAL FUND ANALYSIS**

**{fund_name}**

🔍 **Analysis in Progress...**

For detailed mutual fund analysis, I recommend:

1. **Check Fund Performance:**
   • Visit: moneycontrol.com or valueresearchonline.com
   • Look for 3-year and 5-year returns
   • Compare with benchmark and category average

2. **Key Metrics to Check:**
   ✅ Expense Ratio (lower is better, <1% for equity)
   ✅ AUM (Assets Under Management) - prefer ₹500+ Cr
   ✅ Fund Manager track record
   ✅ Portfolio concentration (top 10 holdings)
   ✅ Exit load and lock-in period

3. **Risk Assessment:**
   📊 Check standard deviation (volatility)
   📊 Sharpe ratio (risk-adjusted returns)
   📊 Maximum drawdown (worst loss period)

4. **Investment Recommendation:**
   • Start with SIP (₹500-5000/month)
   • Minimum 3-year investment horizon
   • Diversify across 3-4 funds
   • Review annually, don't churn

**💡 Popular Fund Categories:**

**For Low Risk:**
• Liquid Funds, Debt Funds
• Expected: 5-7% returns

**For Medium Risk:**
• Large Cap, Index Funds
• Expected: 10-12% returns

**For High Risk:**
• Mid Cap, Small Cap Funds
• Expected: 15-20% returns

Would you like stock recommendations based on your risk profile? Just tell me: "I want low/medium/high risk investments" """
        
    def _analyze_sector_stocks(self, sector: str, period: str = "1wk") -> str:
        """Analyze top performing stocks in a sector."""
        try:
            # Sector to stock mapping (top stocks in each sector)
            sector_stocks = {
                'gold': ['GOLDBEES.NS', 'GOLDIAM.NS', 'MANAPPURAM.NS', 'MUTHOOTFIN.NS'],
                'it': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
                'banking': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
                'pharma': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'AUROPHARMA.NS'],
                'auto': ['MARUTI.NS', 'TATAMOTORS.NS', 'M&M.NS', 'BAJAJ-AUTO.NS', 'HEROMOTOCO.NS'],
                'fmcg': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS'],
                'energy': ['RELIANCE.NS', 'ONGC.NS', 'BPCL.NS', 'IOC.NS', 'NTPC.NS'],
                'realty': ['DLF.NS', 'GODREJPROP.NS', 'OBEROIRLTY.NS', 'PRESTIGE.NS', 'BRIGADE.NS'],
                'metal': ['TATASTEEL.NS', 'HINDALCO.NS', 'JSWSTEEL.NS', 'VEDL.NS', 'COALINDIA.NS']
            }
            
            sector_lower = sector.lower()
            stocks = sector_stocks.get(sector_lower, [])
            
            if not stocks:
                available_sectors = ', '.join(sector_stocks.keys())
                return f"""❌ Sector '{sector}' not found.

Available sectors:
{available_sectors}

Example: "Analyze gold sector stocks" or "Show me IT sector top performers" """
            
            # Analyze each stock
            results = []
            for ticker in stocks:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period=period)
                    info = stock.info
                    
                    if not hist.empty and len(hist) > 1:
                        start_price = hist['Close'].iloc[0]
                        end_price = hist['Close'].iloc[-1]
                        change_pct = ((end_price - start_price) / start_price) * 100
                        
                        company_name = info.get('longName', ticker.replace('.NS', ''))
                        current_price = info.get('regularMarketPrice', end_price)
                        
                        results.append({
                            'ticker': ticker.replace('.NS', ''),
                            'name': company_name,
                            'price': current_price,
                            'change': change_pct
                        })
                except:
                    continue
            
            if not results:
                return f"❌ Unable to fetch data for {sector} sector stocks. Please try again later."
            
            # Sort by performance
            results.sort(key=lambda x: x['change'], reverse=True)
            
            # Build response
            period_text = "this week" if period == "1wk" else "this month" if period == "1mo" else "today"
            response = f"""📊 **{sector.upper()} SECTOR ANALYSIS**
Performance for {period_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🏆 TOP PERFORMERS:**

"""
            
            for i, stock in enumerate(results[:3], 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                arrow = "📈" if stock['change'] > 0 else "📉"
                response += f"""{emoji} **{stock['name']}** ({stock['ticker']})
   Price: ₹{stock['price']:,.2f}
   Change: {stock['change']:+.2f}% {arrow}

"""
            
            response += "**📉 OTHER STOCKS:**\n\n"
            
            for stock in results[3:]:
                arrow = "📈" if stock['change'] > 0 else "📉"
                response += f"""• **{stock['name']}** ({stock['ticker']})
   ₹{stock['price']:,.2f} | {stock['change']:+.2f}% {arrow}

"""
            
            # Add recommendation
            top_stock = results[0]
            response += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **RECOMMENDATION:**

The best performer in {sector.upper()} sector {period_text} is **{top_stock['name']}** with {top_stock['change']:+.2f}% returns.

**Want detailed analysis?**
Say: "Is {top_stock['ticker']} a good stock?"

**⚠️ Important:**
• Past performance doesn't guarantee future returns
• Consider fundamentals, not just price movement
• Diversify across sectors
• Consult a SEBI registered advisor

Analysis Date: {datetime.now().strftime('%d %B %Y, %I:%M %p')}"""
            
            return response
            
        except Exception as e:
            return f"⚠️ Error analyzing sector: {str(e)}"
    
    def _run(self, query: str, analysis_type: str) -> str:
        """Main execution method."""
        try:
            if analysis_type == "stock_analysis":
                return self._analyze_stock_comprehensive(query)
            elif analysis_type == "mutual_fund_analysis":
                return self._analyze_mutual_fund(query)
            elif analysis_type == "sector_analysis":
                return self._analyze_sector_stocks(query, period="1wk")
            elif analysis_type == "top_performers":
                return self._analyze_sector_stocks(query, period="1wk")
            else:
                return "❌ Invalid analysis type. Use 'stock_analysis', 'mutual_fund_analysis', 'sector_analysis', or 'top_performers'"
        except Exception as e:
            return f"⚠️ Error in investment analysis: {str(e)}"

# Create instance
investment_intelligence_tool = InvestmentIntelligenceTool()
