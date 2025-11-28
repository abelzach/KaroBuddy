import pandas as pd

def analyze_user_activity(transactions: list, market_data: dict = None) -> list:
    """
    Analyzes user transactions to identify potential behavioral biases.

    :param transactions: A list of transaction dictionaries.
    :param market_data: A dictionary with market performance data (e.g., {'market_change_pct': -5.0}).
    :return: A list of detected biases.
    """
    if not transactions:
        return []

    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    
    detected_biases = []

    # --- 1. Panic Selling Detection ---
    if market_data and market_data.get('market_change_pct', 0) < -3.0:
        # Market is in a significant downturn
        recent_sells = df[
            (df['amount'] < 0) & # It's a sell/spending
            (df['description'].str.contains('sell|sold', case=False, na=False))
        ]
        if not recent_sells.empty:
            for index, row in recent_sells.iterrows():
                detected_biases.append({
                    "bias_type": "PANIC_SELLING",
                    "event_timestamp": row['date'].isoformat(),
                    "description": f"Potential panic sell detected: Sold assets during a market downturn of {market_data['market_change_pct']}%.",
                    "related_transaction_id": row.get('id')
                })

    # --- 2. FOMO Buying Detection (Fear of Missing Out) ---
    # This is a simplified version. A real implementation would need asset price history.
    # We'll simulate it by looking for large investment buys.
    investment_buys = df[
        (df['amount'] < 0) & # Money is spent
        (df['description'].str.contains('buy|invest|purchase', case=False, na=False)) &
        (df['amount'].abs() > df['amount'].abs().quantile(0.90)) # In the top 10% of transaction amounts
    ]
    if not investment_buys.empty:
        for index, row in investment_buys.iterrows():
            detected_biases.append({
                "bias_type": "FOMO_BUYING",
                "event_timestamp": row['date'].isoformat(),
                "description": f"Potential FOMO buy detected: Unusually large investment of {row['amount']}. Monitor if this was chasing high returns.",
                "related_transaction_id": row.get('id')
            })
            
    # --- 3. Concentration Risk ---
    # Analyze the user's portfolio if available (mocked here by transaction descriptions)
    asset_counts = df[df['description'].str.contains('stock|asset', case=False, na=False)]['description'].value_counts()
    total_assets = asset_counts.sum()
    if total_assets > 0:
        most_common_asset_count = asset_counts.iloc[0]
        if (most_common_asset_count / total_assets) > 0.5 and total_assets > 5: # More than 50% in one asset
             detected_biases.append({
                "bias_type": "CONCENTRATION_RISK",
                "event_timestamp": pd.Timestamp.now().isoformat(),
                "description": f"Potential Concentration Risk: Over 50% of recent transactions are related to a single asset type.",
                "related_transaction_id": None
            })

    return detected_biases