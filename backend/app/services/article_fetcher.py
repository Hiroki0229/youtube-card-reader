import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_ALLOWED_SCHEMES = {"http", "https"}


def _validate_safe_url(url: str) -> None:
    """SSRF 防護：驗證 scheme 必須為 http/https，且禁止存取本地或私有網路位址。"""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(f"不支援的網址協定：{parsed.scheme}")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("網址缺少主機名稱")

    # 檢查是否為 localhost 或直接是 IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ValueError(f"禁止存取私有或內部網路位址 ({ip_str})")
    except socket.gaierror as e:
        raise ValueError(f"無法解析主機名稱：{hostname}") from e


def fetch_article(url: str):
    _validate_safe_url(url)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else (soup.title.string if soup.title else "未知標題")
    main = soup.find("article") or soup.find("main") or soup.body
    text = " ".join(
        p.get_text(strip=True)
        for p in (main or soup).find_all("p")
        if len(p.get_text(strip=True)) > 30
    )
    if len(text) < 100:
        raise ValueError("無法擷取足夠的文章內容")
    return title, text

