import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from statsmodels.tsa.arima.model import ARIMA
import warnings

# Suppress warnings from statsmodels
warnings.filterwarnings("ignore")

def predict_cash_flow(transactions: List[Dict[str, Any]], time_horizon_days: int = 30) -> Dict[str, Any]:
    """
    Predicts future cash flow based on historical transactions using ARIMA with a fallback to robust averaging.

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
    
    # Prepare daily series for ARIMA
    df_daily = df.set_index('date')
    income_series = df_daily[df_daily['amount'] > 0]['amount'].resample('D').sum().fillna(0)
    expense_series = df_daily[df_daily['amount'] < 0]['amount'].abs().resample('D').sum().fillna(0)

    # Calculate predictions using ARIMA or fallback
    predicted_income = _predict_with_arima(income_series, time_horizon_days)
    predicted_expenses = _predict_with_arima(expense_series, time_horizon_days)

    # Fallback if ARIMA fails or returns None (e.g. not enough data)
    if predicted_income is None or predicted_expenses is None:
        days_in_data = _calculate_days_in_data(df)
        total_income, total_expenses = _calculate_totals(df)
        fallback_income, fallback_expenses = _calculate_average_predictions(
            total_income, total_expenses, days_in_data, time_horizon_days
        )
        predicted_income = predicted_income if predicted_income is not None else fallback_income
        predicted_expenses = predicted_expenses if predicted_expenses is not None else fallback_expenses
    
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
    return days + 1 # Inclusive of the start and end day

def _calculate_totals(df: pd.DataFrame) -> Tuple[float, float]:
    """Calculates total income and expenses."""
    total_income = df[df['amount'] > 0]['amount'].sum()
    total_expenses = df[df['amount'] < 0]['amount'].abs().sum()
    return float(total_income), float(total_expenses)

def _calculate_average_predictions(total_income: float, total_expenses: float, days_in_data: int, time_horizon_days: int) -> Tuple[float, float]:
    """Calculates predicted income and expenses using simple averaging."""
    avg_daily_income = total_income / days_in_data
    avg_daily_expenses = total_expenses / days_in_data
    
    predicted_income = avg_daily_income * time_horizon_days
    predicted_expenses = avg_daily_expenses * time_horizon_days
    return predicted_income, predicted_expenses

def _predict_with_arima(series: pd.Series, steps: int) -> Optional[float]:
    """
    Predicts future sum using ARIMA model.
    Returns None if not enough data or model fails.
    """
    # Need at least a few data points for ARIMA
    if len(series) < 10:
        return None
        
    try:
        # Simple ARIMA(1,1,1) as a generic starting point
        # For production, auto_arima or grid search would be better but slower
        model = ARIMA(series, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
        return max(0.0, float(forecast.sum())) # Ensure no negative predictions for income/expense sums
    except Exception:
        return None

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