import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages
from database import db_conn
import hashlib
import secrets
from agent_graph import run_agent_graph
import asyncio

# Page configuration
st.set_page_config(
    page_title="KaroBuddy - AI Financial Advisor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --success-color: #2ca02c;
        --danger-color: #d62728;
        --background-color: #0e1117;
        --card-background: #1e2130;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom card styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
    }
    
    .metric-card h3 {
        color: white;
        margin: 0;
        font-size: 14px;
        font-weight: 500;
    }
    
    .metric-card h2 {
        color: white;
        margin: 10px 0 0 0;
        font-size: 32px;
        font-weight: 700;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1e2130;
    }
    
    /* Button styling */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #667eea;
        color: white;
        font-weight: 600;
    }
    
    .stButton>button:hover {
        background-color: #764ba2;
        border-color: #764ba2;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        background-color: #2b313e;
        border-left: 4px solid #667eea;
    }
    
    .chat-message.assistant {
        background-color: #1e2130;
        border-left: 4px solid #2ca02c;
    }
    
    /* Goal progress bar */
    .goal-progress {
        background-color: #2b313e;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Transaction item */
    .transaction-item {
        background-color: #2b313e;
        padding: 12px;
        border-radius: 6px;
        margin: 8px 0;
        border-left: 3px solid #667eea;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        margin: 0.5rem 0 0 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state at the module level
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'telegram_id' not in st.session_state:
    st.session_state.telegram_id = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = time.time()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def check_session_timeout():
    """Check if the session has timed out (30 minutes of inactivity)."""
    current_time = time.time()
    inactive_seconds = current_time - st.session_state.last_activity
    
    if inactive_seconds > 1800:  # 30 minutes in seconds
        st.session_state.authenticated = False
        st.session_state.telegram_id = None
        st.session_state.last_activity = current_time
        st.rerun()
    
    st.session_state.last_activity = current_time

def main():
    """Main application logic."""
    # Initialize session state
    if 'telegram_id' not in st.session_state:
        st.session_state.telegram_id = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
    
    # Check session timeout
    check_session_timeout()

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

def generate_auth_token():
    """Generate a unique authentication token."""
    return secrets.token_urlsafe(32)

def verify_telegram_auth(telegram_id: int, auth_code: str) -> bool:
    """Verify Telegram authentication code."""
    # In production, this would verify with Telegram's API
    # For now, we'll use a simple verification
    expected_code = hashlib.sha256(f"{telegram_id}:karobuddy".encode()).hexdigest()[:6]
    return auth_code.upper() == expected_code.upper()

def get_user_data(telegram_id: int):
    """Fetch user data from database."""
    c = db_conn.cursor()
    c.execute("SELECT name, username, risk_profile, language FROM users WHERE telegram_id=?", (telegram_id,))
    return c.fetchone()

def get_dashboard_data(telegram_id: int, days: int = 30):
    """Get comprehensive dashboard data."""
    c = db_conn.cursor()
    
    # Income
    c.execute("""SELECT SUM(amount) FROM transactions
                 WHERE telegram_id=? AND type='income'
                 AND date > date('now', '-' || ? || ' days')""", (telegram_id, days))
    income = c.fetchone()[0] or 0
    
    # Expenses
    c.execute("""SELECT SUM(amount) FROM transactions
                 WHERE telegram_id=? AND type='expense'
                 AND date > date('now', '-' || ? || ' days')""", (telegram_id, days))
    expense = c.fetchone()[0] or 0
    
    # Goal allocations
    c.execute("""SELECT SUM(amount) FROM transactions
                 WHERE telegram_id=? AND type='goal_allocation'
                 AND date > date('now', '-' || ? || ' days')""", (telegram_id, days))
    goal_allocation = c.fetchone()[0] or 0
    
    # Goals
    c.execute("""SELECT goal_name, target_amount, current_amount, deadline, status
                 FROM goals WHERE telegram_id=? ORDER BY created_at DESC""", (telegram_id,))
    goals = c.fetchall()
    
    # Recent transactions
    c.execute("""SELECT amount, type, category, description, date
                 FROM transactions WHERE telegram_id=?
                 ORDER BY date DESC LIMIT 10""", (telegram_id,))
    transactions = c.fetchall()
    
    # Transaction history for charts
    c.execute("""SELECT date, SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
                 SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
                 FROM transactions WHERE telegram_id=?
                 AND date > date('now', '-' || ? || ' days')
                 GROUP BY date ORDER BY date""", (telegram_id, days))
    daily_data = c.fetchall()
    
    return {
        'income': income,
        'expense': expense,
        'goal_allocation': goal_allocation,
        'savings': income - expense - goal_allocation,
        'goals': goals,
        'transactions': transactions,
        'daily_data': daily_data
    }

def login_page():
    """Display login page with Telegram authentication."""
    st.markdown("""
    <div class="main-header">
        <h1>💰 KaroBuddy</h1>
        <p>Your AI-Powered Financial Advisor</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login with Telegram")
        st.info("To access your financial data, please authenticate using your Telegram account.")
        
        telegram_id = st.text_input("Telegram ID", placeholder="Enter your Telegram ID")
        
        if telegram_id:
            st.markdown("---")
            st.markdown("#### Verification Steps:")
            st.markdown("""
            1. Open your Telegram app
            2. Send `/auth` to @KaroBuddyBot
            3. Copy the 6-digit code you receive
            4. Enter it below
            """)
            
            auth_code = st.text_input("Authentication Code", placeholder="Enter 6-digit code", max_chars=6)
            
            if st.button("🔓 Login", key="login_btn"):
                if verify_telegram_auth(int(telegram_id), auth_code):
                    user_data = get_user_data(int(telegram_id))
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.telegram_id = int(telegram_id)
                        st.session_state.user_name = user_data[0]
                        st.session_state.auth_token = generate_auth_token()
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ User not found. Please start the bot on Telegram first.")
                else:
                    st.error("❌ Invalid authentication code. Please try again.")
        
        st.markdown("---")
        st.markdown("### 📱 Don't have an account?")
        st.markdown("1. Open Telegram and search for **@KaroBuddyBot**")
        st.markdown("2. Send `/start` to create your account")
        st.markdown("3. Come back here to login")

def dashboard_page():
    """Display main dashboard."""
    data = get_dashboard_data(st.session_state.telegram_id)
    
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1>Welcome back, {st.session_state.user_name}! 👋</h1>
        <p>Your Financial Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #2ca02c 0%, #1f8a1f 100%);">
            <h3>💰 Total Income</h3>
            <h2>₹{data['income']:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #d62728 0%, #a01f20 100%);">
            <h3>💸 Total Expenses</h3>
            <h2>₹{data['expense']:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #ff7f0e 0%, #cc6600 100%);">
            <h3>🎯 Goal Allocations</h3>
            <h2>₹{data['goal_allocation']:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        savings_color = "#2ca02c" if data['savings'] > 0 else "#d62728"
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, {savings_color} 0%, {savings_color}dd 100%);">
            <h3>💵 Net Savings</h3>
            <h2>₹{data['savings']:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Income vs Expenses")
        if data['daily_data']:
            df = pd.DataFrame(data['daily_data'], columns=['Date', 'Income', 'Expense'])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Income'], name='Income',
                                    line=dict(color='#2ca02c', width=3)))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Expense'], name='Expense',
                                    line=dict(color='#d62728', width=3)))
            fig.update_layout(
                template='plotly_dark',
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transaction data available yet.")
    
    with col2:
        st.markdown("### 🎯 Financial Goals Progress")
        if data['goals']:
            goal_names = [g[0] for g in data['goals'][:5]]
            goal_progress = [(g[2]/g[1]*100) if g[1] > 0 else 0 for g in data['goals'][:5]]
            
            fig = go.Figure(go.Bar(
                x=goal_progress,
                y=goal_names,
                orientation='h',
                marker=dict(color=goal_progress, colorscale='Viridis')
            ))
            fig.update_layout(
                template='plotly_dark',
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis_title="Progress (%)",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No goals created yet. Create your first goal!")
    
    # Recent Transactions and Goals
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📝 Recent Transactions")
        if data['transactions']:
            for trans in data['transactions'][:5]:
                amount, trans_type, category, desc, date = trans
                icon = "💰" if trans_type == "income" else "💸" if trans_type == "expense" else "🎯"
                color = "#2ca02c" if trans_type == "income" else "#d62728" if trans_type == "expense" else "#ff7f0e"
                
                st.markdown(f"""
                <div class="transaction-item" style="border-left-color: {color};">
                    <div style="display: flex; justify-content: space-between;">
                        <span>{icon} <strong>{desc or category}</strong></span>
                        <span style="color: {color}; font-weight: bold;">₹{amount:,.0f}</span>
                    </div>
                    <div style="font-size: 0.85em; color: #888; margin-top: 5px;">{date}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No transactions yet. Start tracking your finances!")
    
    with col2:
        st.markdown("### 🎯 Active Goals")
        if data['goals']:
            for goal in data['goals'][:5]:
                name, target, current, deadline, status = goal
                progress = (current / target * 100) if target > 0 else 0
                
                st.markdown(f"""
                <div class="goal-progress">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong>{name}</strong>
                        <span>{progress:.1f}%</span>
                    </div>
                    <div style="background-color: #1e2130; border-radius: 10px; height: 8px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                                    width: {progress}%; height: 100%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85em; color: #888;">
                        <span>₹{current:,.0f} / ₹{target:,.0f}</span>
                        <span>📅 {deadline}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No goals yet. Create your first financial goal!")

def chat_page():
    """AI Chat interface."""
    st.markdown("""
    <div class="main-header">
        <h1>💬 Chat with KaroBuddy AI</h1>
        <p>Ask me anything about your finances!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history if not exists
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history using Streamlit's native chat components
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    
    # Chat input
    
    # Suggested Actions
    if 'dfg_confirmation' not in st.session_state:
        st.session_state.dfg_confirmation = False

    if st.session_state.dfg_confirmation:
        st.markdown("""
        <div style="background-color: #1e2130; padding: 20px; border-radius: 10px; border: 1px solid #667eea; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">🧬 DFG Analysis</h3>
            <p><strong>Dynamic Financial Genome (DFG)</strong> analysis uses your transaction history to:</p>
            <ul>
                <li>🔮 Predict your future cash flow</li>
                <li>📊 Calculate your income volatility score</li>
                <li>💡 Generate a personalized dynamic budget</li>
            </ul>
            <p style="font-size: 0.9em; color: #aaa;">This will analyze your last 90 days of transactions.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Generate Analysis", use_container_width=True):
                st.session_state.dfg_confirmation = False
                action_clicked = "Analyze my DFG and predict cash flow"
        with col2:
            if st.button("❌ Go Back", use_container_width=True):
                st.session_state.dfg_confirmation = False
                st.rerun()
    else:
        st.markdown("### Suggested Actions")
        col1, col2, col3 = st.columns(3)
        
        action_clicked = None
        
        with col1:
            if st.button("🔮 Run DFG Analysis", use_container_width=True):
                st.session_state.dfg_confirmation = True
                st.rerun()
                
        with col2:
            if st.button("📊 Generate Report", use_container_width=True):
                 action_clicked = "Generate a comprehensive financial report"
                 
        with col3:
            if st.button("💡 Investment Tips", use_container_width=True):
                action_clicked = "Suggest investments based on my risk profile"

    # Handle button clicks
    if action_clicked:
        # Add user message
        st.session_state.chat_history.append({'role': 'user', 'content': action_clicked})
        
        # Get AI response
        with st.spinner("Analyzing..."):
            try:
                response, _ = asyncio.run(run_agent_graph(
                    st.session_state.telegram_id,
                    action_clicked,
                    "general" # Router will handle intent
                ))
                st.session_state.chat_history.append({'role': 'assistant', 'content': response})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

    if prompt := st.chat_input("Ask me anything about your finances..."):
        # Add user message to chat history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response, _ = asyncio.run(run_agent_graph(
                        st.session_state.telegram_id,
                        prompt,
                        "general"
                    ))
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response
                    })
                except Exception as e:
                    error_msg = f"⚠️ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': error_msg
                    })

def goals_page():
    """Goals management page."""
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Financial Goals</h1>
        <p>Track and manage your financial goals</p>
    </div>
    """, unsafe_allow_html=True)
    
    data = get_dashboard_data(st.session_state.telegram_id)
    
    # Create new goal
    with st.expander("➕ Create New Goal", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            goal_name = st.text_input("Goal Name", placeholder="e.g., Emergency Fund")
            target_amount = st.number_input("Target Amount (₹)", min_value=1000, step=1000)
        with col2:
            deadline = st.date_input("Deadline", min_value=datetime.now().date())
            
        if st.button("Create Goal"):
            if goal_name and target_amount:
                c = db_conn.cursor()
                c.execute("""INSERT INTO goals (telegram_id, goal_name, target_amount, 
                             current_amount, deadline, status, created_at)
                             VALUES (?, ?, ?, 0, ?, 'active', ?)""",
                          (st.session_state.telegram_id, goal_name, target_amount,
                           deadline.isoformat(), datetime.now().isoformat()))
                db_conn.commit()
                st.success(f"✅ Goal '{goal_name}' created successfully!")
                st.rerun()
    
    st.markdown("---")
    
    # Display goals
    if data['goals']:
        for idx, goal in enumerate(data['goals']):
            name, target, current, deadline, status = goal
            progress = (current / target * 100) if target > 0 else 0
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"### {name}")
                    progress = min(progress / 100, 1.0)  # Clamp to [0.0, 1.0]
                    st.progress(progress)
                    st.caption(f"₹{current:,.0f} / ₹{target:,.0f} ({progress:.1f}%)")
                
                with col2:
                    st.metric("Remaining", f"₹{target - current:,.0f}")
                    st.caption(f"Deadline: {deadline}")
                
                with col3:
                    # Create a unique key using both the goal name and its index
                    goal_key = f"allocate_{name}_{idx}"
                    
                    # Initialize allocation amount in session state if not exists
                    if goal_key not in st.session_state:
                        st.session_state[goal_key] = 0
                    
                    # Use a callback to handle the allocation
                    def update_allocation(goal_name=name, goal_idx=idx):
                        amount_key = f"allocate_{goal_name}_{goal_idx}"
                        if amount_key in st.session_state:
                            allocate_amount = st.session_state[amount_key]
                            if allocate_amount > 0:
                                with st.spinner(f'Processing allocation of ₹{allocate_amount:,.0f}...'):
                                    c = db_conn.cursor()
                                    new_amount = current + allocate_amount
                                    c.execute("UPDATE goals SET current_amount=? WHERE telegram_id=? AND goal_name=?",
                                            (new_amount, st.session_state.telegram_id, goal_name))
                                    c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                                                VALUES (?, ?, 'goal_allocation', ?, ?, ?)""",
                                            (st.session_state.telegram_id, allocate_amount, goal_name,
                                             f"Allocated to {goal_name}", datetime.now().date().isoformat()))
                                    db_conn.commit()
                                    st.session_state[amount_key] = 0
                                    st.rerun()
                    
                    # Create the number input with on_change callback
                    allocate_amount = st.number_input(
                        "Allocate",
                        min_value=0,
                        step=100,
                        key=goal_key,
                        on_change=update_allocation,
                        args=(name, idx)
                    )
                    
                    if st.button("Add Funds", key=f"btn_{name}_{idx}"):
                        update_allocation(name, idx)
                
                st.markdown("---")
    else:
        st.info("No goals yet. Create your first financial goal above!")
    
    # Allocate funds to existing goals
    st.markdown("### 💸 Allocate Funds to Existing Goals")
    goals = data['goals']
    
    if goals:
        for idx, goal in enumerate(goals):
            goal_name = goal.get('name', 'Unknown')
            allocate_amount = st.number_input(
                f"Allocate funds to {goal_name}",
                min_value=0.0,
                step=100.0,
                key=f"allocate_{goal_name}_{idx}"  # Make key unique with index
            )
            
            if st.button(f"Allocate to {goal_name}", key=f"allocate_btn_{goal_name}_{idx}"):
                if allocate_amount > 0:
                    c = db_conn.cursor()
                    current_amount = goal[2]  # current_amount from goal data
                    new_amount = current_amount + allocate_amount
                    
                    # Update goal's current amount
                    c.execute("UPDATE goals SET current_amount=? WHERE telegram_id=? AND goal_name=?",
                            (new_amount, st.session_state.telegram_id, goal_name))
                    
                    # Record the transaction
                    c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                                VALUES (?, ?, 'goal_allocation', ?, ?, ?)""",
                            (st.session_state.telegram_id, allocate_amount, goal_name,
                             f"Allocated to {goal_name}", datetime.now().date().isoformat()))
                    db_conn.commit()
                    st.success(f"✅ Allocated ₹{allocate_amount:,.0f} to {goal_name}!")
                    st.rerun()
    else:
        st.info("No goals available to allocate funds. Create a goal first!")

def transactions_page():
    """Add income and expenses page."""
    st.markdown("""
    <div class="main-header">
        <h1>💰 Add Transactions</h1>
        <p>Log your income and expenses</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for Income and Expense
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Add Income")
        with st.form("income_form", clear_on_submit=True):
            income_amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=100.0,
                key="income_amount"
            )
            
            income_source = st.selectbox(
                "Source",
                ["Salary", "Freelance", "Business", "Investment Returns", "Gift", "Other"],
                key="income_source"
            )
            
            income_description = st.text_input(
                "Description (optional)",
                placeholder="e.g., Monthly salary, Client payment",
                key="income_desc"
            )
            
            income_date = st.date_input(
                "Date",
                value=datetime.now().date(),
                key="income_date"
            )
            
            submit_income = st.form_submit_button("➕ Add Income", use_container_width=True)
            
            if submit_income and income_amount > 0:
                try:
                    c = db_conn.cursor()
                    c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                                VALUES (?, ?, 'income', ?, ?, ?)""",
                            (st.session_state.telegram_id, income_amount, income_source,
                             income_description or f"{income_source} income", income_date.isoformat()))
                    db_conn.commit()
                    st.success(f"✅ Added income of ₹{income_amount:,.0f}!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    with col2:
        st.markdown("### 💸 Add Expense")
        with st.form("expense_form", clear_on_submit=True):
            expense_amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=100.0,
                key="expense_amount"
            )
            
            expense_category = st.selectbox(
                "Category",
                ["Food & Dining", "Transportation", "Shopping", "Bills & Utilities",
                 "Healthcare", "Entertainment", "Education", "Rent", "Other"],
                key="expense_category"
            )
            
            expense_description = st.text_input(
                "Description (optional)",
                placeholder="e.g., Grocery shopping, Electricity bill",
                key="expense_desc"
            )
            
            expense_date = st.date_input(
                "Date",
                value=datetime.now().date(),
                key="expense_date"
            )
            
            submit_expense = st.form_submit_button("➕ Add Expense", use_container_width=True)
            
            if submit_expense and expense_amount > 0:
                try:
                    c = db_conn.cursor()
                    c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                                VALUES (?, ?, 'expense', ?, ?, ?)""",
                            (st.session_state.telegram_id, expense_amount, expense_category,
                             expense_description or f"{expense_category} expense", expense_date.isoformat()))
                    db_conn.commit()
                    st.success(f"✅ Added expense of ₹{expense_amount:,.0f}!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    # Recent transactions
    st.markdown("### 📝 Recent Transactions")
    
    data = get_dashboard_data(st.session_state.telegram_id, days=30)
    
    if data['transactions']:
        # Create a dataframe for better display
        trans_data = []
        for trans in data['transactions'][:10]:
            amount, trans_type, category, desc, date = trans
            trans_data.append({
                'Date': date,
                'Type': trans_type.title(),
                'Category': category,
                'Description': desc,
                'Amount': f"₹{amount:,.0f}"
            })
        
        df = pd.DataFrame(trans_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Add your first transaction above!")



def dfg_page():
    """Dynamic Financial Genome Analysis Page."""
    st.markdown("""
    <div class="main-header">
        <h1>🧬 DFG Analysis</h1>
        <p>Your Dynamic Financial Genome & Forecast</p>
    </div>
    """, unsafe_allow_html=True)
    
    telegram_id = st.session_state.telegram_id
    c = db_conn.cursor()
    
    # Fetch latest DFG data
    c.execute("""SELECT income_volatility_score, predicted_cash_flow_json, last_updated 
                 FROM dynamic_financial_genome WHERE user_id=?""", (telegram_id,))
    dfg_data = c.fetchone()
    
    # Fetch latest budget
    c.execute("""SELECT recommended_allocations_json FROM dynamic_budgets 
                 WHERE user_id=? ORDER BY created_at DESC LIMIT 1""", (telegram_id,))
    budget_data = c.fetchone()
    
    if not dfg_data:
        st.info("No DFG analysis found. Go to the Chat and ask to 'Analyze my DFG' or 'Predict cash flow'!")
        if st.button("🔮 Run DFG Analysis Now"):
             with st.spinner("Crunching the numbers..."):
                 try:
                     response, _ = asyncio.run(run_agent_graph(telegram_id, "Analyze my DFG", "dfg_analysis"))
                     st.success("Analysis Complete!")
                     st.markdown(response)
                     time.sleep(2)
                     st.rerun()
                 except Exception as e:
                     st.error(f"Error: {str(e)}")
        return

    import json
    try:
        cash_flow = json.loads(dfg_data[1].replace("'", '"'))
        volatility = dfg_data[0]
    except:
        try:
            import ast
            cash_flow = ast.literal_eval(dfg_data[1])
            volatility = dfg_data[0]
        except:
             st.error("Error parsing DFG data.")
             return

    # --- Metrics Section ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Predicted Income", f"₹{cash_flow.get('predicted_income', 0):,.0f}")
    with col2:
        st.metric("Predicted Expenses", f"₹{cash_flow.get('predicted_expenses', 0):,.0f}")
    with col3:
        net_flow = cash_flow.get('net_cash_flow', 0)
        st.metric("Net Cash Flow", f"₹{net_flow:,.0f}", delta_color="normal" if net_flow >= 0 else "inverse")
    with col4:
        st.metric("Volatility Score", f"{volatility:.2f}", 
                  delta="High Risk" if volatility > 2 else "Stable", delta_color="inverse")

    st.markdown("---")

    # --- Cash Flow Graph ---
    st.subheader("📈 Cash Flow Projection")
    
    # 1. Get Historical Data (Last 90 days)
    c.execute("""SELECT date, SUM(amount) as net_amount 
                 FROM transactions 
                 WHERE telegram_id=? AND date > date('now', '-90 days')
                 GROUP BY date ORDER BY date""", (telegram_id,))
    history_rows = c.fetchall()
    
    history_df = pd.DataFrame(history_rows, columns=['Date', 'Net Amount'])
    history_df['Date'] = pd.to_datetime(history_df['Date'])
    
    # Cumulative Cash Flow
    if not history_df.empty:
        history_df['Cumulative'] = history_df['Net Amount'].cumsum()
    else:
        history_df['Cumulative'] = []

    # 2. Generate Prediction Data (Next 30 days)
    last_date = history_df['Date'].max() if not history_df.empty else datetime.now()
    last_val = history_df['Cumulative'].iloc[-1] if not history_df.empty else 0
    
    pred_net_daily = cash_flow.get('net_cash_flow', 0) / 30 
    
    future_dates = [last_date + timedelta(days=i) for i in range(1, 31)]
    future_vals = [last_val + (pred_net_daily * i) for i in range(1, 31)]
    
    future_df = pd.DataFrame({'Date': future_dates, 'Cumulative': future_vals})

    # 3. Plot
    fig = go.Figure()

    # Solid line for known points
    if not history_df.empty:
        fig.add_trace(go.Scatter(
            x=history_df['Date'], 
            y=history_df['Cumulative'],
            mode='lines+markers',
            name='Historical Cash Flow',
            line=dict(color='#2ca02c', width=3)
        ))

    # Dotted line for predicted cost/flow
    fig.add_trace(go.Scatter(
        x=future_df['Date'], 
        y=future_df['Cumulative'],
        mode='lines',
        name='Predicted Trend',
        line=dict(color='#ff7f0e', width=3, dash='dot')
    ))

    fig.update_layout(
        template='plotly_dark',
        height=400,
        title="Cash Flow Trajectory (90 Days History + 30 Days Forecast)",
        xaxis_title="Date",
        yaxis_title="Cumulative Net Cash Flow (₹)",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Dynamic Budget Section ---
    st.markdown("---")
    st.subheader("💡 Dynamic Budget Allocation")
    
    if budget_data:
        try:
            budget = json.loads(budget_data[0].replace("'", '"'))
        except:
             try:
                import ast
                budget = ast.literal_eval(budget_data[0])
             except:
                budget = {}
        
        b_col1, b_col2 = st.columns([1, 1])
        
        with b_col1:
            labels = ['Needs', 'Wants', 'Savings']
            values = [
                budget.get('needs_allocation', 0),
                budget.get('wants_allocation', 0),
                budget.get('savings_allocation', 0)
            ]
            
            fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig_donut.update_layout(template='plotly_dark', height=300, title="Recommended Allocation")
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with b_col2:
            st.markdown("### Budget Details")
            st.info(f"**Needs (50%):** ₹{values[0]:,.0f}\n\nEssential expenses like rent, food, utilities.")
            st.warning(f"**Wants (30%):** ₹{values[1]:,.0f}\n\nDiscretionary spending like dining out, entertainment.")
            st.success(f"**Savings (20%):** ₹{values[2]:,.0f}\n\nInvestments and emergency fund.")
            
            if budget.get('notes'):
                st.caption(f"*Note: {budget.get('notes')}*")
    else:
        st.info("No dynamic budget generated yet.")

def main():
    """Main application logic."""
    if not st.session_state.authenticated:
        login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.markdown(f"### 👤 {st.session_state.user_name}")
            st.markdown(f"**ID:** {st.session_state.telegram_id}")
            st.markdown("---")
            
            page = st.radio(
                "Navigation",
                ["📊 Dashboard", "💰 Add Transaction", " AI Chat", "🎯 Goals", "🧬 DFG Analysis"],
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.session_state.telegram_id = None
                st.session_state.user_name = None
                st.session_state.auth_token = None
                st.session_state.chat_history = []
                st.rerun()
        
        # Main content
        if page == "📊 Dashboard":
            dashboard_page()
        elif page == "💰 Add Transaction":
            transactions_page()
        elif page == "� AI Chat":
            chat_page()
        elif page == "🎯 Goals":
            goals_page()
        elif page == "🧬 DFG Analysis":
            dfg_page()

if __name__ == "__main__":
    main()
