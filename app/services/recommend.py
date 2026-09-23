def sell_now_vs_store(
    current: float,
    predicted: float,
    low: float,
    high: float,
    storage_cost_per_kg_day: float,
    horizon_days: int,
    urgency: str = "medium",
) -> dict:
    storage_total = storage_cost_per_kg_day * horizon_days
    expected_net = predicted - current - storage_total
    band = max(1.0, high - low)
    confidence = max(0.35, min(0.92, 1.0 - (band / max(current, 1)) * 0.6))
    if urgency == "high":
        action = "sell_now"
        reason = "Liquidity urgency is high — cash within days outweighs a modest wait premium."
        if expected_net > current * 0.18 and confidence > 0.7:
            action = "store"
            reason = "Even with urgent cash need, forecast premium is large enough to wait."
    elif expected_net > 0 and predicted > current:
        action = "store"
        reason = "Forecast price rise covers storage cost within the horizon."
    else:
        action = "sell_now"
        reason = "Expected net after storage is flat or negative versus today's mandi."
    return {
        "action": action,
        "label": "Store" if action == "store" else "Sell now",
        "expected_net_per_kg": round(expected_net, 2),
        "storage_cost_per_kg": round(storage_total, 2),
        "confidence": round(confidence, 2),
        "interval": {"low": round(low, 2), "high": round(high, 2)},
        "reason": reason,
    }
