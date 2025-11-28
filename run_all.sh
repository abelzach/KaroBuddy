#!/bin/bash
echo "============================================================"
echo "🚀 Starting KaroBuddy Services"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Streamlit not found. Installing dependencies..."
    pip3 install -r requirements.txt
fi

echo "✅ Dependencies OK"
echo ""

# Create logs directory
mkdir -p logs

# Start Telegram Bot in background
echo "🤖 Starting Telegram Bot..."
python3 main.py > logs/bot.log 2>&1 &
BOT_PID=$!
echo "✅ Telegram Bot started (PID: $BOT_PID)"
echo ""

# Wait a moment for bot to initialize
sleep 2

# Start Web App
echo "🌐 Starting Web Application..."
echo "📱 Web app will open in your browser automatically"
echo ""
echo "============================================================"
echo "✅ Both services are running!"
echo "============================================================"
echo ""
echo "📊 Telegram Bot: Running (PID: $BOT_PID)"
echo "🌐 Web App: http://localhost:8501"
echo ""
echo "📝 Logs:"
echo "   Bot: logs/bot.log"
echo "   Web: Terminal output"
echo ""
echo "🛑 To stop both services:"
echo "   Press Ctrl+C in this terminal"
echo "   Or run: kill $BOT_PID"
echo ""
echo "============================================================"
echo ""

# Start Streamlit (this will block)
streamlit run web_app.py

# Cleanup when Streamlit exits
echo ""
echo "🛑 Stopping services..."
kill $BOT_PID 2>/dev/null
echo "✅ All services stopped"
