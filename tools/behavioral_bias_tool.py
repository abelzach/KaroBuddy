import pandas as pd
from typing import List, Dict, Any, Optional

# Constants
MARKET_DOWNTURN_THRESHOLD = -3.0
FOMO_QUANTILE_THRESHOLD = 0.90
CONCENTRATION_RATIO_THRESHOLD = 0.5
CONCENTRATION_MIN_ASSETS = 5

def analyze_user_activity(transactions: List[Dict[str, Any]], market_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Analyzes user transactions to identify potential behavioral biases.

    :param transactions: A list of transaction dictionaries.
    :param market_data: A dictionary with market performance data (e.g., {'market_change_pct': -5.0}).
    :return: A list of detected biases.
    """
    if not transactions:
        return []

    df = pd.DataFrame(transactions)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    detected_biases = []

    detected_biases.extend(_detect_panic_selling(df, market_data))
    detected_biases.extend(_detect_fomo_buying(df))
    detected_biases.extend(_detect_concentration_risk(df))

    return detected_biases

def _detect_panic_selling(df: pd.DataFrame, market_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detects panic selling during market downturns."""
    biases = []
    if market_data and market_data.get('market_change_pct', 0) < MARKET_DOWNTURN_THRESHOLD:
        # Market is in a significant downturn
        # Logic Change: Assuming selling an asset results in positive cash flow (income)
        recent_sells = df[
            (df['amount'] > 0) & # It's a sell/income
            (df['description'].str.contains('sell|sold', case=False, na=False))
        ]
        if not recent_sells.empty:
            for _, row in recent_sells.iterrows():
                biases.append({
                    "bias_type": "PANIC_SELLING",
                    "event_timestamp": row['date'].isoformat() if 'date' in row else None,
                    "description": f"Potential panic sell detected: Sold assets during a market downturn of {market_data['market_change_pct']}%.",
                    "related_transaction_id": row.get('id')
                })
    return biases

def _detect_fomo_buying(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detects FOMO buying (large investments)."""
    biases = []
    # This is a simplified version. A real implementation would need asset price history.
    # We'll simulate it by looking for large investment buys.
    
    # Filter for spending (negative amounts)
    spending_df = df[df['amount'] < 0]
    
    if spending_df.empty:
        return []

    investment_buys = spending_df[
        (spending_df['description'].str.contains('buy|invest|purchase', case=False, na=False)) &
        (spending_df['amount'].abs() > spending_df['amount'].abs().quantile(FOMO_QUANTILE_THRESHOLD)) # In the top 10% of transaction amounts
    ]
    
    if not investment_buys.empty:
        for _, row in investment_buys.iterrows():
            biases.append({
                "bias_type": "FOMO_BUYING",
                "event_timestamp": row['date'].isoformat() if 'date' in row else None,
                "description": f"Potential FOMO buy detected: Unusually large investment of {row['amount']}. Monitor if this was chasing high returns.",
                "related_transaction_id": row.get('id')
            })
    return biases

def _detect_concentration_risk(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Detects concentration risk in portfolio."""
    biases = []
    # Analyze the user's portfolio if available (mocked here by transaction descriptions)
    asset_counts = df[df['description'].str.contains('stock|asset', case=False, na=False)]['description'].value_counts()
    total_assets = asset_counts.sum()
    
    if total_assets > 0:
        most_common_asset_count = asset_counts.iloc[0]
        if (most_common_asset_count / total_assets) > CONCENTRATION_RATIO_THRESHOLD and total_assets > CONCENTRATION_MIN_ASSETS: # More than 50% in one asset
             biases.append({
                "bias_type": "CONCENTRATION_RISK",
                "event_timestamp": pd.Timestamp.now().isoformat(),
                "description": f"Potential Concentration Risk: Over {int(CONCENTRATION_RATIO_THRESHOLD*100)}% of recent transactions are related to a single asset type.",
                "related_transaction_id": None
            })
    return biases