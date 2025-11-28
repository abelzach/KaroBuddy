from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from agent_graph import run_agent_graph
from database import db_manager
from translations import get_text, get_language_keyboard
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

def get_user_lang(user_id: int) -> str:
    """Get user's preferred language."""
    return db_manager.get_user_language(user_id)

def get_main_menu_keyboard(lang: str = "en"):
    """Get the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(get_text("log_income", lang), callback_data='income'),
            InlineKeyboardButton(get_text("log_expense", lang), callback_data='expense')
        ],
        [
            InlineKeyboardButton(get_text("my_goals", lang), callback_data='goals'),
            InlineKeyboardButton(get_text("dashboard", lang), callback_data='dashboard')
        ],
        [
            InlineKeyboardButton(get_text("stock_analysis", lang), callback_data='stock'),
            InlineKeyboardButton(get_text("investment_ideas", lang), callback_data='invest')
        ],
        [
            InlineKeyboardButton(get_text("generate_report", lang), callback_data='report'),
            InlineKeyboardButton(get_text("scam_check", lang), callback_data='fraud')
        ],
        [
            InlineKeyboardButton(get_text("help", lang), callback_data='help'),
            InlineKeyboardButton(get_text("change_language", lang), callback_data='change_language')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_goal_menu_keyboard(lang: str = "en"):
    """Get the goal management keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(get_text("create_goal", lang), callback_data='goal_create'),
            InlineKeyboardButton(get_text("view_goals", lang), callback_data='goal_list')
        ],
        [
            InlineKeyboardButton(get_text("allocate_funds", lang), callback_data='goal_allocate'),
            InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_investment_menu_keyboard(lang: str = "en"):
    """Get the investment recommendation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(get_text("stock_suggestions", lang), callback_data='invest_stocks'),
            InlineKeyboardButton(get_text("mutual_funds", lang), callback_data='invest_mf')
        ],
        [
            InlineKeyboardButton(get_text("set_risk_profile", lang), callback_data='risk_profile'),
            InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_risk_profile_keyboard(lang: str = "en"):
    """Get risk profile selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(get_text("low_risk", lang), callback_data='risk_low')],
        [InlineKeyboardButton(get_text("medium_risk", lang), callback_data='risk_medium')],
        [InlineKeyboardButton(get_text("high_risk", lang), callback_data='risk_high')],
        [InlineKeyboardButton(get_text("back", lang), callback_data='invest')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_report_menu_keyboard(lang: str = "en"):
    """Get report generation menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(get_text("spending_report", lang), callback_data='report_spending'),
            InlineKeyboardButton(get_text("investment_report", lang), callback_data='report_investment')
        ],
        [
            InlineKeyboardButton(get_text("comprehensive_report", lang), callback_data='report_comprehensive')
        ],
        [
            InlineKeyboardButton(get_text("pdf_format", lang), callback_data='report_format_pdf'),
            InlineKeyboardButton(get_text("excel_format", lang), callback_data='report_format_excel')
        ],
        [
            InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')
        ]
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
    
    # Get user's language preference
    lang = get_user_lang(user.id)
    
    welcome_message = f"""👋 **{get_text('welcome', lang)}**

{get_text('welcome_message', lang, name=user.first_name)}

**{get_text('what_i_can_do', lang)}**

{get_text('income_expense_tracking', lang)}
   {get_text('income_expense_desc', lang)}

{get_text('goal_based_planning', lang)}
   {get_text('goal_based_desc', lang)}

{get_text('investment_intelligence', lang)}
   {get_text('investment_desc', lang)}

{get_text('smart_recommendations', lang)}
   {get_text('smart_rec_desc', lang)}

{get_text('scam_protection', lang)}
   {get_text('scam_desc', lang)}

{get_text('financial_dashboard', lang)}
   {get_text('dashboard_desc', lang)}

**{get_text('quick_start', lang)}**
{get_text('quick_start_1', lang)}
{get_text('quick_start_2', lang)}
{get_text('quick_start_3', lang)}
{get_text('quick_start_4', lang)}

{get_text('choose_option', lang)} 👇"""
    
    await update.message.reply_text(
        welcome_message, 
        reply_markup=get_main_menu_keyboard(lang), 
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    help_text = f"""🤖 **{get_text('help_guide', lang)}**

**{get_text('main_features', lang)}**

**1️⃣ {get_text('income_expense_tracking', lang)}**
   • "I earned 25000" / "मैंने 25000 कमाए"
   • "Spent 2500 on groceries" / "किराने पर 2500 खर्च किए"
   • Automatic categorization / स्वचालित वर्गीकरण

**2️⃣ {get_text('goal_based_planning', lang)}**
   • "Create goal Emergency Fund with target 100000"
   • "Allocate 5000 to Emergency Fund"
   • "Show my goals" / "मेरे लक्ष्य दिखाएं"

**3️⃣ {get_text('stock_analysis', lang)}**
   • "Is RELIANCE a good stock?" / "क्या RELIANCE अच्छा स्टॉक है?"
   • "Check TCS stock" / "TCS स्टॉक जांचें"
   • Get comprehensive analysis / व्यापक विश्लेषण प्राप्त करें

**4️⃣ {get_text('investment_intelligence', lang)}**
   • Set your risk profile / अपना जोखिम प्रोफाइल सेट करें
   • Get personalized recommendations / व्यक्तिगत सिफारिशें प्राप्त करें
   • Risk-adjusted suggestions / जोखिम-समायोजित सुझाव

**5️⃣ {get_text('scam_protection', lang)}**
   • "Is this a scam: [paste message]"
   • AI-powered fraud detection / AI-संचालित धोखाधड़ी पहचान
   • Protect your money / अपने पैसे की रक्षा करें

**6️⃣ {get_text('dashboard', lang)}**
   • View income, expenses, savings / आय, व्यय, बचत देखें
   • Track goal progress / लक्ष्य प्रगति ट्रैक करें
   • Financial overview / वित्तीय अवलोकन

**💡 PRO TIPS:**

✅ Set goals to separate savings from expenses
✅ Allocate to goals - it won't count as spending
✅ Set your risk profile for better recommendations
✅ Always verify investment opportunities
✅ Build 3-6 month emergency fund first

**🎯 COMMANDS:**
/start - Main menu / मुख्य मेनू
/dashboard - Financial summary / वित्तीय सारांश
/help - This help message / यह सहायता संदेश

**Need specific help?** Just ask me naturally! I understand conversational language. 😊"""
    
    keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    await update.message.chat.send_action("typing")
    result, file_paths = await run_agent_graph(user_id, "show my dashboard", "dashboard")
    
    keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(result, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    lang = get_user_lang(user_id)
    
    if action == 'main_menu':
        welcome_message = f"""🏠 **{get_text('main_menu', lang)}**

{get_text('choose_option', lang)}"""
        await query.message.edit_text(
            welcome_message,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode='Markdown'
        )
    
    elif action == 'change_language':
        await query.message.edit_text(
            get_text('select_language', lang),
            reply_markup=get_language_keyboard(),
            parse_mode='Markdown'
        )
    
    elif action.startswith('lang_'):
        new_lang = action.replace('lang_', '')
        db_manager.set_user_language(user_id, new_lang)
        
        await query.message.edit_text(
            get_text('language_changed', new_lang),
            reply_markup=get_main_menu_keyboard(new_lang),
            parse_mode='Markdown'
        )
    
    elif action == 'income':
        user_states[user_id] = 'awaiting_income'
        await query.message.reply_text(
            f"{get_text('log_income_title', lang)}\n\n"
            f"{get_text('log_income_prompt', lang)}\n\n"
            f"{get_text('log_income_examples', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'expense':
        user_states[user_id] = 'awaiting_expense'
        await query.message.reply_text(
            f"{get_text('log_expense_title', lang)}\n\n"
            f"{get_text('log_expense_prompt', lang)}\n\n"
            f"{get_text('log_expense_examples', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'goals':
        await query.message.edit_text(
            f"{get_text('goal_management', lang)}\n\n"
            f"{get_text('goal_management_desc', lang)}",
            reply_markup=get_goal_menu_keyboard(lang),
            parse_mode='Markdown'
        )
    
    elif action == 'goal_create':
        user_states[user_id] = 'awaiting_goal_create'
        await query.message.reply_text(
            f"{get_text('create_goal_title', lang)}\n\n"
            f"{get_text('create_goal_prompt', lang)}\n\n"
            f"{get_text('create_goal_format', lang)}\n\n"
            f"{get_text('create_goal_examples', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'goal_list':
        await query.message.chat.send_action("typing")
        result, _ = await run_agent_graph(user_id, "show my goals", "goal")
        keyboard = [[InlineKeyboardButton(get_text("back_to_goals", lang), callback_data='goals')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'goal_allocate':
        user_states[user_id] = 'awaiting_goal_allocate'
        await query.message.reply_text(
            f"{get_text('allocate_funds_title', lang)}\n\n"
            f"{get_text('allocate_funds_prompt', lang)}\n\n"
            f"{get_text('allocate_funds_format', lang)}\n\n"
            f"{get_text('allocate_funds_examples', lang)}\n\n"
            f"{get_text('allocate_funds_tip', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'stock':
        user_states[user_id] = 'awaiting_stock'
        await query.message.reply_text(
            f"{get_text('stock_analysis_title', lang)}\n\n"
            f"{get_text('stock_analysis_prompt', lang)}\n\n"
            f"{get_text('stock_quick_check', lang)}\n\n"
            f"{get_text('stock_detailed', lang)}\n\n"
            f"{get_text('popular_stocks', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'invest':
        await query.message.edit_text(
            f"{get_text('investment_recommendations', lang)}\n\n"
            f"{get_text('investment_rec_desc', lang)}\n\n"
            f"{get_text('what_would_you_like', lang)}",
            reply_markup=get_investment_menu_keyboard(lang),
            parse_mode='Markdown'
        )
    
    elif action == 'invest_stocks':
        user_states[user_id] = 'awaiting_invest_stocks'
        await query.message.reply_text(
            f"{get_text('stock_suggestions', lang)}\n\n"
            f"{get_text('investment_rec_desc', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'invest_mf':
        user_states[user_id] = 'awaiting_invest_mf'
        await query.message.reply_text(
            f"{get_text('mutual_funds', lang)}\n\n"
            f"{get_text('investment_rec_desc', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'risk_profile':
        await query.message.edit_text(
            f"{get_text('set_risk_profile_title', lang)}\n\n"
            f"{get_text('risk_profile_desc', lang)}\n\n"
            f"{get_text('choose_risk_tolerance', lang)}",
            reply_markup=get_risk_profile_keyboard(lang),
            parse_mode='Markdown'
        )
    
    elif action.startswith('risk_'):
        risk_level = action.replace('risk_', '')
        await query.message.chat.send_action("typing")
        result, _ = await run_agent_graph(user_id, f"Set my risk profile to {risk_level}", "risk_profile")
        keyboard = [[InlineKeyboardButton(get_text("back_to_investments", lang), callback_data='invest')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'fraud':
        user_states[user_id] = 'awaiting_fraud_check'
        await query.message.reply_text(
            f"{get_text('scam_detection', lang)}\n\n"
            f"{get_text('scam_detection_prompt', lang)}\n\n"
            f"{get_text('scam_check_for', lang)}\n\n"
            f"{get_text('scam_example', lang)}",
            parse_mode='Markdown'
        )
    
    elif action == 'dashboard':
        await query.message.chat.send_action("typing")
        result, _ = await run_agent_graph(user_id, "show my dashboard", "dashboard")
        keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'report':
        await query.message.edit_text(
            f"{get_text('report_generation', lang)}\n\n"
            f"{get_text('report_desc', lang)}\n\n"
            f"{get_text('report_types', lang)}\n\n"
            f"{get_text('formats_available', lang)}\n\n"
            f"{get_text('choose_report', lang)}",
            reply_markup=get_report_menu_keyboard(lang),
            parse_mode='Markdown'
        )
    
    elif action.startswith('report_'):
        # Store report preferences
        if 'report_type' not in context.user_data:
            context.user_data['report_type'] = 'comprehensive'
        if 'report_format' not in context.user_data:
            context.user_data['report_format'] = 'pdf'
        
        if action == 'report_spending':
            context.user_data['report_type'] = 'spending'
            await query.answer("✅ Spending report selected")
        elif action == 'report_investment':
            context.user_data['report_type'] = 'investment'
            await query.answer("✅ Investment report selected")
        elif action == 'report_comprehensive':
            context.user_data['report_type'] = 'comprehensive'
            await query.answer("✅ Comprehensive report selected")
        elif action == 'report_format_pdf':
            context.user_data['report_format'] = 'pdf'
            await query.answer("✅ PDF format selected")
        elif action == 'report_format_excel':
            context.user_data['report_format'] = 'excel'
            await query.answer("✅ Excel format selected")
        
        # Generate report
        report_type = context.user_data.get('report_type', 'comprehensive')
        report_format = context.user_data.get('report_format', 'pdf')
        
        await query.message.reply_text(
            get_text('generating_report', lang, type=report_type, format=report_format.upper()),
            parse_mode='Markdown'
        )
        
        await query.message.chat.send_action("upload_document")
        
        # Generate the report
        message_text = f"generate {report_type} report in {report_format} format"
        result, file_paths = await run_agent_graph(user_id, message_text, "report_generation")
        
        # Send the files to user
        if file_paths:
            for file_path in file_paths:
                try:
                    with open(file_path, 'rb') as f:
                        if file_path.endswith('.pdf'):
                            await query.message.reply_document(
                                document=f,
                                filename=file_path.split('/')[-1],
                                caption=f"📄 {report_type.title()} Report"
                            )
                        elif file_path.endswith('.xlsx'):
                            await query.message.reply_document(
                                document=f,
                                filename=file_path.split('/')[-1],
                                caption=f"📊 {report_type.title()} Report"
                            )
                except Exception as e:
                    logger.error(f"Error sending file {file_path}: {e}")
        
        keyboard = [[InlineKeyboardButton(get_text("generate_another", lang), callback_data='report')],
                   [InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await query.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == 'help':
        help_text = f"""🤖 **{get_text('quick_help', lang)}**

**💰 {get_text('income_expense_tracking', lang)}:**
"I earned 25000" / "मैंने 25000 कमाए"
"Spent 2500 on groceries" / "किराने पर 2500 खर्च किए"

**🎯 {get_text('goal_based_planning', lang)}:**
"Create goal Emergency Fund with target 100000"
"Allocate 5000 to Emergency Fund"

**📈 {get_text('investment_intelligence', lang)}:**
"Is RELIANCE a good stock?" / "क्या RELIANCE अच्छा स्टॉक है?"
"Suggest low risk mutual funds"

**📄 {get_text('generate_report', lang)}:**
"Generate spending report"
"Create comprehensive report in Excel"

**🛡️ {get_text('scam_check', lang)}:**
"Is this a scam: [message]"

Use /help for detailed guide."""
        keyboard = [[InlineKeyboardButton(get_text("full_help_guide", lang), callback_data='full_help')],
                   [InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif action == 'full_help':
        await help_command(query, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id
    message = update.message.text
    lang = get_user_lang(user_id)
    
    # Get user state
    state = user_states.get(user_id, 'general')
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Route to appropriate agent based on state
    if state == 'awaiting_income':
        result, file_paths = await run_agent_graph(user_id, message, "income")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_expense':
        result, file_paths = await run_agent_graph(user_id, message, "expense")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_stock':
        result, file_paths = await run_agent_graph(user_id, message, "stock_analysis" if "good" in message.lower() else "stock")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_fraud_check':
        result, file_paths = await run_agent_graph(user_id, message, "fraud")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_menu", lang), callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_goal_create':
        result, file_paths = await run_agent_graph(user_id, message, "goal")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_goals", lang), callback_data='goals')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_goal_allocate':
        result, file_paths = await run_agent_graph(user_id, message, "goal")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_goals", lang), callback_data='goals')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_invest_stocks':
        result, file_paths = await run_agent_graph(user_id, message, "investment_recommendation")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_investments", lang), callback_data='invest')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_invest_mf':
        result, file_paths = await run_agent_graph(user_id, message, "investment_recommendation")
        user_states[user_id] = 'general'
        keyboard = [[InlineKeyboardButton(get_text("back_to_investments", lang), callback_data='invest')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
    
    else:
        # General conversation - let the agent decide
        result, file_paths = await run_agent_graph(user_id, message, "general")
        
        # Send any files if generated
        if file_paths:
            for file_path in file_paths:
                try:
                    with open(file_path, 'rb') as f:
                        if file_path.endswith('.pdf'):
                            await update.message.reply_document(
                                document=f,
                                filename=file_path.split('/')[-1],
                                caption="📄 Your Financial Report"
                            )
                        elif file_path.endswith('.xlsx'):
                            await update.message.reply_document(
                                document=f,
                                filename=file_path.split('/')[-1],
                                caption="📊 Your Financial Report"
                            )
                except Exception as e:
                    logger.error(f"Error sending file {file_path}: {e}")
        
        keyboard = [[InlineKeyboardButton(get_text("main_menu", lang), callback_data='main_menu')]]
        await update.message.reply_text(result, reply_markup=InlineKeyboardMarkup(keyboard))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else None
        lang = get_user_lang(user_id) if user_id else 'en'
        
        await update.effective_message.reply_text(
            get_text('error_occurred', lang)
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
    print("🤖 KaroBuddy Financial Advisor Bot - Multi-Language Version")
    print("=" * 60)
    print("✅ Bot is running and ready to help!")
    print("📱 Open Telegram and start chatting with your bot")
    print("")
    print("🌐 LANGUAGE SUPPORT:")
    print("   • English (en)")
    print("   • हिंदी / Hindi (hi)")
    print("")
    print("🎯 FEATURES:")
    print("   • Multi-language interface")
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
