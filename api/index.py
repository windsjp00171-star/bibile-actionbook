"""Vercel serverless 進入點。

Vercel 的 Python runtime 會找這個模組裡名為 `app` 的 WSGI 物件當 handler。
真正的應用仍然是 repo 根目錄的 app.py，這裡只補上 import 路徑，不放任何邏輯，
本機開發／其他平台（Procfile 的 gunicorn app:app）完全不受影響。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402  (必須先插入路徑才能 import)

__all__ = ["app"]
