import pandas as pd
from typing import List, Dict, Any, Tuple

def predict_cash_flow(transactions: List[Dict[str, Any]], time_horizon_days: int = 30) -> Dict[str, Any]:
    """
    Predicts future cash flow based on historical transactions using a robust averaging method.

    :param transactions: A list of transaction dictionaries, each with 'date' and 'amount'.
    :param time_horizon_days: The number of days into the future to predict.
    :return: A dictionary with predicted income, expenses, and volatility score.
    """
    if not transactions:
        return _create_empty_prediction()

    df = pd.DataFrame(transactions)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        return _create_empty_prediction()

    currency = transactions[0].get('currency', 'USD')
    
    days_in_data = _calculate_days_in_data(df)
    total_income, total_expenses = _calculate_totals(df)
    
    predicted_income, predicted_expenses = _calculate_predictions(
        total_income, total_expenses, days_in_data, time_horizon_days
    )
    
    net_cash_flow = predicted_income - predicted_expenses
    volatility_score = _calculate_volatility(df)

    return {
        "predicted_income": round(predicted_income, 2),
        "predicted_expenses": round(predicted_expenses, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "volatility_score": round(volatility_score, 2),
        "currency": currency
    }

def _create_empty_prediction() -> Dict[str, Any]:
    """Creates a default empty prediction dictionary."""
    return {
        "predicted_income": 0,
        "predicted_expenses": 0,
        "net_cash_flow": 0,
        "volatility_score": 0,
        "currency": "USD"
    }

def _calculate_days_in_data(df: pd.DataFrame) -> int:
    """Calculates the number of days spanned by the data."""
    if df.empty:
        return 1
    days = (df['date'].max() - df['date'].min()).days
    return max(days, 1) # Avoid division by zero

def _calculate_totals(df: pd.DataFrame) -> Tuple[float, float]:
    """Calculates total income and expenses."""
    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expenses = df[df['amount'] < 0]['amount'].abs().sum()
    return float(total_income), float(total_expenses)

def _calculate_predictions(total_income: float, total_expenses: float, days_in_data: int, time_horizon_days: int) -> Tuple[float, float]:
    """Calculates predicted income and expenses for the time horizon."""
    avg_daily_income = total_income / days_in_data
    avg_daily_expenses = total_expenses / days_in_data
    
    predicted_income = avg_daily_income * time_horizon_days
    predicted_expenses = avg_daily_expenses * time_horizon_days
    return predicted_income, predicted_expenses

def _calculate_volatility(df: pd.DataFrame) -> float:
    """Calculates volatility score based on daily net flow."""
    df_indexed = df.set_index('date')
    daily_net_flow = df_indexed['amount'].resample('D').sum()
    
    mean_daily_flow = daily_net_flow.mean()
    std_daily_flow = daily_net_flow.std()

    if mean_daily_flow != 0:
        volatility_score = std_daily_flow / mean_daily_flow
    else:
        volatility_score = 0
        
    return abs(volatility_score) if pd.notna(volatility_score) else 0.0