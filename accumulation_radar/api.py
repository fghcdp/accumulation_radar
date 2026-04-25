import time

import requests

from .config import FAPI


def api_get(endpoint, params=None):
    """币安API请求（3次重试 + 429限速）"""
    url = f"{FAPI}{endpoint}"
    for _ in range(3):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(2)
            else:
                return None
        except (requests.RequestException, ValueError):
            time.sleep(1)
    return None
