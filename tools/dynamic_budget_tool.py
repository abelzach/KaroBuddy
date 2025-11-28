def generate_dynamic_budget(cash_flow_prediction: dict, user_goals: dict = None) -> dict:
    """
    Generates a dynamic budget based on predicted cash flow.

    :param cash_flow_prediction: The output from the cash_flow_tool.
    :param user_goals: A dictionary of user's financial goals (e.g., {'savings_goal': 500}).
    :return: A dictionary with recommended budget allocations.
    """
    predicted_income = cash_flow_prediction.get("predicted_income", 0)
    
    if predicted_income == 0:
        return {"error": "Cannot generate budget with zero predicted income."}

    # Default budget allocation percentages (50/30/20 rule)
    allocations = {
        "needs": 0.50,
        "wants": 0.30,
        "savings": 0.20
    }

    # Adjust allocations based on volatility
    volatility_score = cash_flow_prediction.get("volatility_score", 0)
    if volatility_score > 1.5: # High volatility
        # Increase savings, decrease wants
        allocations["savings"] += 0.10
        allocations["wants"] -= 0.10

    # Prioritize user goals if provided
    if user_goals and "savings_goal" in user_goals:
        required_savings = user_goals["savings_goal"]
        if required_savings > predicted_income * allocations["savings"]:
            # If goal is higher than allocated savings, try to pull from 'wants'
            savings_percentage = required_savings / predicted_income
            if savings_percentage <= (allocations["savings"] + allocations["wants"]):
                allocations["savings"] = savings_percentage
                allocations["wants"] = 1.0 - allocations["savings"] - allocations["needs"]
            else:
                # Goal is too aggressive for current income prediction
                pass # For now, we don't change the 'needs' category

    recommended_budget = {
        "needs_allocation": round(predicted_income * allocations["needs"], 2),
        "wants_allocation": round(predicted_income * allocations["wants"], 2),
        "savings_allocation": round(predicted_income * allocations["savings"], 2),
        "currency": cash_flow_prediction.get("currency", "USD"),
        "notes": "Based on the 50/30/20 rule, adjusted for income volatility."
    }

    return recommended_budget