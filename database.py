import sqlite3
import chromadb
from datetime import datetime
from typing import Optional, List, Tuple

class DatabaseManager:
    """Manages SQLite and ChromaDB connections."""
    
    def __init__(self, db_path: str = "karobuddy.db"):
        self.db_path = db_path
        self.conn = None
        self.chroma_client = None
        self.initialize()
    
    def initialize(self):
        """Initialize both SQLite and ChromaDB."""
        self.conn = self._init_sqlite()
        self.chroma_client = self._init_chromadb()
    
    def _init_sqlite(self) -> sqlite3.Connection:
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            income_type TEXT,
            risk_profile TEXT DEFAULT 'medium',
            language TEXT DEFAULT 'en',
            created_at TEXT
        )''')
        
        # Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount REAL,
            type TEXT,
            category TEXT,
            description TEXT,
            date TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )''')
        
        # Financial goals table
        c.execute('''CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            goal_name TEXT,
            target_amount REAL,
            current_amount REAL DEFAULT 0,
            deadline TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )''')
        
        # Conversation history table
        c.execute('''CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            message TEXT,
            response TEXT,
            agent_used TEXT,
            timestamp TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )''')
        
        # DFG Engine: Dynamic Financial Genome table
        c.execute('''CREATE TABLE IF NOT EXISTS dynamic_financial_genome (
            user_id INTEGER PRIMARY KEY,
            income_volatility_score REAL,
            predicted_cash_flow_json TEXT,
            last_updated TEXT,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )''')

        # DFG Engine: Behavioral Biases table
        c.execute('''CREATE TABLE IF NOT EXISTS behavioral_biases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bias_type TEXT,
            event_timestamp TEXT,
            description TEXT,
            related_transaction_ids_json TEXT,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )''')

        # DFG Engine: Dynamic Budgets table
        c.execute('''CREATE TABLE IF NOT EXISTS dynamic_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            budget_period TEXT,
            recommended_allocations_json TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )''')
        
        conn.commit()
        return conn
    
    def _init_chromadb(self) -> chromadb.Client:
        """Initialize ChromaDB for fraud pattern detection."""
        client = chromadb.Client()
        
        # Create collection for fraud patterns
        fraud_collection = client.get_or_create_collection("fraud_patterns")
        
        # Seed with common scam patterns
        scam_examples = [
            "guaranteed returns double your money in 30 days risk free investment",
            "limited time offer join now passive income no effort required",
            "recovery service send bitcoin unlock your wallet frozen funds",
            "trading bot automatic profits 100% success rate guaranteed",
            "mlm network marketing be your own boss financial freedom pyramid",
            "crypto investment scheme high returns low risk quick money",
            "forex trading signals guaranteed profit daily returns",
            "binary options trading system never lose money",
            "ponzi scheme investment club exclusive membership",
            "get rich quick work from home unlimited income"
        ]
        
        # Check if collection is empty before adding
        try:
            existing = fraud_collection.get()
            if not existing['ids']:
                fraud_collection.add(
                    documents=scam_examples,
                    ids=[f"scam_{i}" for i in range(len(scam_examples))],
                    metadatas=[{"type": "fraud", "severity": "high"} for _ in scam_examples]
                )
        except:
            fraud_collection.add(
                documents=scam_examples,
                ids=[f"scam_{i}" for i in range(len(scam_examples))],
                metadatas=[{"type": "fraud", "severity": "high"} for _ in scam_examples]
            )
        
        return client
    
    def create_user(self, telegram_id: int, name: str = None, username: str = None):
        """Create or update user in database."""
        c = self.conn.cursor()
        c.execute("""INSERT OR REPLACE INTO users (telegram_id, name, username, created_at)
                     VALUES (?, ?, ?, ?)""",
                  (telegram_id, name, username, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user_language(self, telegram_id: int) -> str:
        """Get user's preferred language."""
        c = self.conn.cursor()
        c.execute("SELECT language FROM users WHERE telegram_id=?", (telegram_id,))
        result = c.fetchone()
        return result[0] if result else 'en'
    
    def set_user_language(self, telegram_id: int, language: str):
        """Set user's preferred language."""
        c = self.conn.cursor()
        c.execute("UPDATE users SET language=? WHERE telegram_id=?", (language, telegram_id))
        self.conn.commit()
    
    def log_transaction(self, telegram_id: int, amount: float, trans_type: str, 
                       category: str = None, description: str = None):
        """Log a financial transaction."""
        c = self.conn.cursor()
        c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (telegram_id, amount, trans_type, category, description, 
                   datetime.now().date().isoformat()))
        self.conn.commit()
    
    def get_transactions(self, telegram_id: int, days: int = 30, 
                        trans_type: Optional[str] = None) -> List[Tuple]:
        """Get transactions for a user."""
        c = self.conn.cursor()
        if trans_type:
            c.execute("""SELECT id, amount, type, category, description, date 
                        FROM transactions 
                        WHERE telegram_id=? AND type=? 
                        AND date > date('now', '-' || ? || ' days')
                        ORDER BY date DESC""",
                     (telegram_id, trans_type, days))
        else:
            c.execute("""SELECT id, amount, type, category, description, date 
                        FROM transactions 
                        WHERE telegram_id=? 
                        AND date > date('now', '-' || ? || ' days')
                        ORDER BY date DESC""",
                     (telegram_id, days))
        return c.fetchall()
    
    def save_conversation(self, telegram_id: int, message: str, 
                         response: str, agent_used: str = None):
        """Save conversation to history."""
        c = self.conn.cursor()
        c.execute("""INSERT INTO conversations (telegram_id, message, response, agent_used, timestamp)
                     VALUES (?, ?, ?, ?, ?)""",
                  (telegram_id, message, response, agent_used, datetime.now().isoformat()))
        self.conn.commit()
    
    def close(self):
        """Close database connections."""
        if self.conn:
            self.conn.close()

# Global database instance
db_manager = DatabaseManager()
db_conn = db_manager.conn
chroma_client = db_manager.chroma_client
