from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from database import chroma_client

class FraudInput(BaseModel):
    message: str = Field(description="Investment opportunity or message to check")

class FraudDetectorTool(BaseTool):
    name: str = "fraud_detector"
    description: str = "Detects if a message contains scam patterns using semantic similarity"
    args_schema: type[BaseModel] = FraudInput
    
    def _run(self, message: str) -> str:
        """Detect fraud patterns in a message."""
        try:
            # Query ChromaDB for similar fraud patterns
            fraud_collection = chroma_client.get_collection("fraud_patterns")
            
            results = fraud_collection.query(
                query_texts=[message],
                n_results=3
            )
            
            if not results['distances'] or not results['distances'][0]:
                return "✅ Looks safe! No scam patterns detected."
            
            # Check similarity score (lower = more similar in ChromaDB)
            top_similarity = results['distances'][0][0]
            
            if top_similarity < 0.5:  # Very similar to known scam
                matched_pattern = results['documents'][0][0]
                return f"""🚨 CRITICAL SCAM ALERT!

This message matches known fraud patterns:
"{matched_pattern[:60]}..."

Red flags detected:
❌ Guaranteed returns claims
❌ Urgency tactics ("limited time")
❌ Too good to be true promises
❌ Pressure to act quickly

⚠️ DO NOT INVEST! This is likely a Ponzi scheme or scam.

🛡️ Protect yourself:
• Never share OTPs or passwords
• Verify SEBI registration
• Research thoroughly
• If it sounds too good to be true, it probably is"""

            elif top_similarity < 0.8:  # Somewhat similar
                return f"""⚠️ WARNING: Potential scam detected

This message has suspicious elements similar to known scams.

Be cautious and verify:
✓ Check company credentials
✓ Verify SEBI/RBI registration
✓ Look for online reviews
✓ Never share sensitive information
✓ Research thoroughly before investing

🔍 Red flags to watch:
• Guaranteed high returns
• Pressure to invest quickly
• Unregistered entities
• Requests for upfront payment"""
            
            else:
                return """✅ No major red flags detected

However, always practice due diligence:
• Research the company/opportunity
• Check regulatory compliance
• Read reviews and testimonials
• Never invest more than you can afford to lose
• Consult a financial advisor for large investments

Stay safe! 🛡️"""
        
        except Exception as e:
            return f"⚠️ Error checking for fraud patterns: {str(e)}\n\nPlease be cautious and do your own research!"

# Create instance
fraud_tool = FraudDetectorTool()
