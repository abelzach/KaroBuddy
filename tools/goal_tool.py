from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import db_conn
from datetime import datetime, timedelta
from typing import Optional

class GoalInput(BaseModel):
    telegram_id: int = Field(description="User's telegram ID")
    action: str = Field(description="Action: create, list, allocate, or delete")
    goal_name: Optional[str] = Field(default=None, description="Name of the goal")
    target_amount: Optional[float] = Field(default=None, description="Target amount for goal")
    deadline: Optional[str] = Field(default=None, description="Deadline for goal (YYYY-MM-DD)")
    allocation_amount: Optional[float] = Field(default=None, description="Amount to allocate to goal")

class GoalManagementTool(BaseTool):
    name: str = "goal_manager"
    description: str = "Manages financial goals - create, track, allocate funds, and monitor progress"
    args_schema: type[BaseModel] = GoalInput
    
    def _run(self, telegram_id: int, action: str, goal_name: str = None, 
             target_amount: float = None, deadline: str = None, 
             allocation_amount: float = None) -> str:
        """Manage financial goals."""
        try:
            c = db_conn.cursor()
            
            if action == "create":
                if not goal_name or not target_amount:
                    return "❌ Please provide goal name and target amount.\n\nExample: 'Create goal Emergency Fund with target 100000'"
                
                # Set default deadline if not provided (1 year from now)
                if not deadline:
                    deadline = (datetime.now() + timedelta(days=365)).date().isoformat()
                
                c.execute("""INSERT INTO goals (telegram_id, goal_name, target_amount, 
                             current_amount, deadline, status, created_at)
                             VALUES (?, ?, ?, 0, ?, 'active', ?)""",
                          (telegram_id, goal_name, target_amount, deadline, 
                           datetime.now().isoformat()))
                db_conn.commit()
                
                return f"""✅ Goal Created Successfully!

🎯 **{goal_name}**
💰 Target: ₹{target_amount:,.0f}
📅 Deadline: {deadline}
💵 Current: ₹0

💡 Tip: Use 'Allocate ₹5000 to {goal_name}' to add funds to this goal. Allocated funds won't count as expenses!"""
            
            elif action == "list":
                c.execute("""SELECT goal_name, target_amount, current_amount, deadline, status
                             FROM goals WHERE telegram_id=? ORDER BY created_at DESC""",
                          (telegram_id,))
                goals = c.fetchall()
                
                if not goals:
                    return """📋 **Your Financial Goals**

You haven't set any goals yet!

💡 Create your first goal:
• "Create goal Emergency Fund with target 100000"
• "Set goal Vacation with target 50000"
• "New goal House Down Payment with target 500000"

Goals help you save systematically and track progress! 🎯"""
                
                response = "📋 **Your Financial Goals**\n\n"
                total_target = 0
                total_current = 0
                
                for goal in goals:
                    name, target, current, deadline, status = goal
                    progress = (current / target * 100) if target > 0 else 0
                    total_target += target
                    total_current += current
                    
                    status_emoji = "✅" if status == "completed" else "🎯"
                    progress_bar = "🟩" * int(progress / 10) + "⬜" * (10 - int(progress / 10))
                    
                    response += f"""{status_emoji} **{name}**
💰 ₹{current:,.0f} / ₹{target:,.0f} ({progress:.1f}%)
{progress_bar}
📅 Deadline: {deadline}

"""
                
                response += f"""**Overall Progress:**
💵 Total Saved: ₹{total_current:,.0f}
🎯 Total Target: ₹{total_target:,.0f}
📊 Overall: {(total_current/total_target*100) if total_target > 0 else 0:.1f}%

💡 Allocate funds: "Allocate ₹5000 to Emergency Fund" """
                
                return response
            
            elif action == "allocate":
                if not goal_name or not allocation_amount:
                    return "❌ Please specify goal name and amount.\n\nExample: 'Allocate ₹5000 to Emergency Fund'"
                
                # Check if goal exists
                c.execute("""SELECT id, current_amount, target_amount FROM goals 
                             WHERE telegram_id=? AND goal_name=? AND status='active'""",
                          (telegram_id, goal_name))
                goal = c.fetchone()
                
                if not goal:
                    return f"❌ Goal '{goal_name}' not found or already completed.\n\nUse 'Show my goals' to see active goals."
                
                goal_id, current, target = goal
                new_amount = current + allocation_amount
                
                # Update goal
                c.execute("""UPDATE goals SET current_amount=? WHERE id=?""",
                          (new_amount, goal_id))
                
                # Log as goal allocation (not expense)
                c.execute("""INSERT INTO transactions (telegram_id, amount, type, category, description, date)
                             VALUES (?, ?, 'goal_allocation', ?, ?, ?)""",
                          (telegram_id, allocation_amount, goal_name, 
                           f"Allocated to {goal_name}", datetime.now().date().isoformat()))
                
                # Check if goal is completed
                if new_amount >= target:
                    c.execute("""UPDATE goals SET status='completed' WHERE id=?""", (goal_id,))
                    db_conn.commit()
                    return f"""🎉 **GOAL COMPLETED!** 🎉

🎯 **{goal_name}**
💰 ₹{new_amount:,.0f} / ₹{target:,.0f}

Congratulations! You've reached your goal! 🥳

💡 Ready for your next goal? Create a new one to keep building wealth!"""
                
                db_conn.commit()
                progress = (new_amount / target * 100)
                remaining = target - new_amount
                
                return f"""✅ Allocated ₹{allocation_amount:,.0f} to {goal_name}!

🎯 **{goal_name}**
💰 ₹{new_amount:,.0f} / ₹{target:,.0f} ({progress:.1f}%)
📊 {'🟩' * int(progress / 10)}{'⬜' * (10 - int(progress / 10))}
💵 Remaining: ₹{remaining:,.0f}

{
    "🔥 Almost there! Keep going!" if progress > 80
    else "💪 Great progress! You're halfway there!" if progress > 50
    else "🌱 Good start! Stay consistent!" if progress > 20
    else "🎯 Every step counts! Keep saving!"
}

💡 This amount is excluded from your expense tracking!"""
            
            elif action == "delete":
                if not goal_name:
                    return "❌ Please specify goal name to delete.\n\nExample: 'Delete goal Emergency Fund'"
                
                c.execute("""DELETE FROM goals WHERE telegram_id=? AND goal_name=?""",
                          (telegram_id, goal_name))
                db_conn.commit()
                
                if c.rowcount > 0:
                    return f"✅ Goal '{goal_name}' deleted successfully!"
                else:
                    return f"❌ Goal '{goal_name}' not found."
            
            else:
                return "❌ Invalid action. Use: create, list, allocate, or delete"
        
        except Exception as e:
            return f"⚠️ Error managing goals: {str(e)}"

goal_tool = GoalManagementTool()