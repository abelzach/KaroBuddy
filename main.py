from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from agent_graph import run_agent_graph
from database import db_manager
import config
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store conversation state (in production, use Redis)
user_states = {}

def get_main_menu_keyboard():
    """Get the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Log Income", callback_data='income'),
            InlineKeyboardButton("💸 Log Expense", callback_data='expense')
        ],
        [
            InlineKeyboardButton("🎯 My Goals", callback_data='goals'),
            InlineKeyboardButton("📊 Dashboard", callback_data='dashboard')
        ],
        [
            InlineKeyboardButton("📈 Stock Analysis", callback_data='stock'),
            InlineKeyboardButton("💼 Investment Ideas", callback_data='invest')
        ],
        [
            InlineKeyboardButton("🛡️ Scam Check", callback_data='fraud'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_goal_menu_keyboard():
    """Get the goal management keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create Goal", callback_data='goal_create'),
            InlineKeyboardButton("📋 View Goals", callback_data='goal_list')
        ],
        [
            InlineKeyboardButton("💰 Allocate Funds", callback_data='goal_allocate'),
            InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_investment_menu_keyboard():
    """Get the investment recommendation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Stock Suggestions", callback_data='invest_stocks'),
            InlineKeyboardButton("💼 Mutual Funds", callback_data='invest_mf')
        ],
        [
            InlineKeyboardButton("🎯 Set Risk Profile", callback_data='risk_profile'),
            InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_risk_profile_keyboard():
    """Get risk profile selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🛡️ Low Risk (Conservative)", callback_data='risk_low')],
        [InlineKeyboardButton("⚖️ Medium Risk (Balanced)", callback_data='risk_medium')],
        [InlineKeyboardButton("🚀 High Risk (Aggressive)", callback_data='risk_high')],
        [InlineKeyboardButton("🔙 Back", callback_data='invest')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    # Create or update user in database
    db_manager.create_user(
        telegram_id=user.id,
        name=user.first_name,
        username=user.username
    )
    
    welcome_message = f"""👋 **Welcome to KaroBuddy!**

Hi {user.first_name}! I'm your AI-powered financial coach designed for people with irregular incomes.

**🎯 What I Can Do:**

💰 **Income & Expense Tracking**
   Track your money flow and build savings

🎯 **Goal-Based Planning**
   Set financial goals and track progress

📈 **Investment Intelligence**
   Get detailed stock & mutual fund analysis

💼 **Smart Recommendations**
   Personalized suggestions based on your risk profile

🛡️ **Scam Protection**
   Detect fraudulent investment schemes

📊 **Financial Dashboard**
   Complete overview of your finances

**🚀 Quick Start:**
1. Set your risk profile
2. Create financial goals
3. Track income & expenses
4. Get investment recommendations

Choose an option below to get started! 👇"""
    
    await update.message.reply_text(
        welcome_message, 
        reply_markup=get_main_menu_keyboard(), 
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """🤖 **KaroBuddy Help Guide**

**📱 MAIN FEATURES:**

**1️⃣ Income & Expense Tracking**
   • "I earned 25000"
   • "Spent 2500 on groceries"
   • Automatic categorization

**2️⃣ Goal Management**
   • "Create goal Emergency Fund with target 100000"
   • "Allocate 5000 to Emergency Fund"
   • "Show my goals"

**3️⃣ Stock Analysis**
   • "Is RELIANCE a good stock?"
   • "Check TCS stock"
   • Get comprehensive analysis with buy/hold/sell recommendations

**4️⃣ Investment Recommendations**
   • Set your risk profile (low/medium/high)
   • Get personalized stock & mutual fund suggestions
   • Risk-adjusted recommendations

**5️⃣ Scam Detection**
   • "Is this a scam: [paste message]"
   • AI-powered fraud detection
   • Protect your money

**6️⃣ Dashboard**
   • View income, expenses, savings
   • Track goal progress
   • Financial overview

**💡 PRO TIPS:**

✅ Set goals to separate savings from expenses
✅ Allocate to goals - it won't count as spending
✅ Set your risk profile for better recommendations
✅ Always verify investment opportunities
✅ Build 3-6 month emergency fund first

**🎯 COMMANDS:**
/start - Main menu
/dashboard - Financial summary
/help - This help message

**Need specific help?** Just ask me naturally! I understand conversational language. 😊"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command."""
    user_id = update.effective_user.id
    await update.message.chat.send_action("typing")
    result = await run_agent_graph(user_id, "show my dashboard", "dashboard")
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(result, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    
    if action == 'main_menu':
        welcome_message = """🏠 **Main Menu**

Choose what you'd like to do:"""
        await query.message.edit_text(
            welcome_message,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action == 'income':
        user_states[user_id] = 'awaiting_income'
        await query.message.reply_text(
            "💰 **Log Income**\n\n"
            "How much did you earn?\n\n"
            "**Examples:**\n"
            "• I earned 25000\n"
            "• Got paid ₹50000\n"
            "• Received 15000 from client\n"
            "• Freelance income 35000",
            parse_mode='Markdown'
        )
    
    elif action == 'expense':
        user_states[user_id] = 'awaiting_expense'
        await query.message.reply_text(
            "💸 **Log Expense**\n\n"
            "How much did you spend and on what?\n\n"
            "**Examples:**\n"
            "• Spent 2500 on groceries\n"
            "• Paid 5000 for rent\n"
            "• Bought shoes for 3000\n"
            "• Restaurant bill 1500",
            parse_mode='Markdown'
        )
    
    elif action == 'goals':
        await query.message.edit_text(
            "🎯 **Goal Management**\n\n"
            "Manage your financial goals:\n\n"
            "• Create new goals\n"
            "• View existing goals\n"
            "• Allocate funds to goals\n\n"
            "💡 Goal allocations don't count as expenses!",
            reply_markup=get_goal_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action == 'goal_create':
        user_states[user_id] = 'awaiting_goal_create'
        await query.message.reply_text(
            "➕ **Create New Goal**\n\n"
            "Tell me about your goal:\n\n"
            "**Format:**\n"
            "Create goal [NAME] with target [AMOUNT]\n\n"
            "**Examples:**\n"
            "• Create goal Emergency Fund with target 100000\n"
            "• New goal Vacation with target 50000\n"
            "• Set goal House Down Payment with target 500000",
            parse_mode='Markdown'
        )
    
    elif action == 'goal_list':
        await query.message.chat.send_action("typing")
        result = await run_agent_graph(user_id, "show my goals", "goal")
        keyboard = [[InlineKeyboardButton("🔙 Back to Goals", callback_data='goals')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'goal_allocate':
        user_states[user_id] = 'awaiting_goal_allocate'
        await query.message.reply_text(
            "💰 **Allocate Funds to Goal**\n\n"
            "How much would you like to allocate?\n\n"
            "**Format:**\n"
            "Allocate [AMOUNT] to [GOAL NAME]\n\n"
            "**Examples:**\n"
            "• Allocate 5000 to Emergency Fund\n"
            "• Add 10000 to Vacation\n"
            "• Put 15000 in House Down Payment\n\n"
            "💡 First, use 'View Goals' to see your goal names",
            parse_mode='Markdown'
        )
    
    elif action == 'stock':
        user_states[user_id] = 'awaiting_stock'
        await query.message.reply_text(
            "📈 **Stock Analysis**\n\n"
            "Which stock would you like to analyze?\n\n"
            "**For Quick Check:**\n"
            "• Check RELIANCE\n"
            "• Analyze TCS\n\n"
            "**For Detailed Analysis:**\n"
            "• Is RELIANCE a good stock?\n"
            "• Should I invest in TCS?\n\n"
            "**Popular Stocks:**\n"
            "RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, SBIN, HINDUNILVR, BAJFINANCE, ASIANPAINT",
            parse_mode='Markdown'
        )
    
    elif action == 'invest':
        await query.message.edit_text(
            "💼 **Investment Recommendations**\n\n"
            "Get personalized investment suggestions based on your risk profile.\n\n"
            "**What would you like?**\n"
            "• Stock recommendations\n"
            "• Mutual fund suggestions\n"
            "• Set/update risk profile",
            reply_markup=get_investment_menu_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action == 'invest_stocks':
        user_states[user_id] = 'awaiting_invest_stocks'
        await query.message.reply_text(
            "📊 **Stock Recommendations**\n\n"
            "I'll suggest stocks based on your risk profile.\n\n"
            "**What's your risk tolerance?**\n\n"
            "Reply with:\n"
            "• Low risk stocks\n"
            "• Medium risk stocks\n"
            "• High risk stocks\n\n"
            "Or set your profile first using the menu.",
            parse_mode='Markdown'
        )
    
    elif action == 'invest_mf':
        user_states[user_id] = 'awaiting_invest_mf'
        await query.message.reply_text(
            "💼 **Mutual Fund Recommendations**\n\n"
            "I'll suggest mutual funds based on your risk profile.\n\n"
            "**What's your risk tolerance?**\n\n"
            "Reply with:\n"
            "• Low risk mutual funds\n"
            "• Medium risk mutual funds\n"
            "• High risk mutual funds\n\n"
            "Or set your profile first using the menu.",
            parse_mode='Markdown'
        )
    
    elif action == 'risk_profile':
        await query.message.edit_text(
            "🎯 **Set Your Risk Profile**\n\n"
            "Your risk profile helps me provide personalized recommendations.\n\n"
            "**Choose your risk tolerance:**",
            reply_markup=get_risk_profile_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action.startswith('risk_'):
        risk_level = action.replace('risk_', '')
        await query.message.chat.send_action("typing")
        result = await run_agent_graph(user_id, f"Set my risk profile to {risk_level}", "risk_profile")
        keyboard = [[InlineKeyboardButton("🔙 Back to Investments", callback_data='invest')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'fraud':
        user_states[user_id] = 'awaiting_fraud_check'
        await query.message.reply_text(
            "🛡️ **Scam Detection**\n\n"
            "Describe the investment opportunity or paste the suspicious message.\n\n"
            "**I'll check for:**\n"
            "• Guaranteed returns promises\n"
            "• Ponzi scheme patterns\n"
            "• Unrealistic claims\n"
            "• High-pressure tactics\n\n"
            "**Example:**\n"
            "Is this a scam: Double your money in 30 days guaranteed!",
            parse_mode='Markdown'
        )
    
    elif action == 'dashboard':
        await query.message.chat.send_action("typing")
        result = await run_agent_graph(user_id, "show my dashboard", "dashboard")
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'help':
        help_text = """🤖 **Quick Help**

**💰 Track Money:**
"I earned 25000"
"Spent 2500 on groceries"

**🎯 Manage Goals:**
"Create goal Emergency Fund with target 100000"
"Allocate 5000 to Emergency Fund"

**📈 Analyze Investments:**
"Is RELIANCE a good stock?"
"Suggest low risk mutual funds"

**🛡️ Check Scams:**
"Is this a scam: [message]"

Use /help for detailed guide."""
        keyboard = [[InlineKeyboardButton("📖 Full Help Guide", callback_data='full_help')],
                   [InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif action == 'full_help':
        await help_command(query, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id
    message = update.message.text
    
    # Get user state
    state = user_states.get(user_id, 'general')
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Route to appropriate agent based on state
    if state == 'awaiting_income':
        result = await run_agent_graph(user_id, message, "income")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_expense':
        result = await run_agent_graph(user_id, message, "expense")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_stock':
        result = await run_agent_graph(user_id, message, "stock_analysis" if "good" in message.lower() else "stock")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_fraud_check':
        result = await run_agent_graph(user_id, message, "fraud")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_goal_create':
        result = await run_agent_graph(user_id, message, "goal")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Goals", callback_data='goals')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_goal_allocate':
        result = await run_agent_graph(user_id, message, "goal")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Goals", callback_data='goals')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_invest_stocks':
        result = await run_agent_graph(user_id, message, "investment_recommendation")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Investments", callback_data='invest')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_invest_mf':
        result = await run_agent_graph(user_id, message, "investment_recommendation")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton("🔙 Back to Investments", callback_data='invest')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    else:
        # General conversation - let the agent decide
        result = await run_agent_graph(user_id, message, "general")
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Sorry, something went wrong. Please try again or use /start to restart."
        )

def main():
    """Start the bot."""
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Create application
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("🤖 KaroBuddy is starting...")
    print("=" * 60)
    print("🤖 KaroBuddy Financial Advisor Bot - Enhanced Version")
    print("=" * 60)
    print("✅ Bot is running and ready to help!")
    print("📱 Open Telegram and start chatting with your bot")
    print("")
    print("🎯 NEW FEATURES:")
    print("   • Goal-based financial planning")
    print("   • Risk-based investment recommendations")
    print("   • Comprehensive stock analysis")
    print("   • Enhanced UI with better navigation")
    print("")
    print("🛑 Press Ctrl+C to stop the bot")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
