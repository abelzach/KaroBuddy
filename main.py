from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    # Create or update user in database
    db_manager.create_user(
        telegram_id=user.id,
        name=user.first_name,
        username=user.username
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Log Income", callback_data='income')],
        [InlineKeyboardButton("💸 Log Expense", callback_data='expense')],
        [InlineKeyboardButton("🔍 Check Stock", callback_data='stock')],
        [InlineKeyboardButton("🛡️ Check for Scam", callback_data='fraud')],
        [InlineKeyboardButton("📊 Dashboard", callback_data='dashboard')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""👋 Hi {user.first_name}! I'm **KaroBuddy** - your AI financial coach!

I help people with irregular incomes:
✅ Smart budgeting & savings
✅ Scam protection
✅ Stock analysis
✅ Financial advice

**Quick Commands:**
/start - Show this menu
/dashboard - View your financial summary
/help - Get help

What would you like to do?"""
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """🤖 **KaroBuddy Help**

**What I can do:**
💰 Track your income and suggest savings
💸 Log your expenses
🔍 Analyze Indian stocks (NSE/BSE)
🛡️ Detect investment scams
📊 Show your financial dashboard

**How to use:**
• Click buttons or type naturally
• "I earned 25000" - Logs income
• "Spent 2500 on groceries" - Logs expense
• "Check RELIANCE stock" - Analyzes stock
• "Is this a scam: [message]" - Checks for fraud

**Commands:**
/start - Main menu
/dashboard - Financial summary
/help - This help message

**Tips:**
• Be specific with amounts
• Use stock tickers (e.g., RELIANCE.NS)
• Always verify investment opportunities
• Build a 3-6 month emergency fund

Need more help? Just ask me anything! 😊"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command."""
    user_id = update.effective_user.id
    result = await run_agent_graph(user_id, "show my dashboard", "dashboard")
    await update.message.reply_text(result, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    
    if action == 'income':
        user_states[user_id] = 'awaiting_income'
        await query.message.reply_text(
            "💰 **Log Income**\n\n"
            "How much did you earn?\n\n"
            "Examples:\n"
            "• I earned 25000\n"
            "• Got paid ₹50000\n"
            "• Received 15000 from client",
            parse_mode='Markdown'
        )
    
    elif action == 'expense':
        user_states[user_id] = 'awaiting_expense'
        await query.message.reply_text(
            "💸 **Log Expense**\n\n"
            "How much did you spend?\n\n"
            "Examples:\n"
            "• Spent 2500 on groceries\n"
            "• Paid 5000 for rent\n"
            "• Bought shoes for 3000",
            parse_mode='Markdown'
        )
    
    elif action == 'stock':
        user_states[user_id] = 'awaiting_stock'
        await query.message.reply_text(
            "🔍 **Stock Analysis**\n\n"
            "Which stock would you like to analyze?\n\n"
            "Examples:\n"
            "• RELIANCE\n"
            "• TCS\n"
            "• INFY\n"
            "• HDFCBANK",
            parse_mode='Markdown'
        )
    
    elif action == 'fraud':
        user_states[user_id] = 'awaiting_fraud_check'
        await query.message.reply_text(
            "🛡️ **Scam Detection**\n\n"
            "Describe the investment opportunity or paste the suspicious message.\n\n"
            "I'll check it against known fraud patterns.",
            parse_mode='Markdown'
        )
    
    elif action == 'dashboard':
        # Call agent to generate dashboard
        result = await run_agent_graph(user_id, "show my dashboard", "dashboard")
        await query.message.reply_text(result, parse_mode='Markdown')

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
    
    elif state == 'awaiting_expense':
        result = await run_agent_graph(user_id, message, "expense")
        user_states[user_id] = 'general'
    
    elif state == 'awaiting_stock':
        result = await run_agent_graph(user_id, message, "stock")
        user_states[user_id] = 'general'
    
    elif state == 'awaiting_fraud_check':
        result = await run_agent_graph(user_id, message, "fraud")
        user_states[user_id] = 'general'
    
    else:
        # General conversation - let the agent decide
        result = await run_agent_graph(user_id, message, "general")
    
    await update.message.reply_text(result, parse_mode='Markdown')

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
    print("=" * 50)
    print("🤖 KaroBuddy Financial Advisor Bot")
    print("=" * 50)
    print("✅ Bot is running and ready to help!")
    print("📱 Open Telegram and start chatting with your bot")
    print("🛑 Press Ctrl+C to stop the bot")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
