"""FastAPI 組裝：CORS、掛上四組路由、健康檢查。"""
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 進度訊息裡有中文與符號；Windows 主控台預設是 cp950 之類的地區編碼，
# 印到一半會丟 UnicodeEncodeError 把請求打斷。先把輸出流轉成 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from app.core import config  # noqa: F401  確保 .env 在最早期被載入
from app.api.ask import router as ask_router
from app.api.models import router as models_router
from app.api.notes import router as notes_router
from app.api.settings import router as settings_router
from app.api.summarize import router as summarize_router

app = FastAPI(title="Youtube Card Reader")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(summarize_router)
app.include_router(ask_router)
app.include_router(models_router)
app.include_router(notes_router)
app.include_router(settings_router)


@app.get("/health")
def health() -> dict:
    """健康檢查。"""
    return {"status": "ok"}
