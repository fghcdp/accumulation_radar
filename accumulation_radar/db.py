import sqlite3
from datetime import datetime, timezone, timedelta

from .config import DB_PATH, logger


def get_db():
    """创建/连接数据库，确保表存在"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY,
        coin TEXT,
        added_date TEXT,
        sideways_days INT,
        range_pct REAL,
        avg_vol REAL,
        low_price REAL,
        high_price REAL,
        current_price REAL,
        score REAL,
        status TEXT DEFAULT 'watching',
        last_oi_alert TEXT,
        notes TEXT
    )""")
    conn.commit()
    return conn


def save_watchlist(conn, results):
    """保存标的池到数据库"""
    c = conn.cursor()
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    for r in results:
        c.execute("""INSERT OR REPLACE INTO watchlist
            (symbol, coin, added_date, sideways_days, range_pct, avg_vol,
             low_price, high_price, current_price, score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r["symbol"], r["coin"], now, r["sideways_days"], r["range_pct"],
             r["avg_vol"], r["low_price"], r["high_price"], r["current_price"],
             r["score"], r["status"]))
    conn.commit()
    logger.info(f"  💾 保存 {len(results)} 个标的到数据库")


def load_watchlist_symbols(conn):
    """从数据库加载标的池"""
    c = conn.cursor()
    c.execute("SELECT symbol FROM watchlist WHERE status != 'removed'")
    return [row[0] for row in c.fetchall()]


def load_pool_map(conn):
    """从数据库加载收筹池详情"""
    c = conn.cursor()
    c.execute("SELECT symbol, score, sideways_days, range_pct, avg_vol, status FROM watchlist")
    pool_map = {}
    for row in c.fetchall():
        pool_map[row[0]] = {
            "pool_score": row[1], "sideways_days": row[2],
            "range_pct": row[3], "avg_vol": row[4], "status": row[5],
        }
    return pool_map
