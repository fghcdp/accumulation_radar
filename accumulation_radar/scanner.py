import time

from .api import api_get
from .config import (
    MIN_DATA_DAYS, MIN_SIDEWAYS_DAYS, MAX_RANGE_PCT,
    MAX_AVG_VOL_USD, MIN_OI_DELTA_PCT, MIN_OI_USD,
    VOL_BREAKOUT_MULT, logger,
)


def get_all_perp_symbols():
    """获取所有USDT永续合约"""
    info = api_get("/fapi/v1/exchangeInfo")
    if not info:
        return []
    return [s["symbol"] for s in info["symbols"]
            if s["quoteAsset"] == "USDT"
            and s["contractType"] == "PERPETUAL"
            and s["status"] == "TRADING"]


def analyze_accumulation(symbol, klines):
    """分析单个币的收筹特征"""
    if len(klines) < MIN_DATA_DAYS:
        return None

    data = []
    for k in klines:
        data.append({
            "ts": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "vol": float(k[7]),
        })

    coin = symbol.replace("USDT", "")

    EXCLUDE = {"USDC", "USDP", "TUSD", "FDUSD", "BTCDOM", "DEFI", "USDM"}
    if coin in EXCLUDE:
        return None

    recent_7d = data[-7:]
    prior = data[:-7]
    if not prior:
        return None

    recent_avg_px = sum(d["close"] for d in recent_7d) / len(recent_7d)
    prior_avg_px = sum(d["close"] for d in prior) / len(prior)
    if prior_avg_px > 0 and ((recent_avg_px - prior_avg_px) / prior_avg_px) > 3.0:
        return None

    best_sideways = 0
    best_range = 0
    best_low = 0
    best_high = 0
    best_avg_vol = 0
    best_slope_pct = 0

    for window in range(MIN_SIDEWAYS_DAYS, len(prior) + 1):
        window_data = prior[-window:]
        lows = [d["low"] for d in window_data]
        highs = [d["high"] for d in window_data]
        w_low = min(lows)
        w_high = max(highs)
        if w_low <= 0:
            continue
        range_pct = ((w_high - w_low) / w_low) * 100
        if range_pct <= MAX_RANGE_PCT:
            avg_vol = sum(d["vol"] for d in window_data) / len(window_data)
            if avg_vol <= MAX_AVG_VOL_USD:
                closes = [d["close"] for d in window_data]
                n = len(closes)
                x_mean = (n - 1) / 2.0
                y_mean = sum(closes) / n
                num = sum((i - x_mean) * (c - y_mean) for i, c in enumerate(closes))
                den = sum((i - x_mean) ** 2 for i in range(n))
                slope = num / den if den > 0 else 0
                slope_pct = (slope * n / closes[0] * 100) if closes[0] > 0 else 0
                if abs(slope_pct) > 20:
                    continue
                if window > best_sideways:
                    best_sideways = window
                    best_range = range_pct
                    best_low = w_low
                    best_high = w_high
                    best_avg_vol = avg_vol
                    best_slope_pct = slope_pct

    if best_sideways < MIN_SIDEWAYS_DAYS:
        return None

    days_score = min(best_sideways / 90, 1.0) * 25
    range_score = max(0, (1 - best_range / MAX_RANGE_PCT)) * 20
    vol_score = max(0, (1 - best_avg_vol / MAX_AVG_VOL_USD)) * 20
    recent_vol = sum(d["vol"] for d in recent_7d) / len(recent_7d)
    vol_breakout = recent_vol / best_avg_vol if best_avg_vol > 0 else 0
    breakout_score = min(vol_breakout / VOL_BREAKOUT_MULT, 1.0) * 15

    est_mcap = data[-1]["close"] * best_avg_vol * 30
    if est_mcap > 0 and est_mcap < 50_000_000:
        mcap_score = 20
    elif est_mcap < 100_000_000:
        mcap_score = 15
    elif est_mcap < 200_000_000:
        mcap_score = 10
    elif est_mcap < 500_000_000:
        mcap_score = 5
    else:
        mcap_score = 0

    total_score = days_score + range_score + vol_score + breakout_score + mcap_score
    flatness_bonus = max(0, (1 - abs(best_slope_pct) / 20)) * 5
    total_score += flatness_bonus

    if vol_breakout >= VOL_BREAKOUT_MULT:
        status = "🔥放量启动"
    elif vol_breakout >= 1.5:
        status = "⚡开始放量"
    else:
        status = "💤收筹中"

    return {
        "symbol": symbol,
        "coin": coin,
        "sideways_days": best_sideways,
        "range_pct": best_range,
        "slope_pct": best_slope_pct,
        "low_price": best_low,
        "high_price": best_high,
        "avg_vol": best_avg_vol,
        "current_price": data[-1]["close"],
        "recent_vol": recent_vol,
        "vol_breakout": vol_breakout,
        "score": total_score,
        "status": status,
        "data_days": len(data),
    }


def scan_accumulation_pool():
    """扫描全市场，找正在被收筹的币"""
    logger.info("📊 扫描全市场收筹标的...")

    symbols = get_all_perp_symbols()
    logger.info(f"  共 {len(symbols)} 个合约")

    results = []
    for i, sym in enumerate(symbols):
        klines = api_get("/fapi/v1/klines", {
            "symbol": sym, "interval": "1d", "limit": 180
        })
        if klines and isinstance(klines, list):
            r = analyze_accumulation(sym, klines)
            if r:
                results.append(r)
        if (i + 1) % 10 == 0:
            time.sleep(0.5)
        if (i + 1) % 100 == 0:
            logger.info(f"  进度: {i+1}/{len(symbols)}... 已发现{len(results)}个")

    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"  ✅ 发现 {len(results)} 个收筹标的")
    return results


def scan_oi_changes(watchlist_symbols):
    """对标的池内的币扫描OI异动"""
    logger.info(f"📊 扫描OI异动（{len(watchlist_symbols)}个标的）...")
    alerts = []
    for sym in watchlist_symbols:
        oi_hist = api_get("/futures/data/openInterestHist", {
            "symbol": sym, "period": "1h", "limit": 3
        })
        if not oi_hist or len(oi_hist) < 2:
            continue
        prev_oi = float(oi_hist[-2]["sumOpenInterestValue"])
        curr_oi = float(oi_hist[-1]["sumOpenInterestValue"])
        if prev_oi <= 0 or curr_oi < MIN_OI_USD:
            continue
        delta_pct = ((curr_oi - prev_oi) / prev_oi) * 100
        if abs(delta_pct) >= MIN_OI_DELTA_PCT:
            ticker = api_get("/fapi/v1/ticker/24hr", {"symbol": sym})
            if not ticker:
                continue
            price = float(ticker["lastPrice"])
            vol_24h = float(ticker["quoteVolume"])
            px_chg = float(ticker["priceChangePercent"])
            funding = api_get("/fapi/v1/fundingRate", {"symbol": sym, "limit": 1})
            fr = float(funding[0]["fundingRate"]) if funding else 0
            coin = sym.replace("USDT", "")
            alerts.append({
                "symbol": sym, "coin": coin,
                "price": price, "oi_usd": curr_oi,
                "oi_delta_pct": delta_pct, "oi_delta_usd": curr_oi - prev_oi,
                "vol_24h": vol_24h, "px_chg_pct": px_chg, "funding_rate": fr,
            })
        time.sleep(0.3)

    alerts.sort(key=lambda x: abs(x["oi_delta_pct"]), reverse=True)
    logger.info(f"  ✅ 发现 {len(alerts)} 个OI异动")
    return alerts
