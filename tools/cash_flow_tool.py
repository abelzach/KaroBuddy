import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import warnings

# Suppress warnings from statsmodels
warnings.filterwarnings("ignore", message="No supported index is available.")
warnings.filterwarnings("ignore", message="Non-stationary starting autoregressive parameters")
warnings.filterwarnings("ignore", message="Non-invertible starting MA parameters found.")

def predict_cash_flow(transactions: list, time_horizon_days: int = 30) -> dict:
    """
    Predicts future cash flow based on historical transactions using a robust averaging method.

    :param transactions: A list of transaction dictionaries, each with 'date' and 'amount'.
    :param time_horizon_days: The number of days into the future to predict.
    :return: A dictionary with predicted income, expenses, and volatility score.
    """
    if not transactions:
        return {
            "predicted_income": 0,
            "predicted_expenses": 0,
            "net_cash_flow": 0,
            "volatility_score": 0,
            "currency": "USD" # Default currency
        }

    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    
    # Determine the time span of the transactions
    days_in_data = (df['date'].max() - df['date'].min()).days
    if days_in_data == 0:
        days_in_data = 1 # Avoid division by zero if all transactions are on the same day

    currency = transactions[0].get('currency', 'USD')

    # Separate and total income and expenses
    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expenses = df[df['amount'] < 0]['amount'].abs().sum()

    # Calculate average daily income and expenses
    avg_daily_income = total_income / days_in_data
    avg_daily_expenses = total_expenses / days_in_data

    # Predict for the given time horizon
    predicted_income = avg_daily_income * time_horizon_days
    predicted_expenses = avg_daily_expenses * time_horizon_days
    
    net_cash_flow = predicted_income - predicted_expenses

    # Calculate volatility score (coefficient of variation for daily net flow)
    df = df.set_index('date')
    daily_net_flow = df['amount'].resample('D').sum()
    
    mean_daily_flow = daily_net_flow.mean()
    std_daily_flow = daily_net_flow.std()

    if mean_daily_flow != 0:
        volatility_score = std_daily_flow / mean_daily_flow
    else:
        volatility_score = 0
        
    volatility_score = abs(volatility_score) if pd.notna(volatility_score) else 0


    return {
        "predicted_income": round(predicted_income, 2),
        "predicted_expenses": round(predicted_expenses, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "volatility_score": round(volatility_score, 2),
        "currency": currency
    }