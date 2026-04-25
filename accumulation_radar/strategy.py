import time

from .api import api_get
from .config import logger


def score_chase(coin_data):
    """策略1: 追多 — 费率排名（短线轧空）"""
    chase = []
    for sym, d in coin_data.items():
        if d["px_chg"] > 3 and d["fr_pct"] < -0.005 and d["vol"] > 1_000_000:
            fr_hist = api_get("/fapi/v1/fundingRate", {"symbol": sym, "limit": 5})
            fr_rates = [float(f["fundingRate"]) * 100 for f in fr_hist] if fr_hist else [d["fr_pct"]]
            fr_prev = fr_rates[-2] if len(fr_rates) >= 2 else d["fr_pct"]
            fr_delta = d["fr_pct"] - fr_prev

            trend = ("🔥加速" if fr_delta < -0.05
                     else "⬇️变负" if fr_delta < -0.01
                     else "➡️" if abs(fr_delta) < 0.01
                     else "⬆️回升")

            chase.append({**d, "fr_delta": fr_delta, "trend": trend,
                          "rates": " → ".join([f"{x:.3f}" for x in fr_rates[-3:]])})
            time.sleep(0.2)

    chase.sort(key=lambda x: x["fr_pct"])
    return chase


def score_combined(coin_data):
    """策略2: 综合 — 四维均衡(各25分=100分)"""
    combined = []
    for sym, d in coin_data.items():
        fr = d["fr_pct"]
        if fr < -0.5: f_sc = 25
        elif fr < -0.1: f_sc = 22
        elif fr < -0.05: f_sc = 18
        elif fr < -0.03: f_sc = 14
        elif fr < -0.01: f_sc = 10
        elif fr < 0: f_sc = 5
        else: f_sc = 0

        mc = d["est_mcap"]
        if mc > 0 and mc < 50e6: m_sc = 25
        elif mc < 100e6: m_sc = 22
        elif mc < 200e6: m_sc = 20
        elif mc < 300e6: m_sc = 17
        elif mc < 500e6: m_sc = 12
        elif mc < 1e9: m_sc = 7
        else: m_sc = 0

        sw = d["sw_days"]
        if sw >= 120: s_sc = 25
        elif sw >= 90: s_sc = 22
        elif sw >= 75: s_sc = 18
        elif sw >= 60: s_sc = 14
        elif sw >= 45: s_sc = 10
        else: s_sc = 0

        abs6 = abs(d["d6h"])
        if abs6 >= 15: o_sc = 25
        elif abs6 >= 8: o_sc = 22
        elif abs6 >= 5: o_sc = 18
        elif abs6 >= 3: o_sc = 14
        elif abs6 >= 2: o_sc = 10
        else: o_sc = 0

        total = f_sc + m_sc + s_sc + o_sc
        if total < 25:
            continue

        combined.append({**d, "total": total,
                         "f_sc": f_sc, "m_sc": m_sc, "s_sc": s_sc, "o_sc": o_sc})

    combined.sort(key=lambda x: x["total"], reverse=True)
    return combined


def score_ambush(coin_data):
    """策略3: 埋伏 — 市值>OI>横盘>费率（中长线）"""
    ambush = []
    for sym, d in coin_data.items():
        if not d["in_pool"]:
            continue
        if d["px_chg"] > 50:
            continue

        mc = d["est_mcap"]
        if mc > 0 and mc < 50e6: m_sc = 35
        elif mc < 100e6: m_sc = 32
        elif mc < 150e6: m_sc = 28
        elif mc < 200e6: m_sc = 25
        elif mc < 300e6: m_sc = 20
        elif mc < 500e6: m_sc = 12
        elif mc < 1e9: m_sc = 5
        else: m_sc = 0

        abs6 = abs(d["d6h"])
        if abs6 >= 10: o_sc = 30
        elif abs6 >= 5: o_sc = 25
        elif abs6 >= 3: o_sc = 20
        elif abs6 >= 2: o_sc = 14
        elif abs6 >= 1: o_sc = 8
        else: o_sc = 0
        if d["d6h"] > 2 and abs(d["px_chg"]) < 5:
            o_sc = min(o_sc + 5, 30)

        sw = d["sw_days"]
        if sw >= 120: s_sc = 20
        elif sw >= 90: s_sc = 17
        elif sw >= 75: s_sc = 14
        elif sw >= 60: s_sc = 10
        elif sw >= 45: s_sc = 6
        else: s_sc = 0

        fr = d["fr_pct"]
        if fr < -0.1: f_sc = 15
        elif fr < -0.05: f_sc = 12
        elif fr < -0.03: f_sc = 9
        elif fr < -0.01: f_sc = 6
        elif fr < 0: f_sc = 3
        else: f_sc = 0

        total = m_sc + o_sc + s_sc + f_sc
        if total < 20:
            continue

        ambush.append({**d, "total": total,
                       "m_sc": m_sc, "o_sc": o_sc, "s_sc": s_sc, "f_sc": f_sc})

    ambush.sort(key=lambda x: x["total"], reverse=True)
    return ambush
