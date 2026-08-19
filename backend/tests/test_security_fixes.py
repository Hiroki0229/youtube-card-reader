"""安全性修復單元測試（C-1, H-1, H-2, H-3, H-4）。"""
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import crypto, config
from app.main import app
from app.services.article_fetcher import _validate_safe_url
from app.transcript.router import route_content
from app.api.implement import _VIEWABLE


def test_c1_local_crypto_encryption_and_decryption():
    """C-1：本機特徵對稱加密可正常加解密，空值與向後相容性正確。"""
    raw_key = "AIzaSyTestApiKey123456789"
    
    # 加密
    encrypted = crypto.encrypt_value(raw_key)
    assert encrypted.startswith("enc:")
    assert encrypted != raw_key
    
    # 不重複加密
    assert crypto.encrypt_value(encrypted) == encrypted
    
    # 解密
    decrypted = crypto.decrypt_value(encrypted)
    assert decrypted == raw_key
    
    # 空字串處理
    assert crypto.encrypt_value("") == ""
    assert crypto.decrypt_value("") == ""
    
    # 向後相容：未加密之純文字直接回傳
    assert crypto.decrypt_value("legacy-plaintext-key") == "legacy-plaintext-key"


def test_c1_config_saves_encrypted_and_reads_decrypted():
    """C-1：config.save 寫入 settings.json 時為密文，但在記憶體內為解密後的明文。"""
    test_key = "AIzaSySaveTestKey999"
    config.save({"GEMINI_API_KEY": test_key})
    
    # 記憶體讀取應為明文（供 SDK 正常調用）
    assert config.get("GEMINI_API_KEY") == test_key
    
    # 讀取磁碟上的 settings.json 原始檔案，應為 enc: 密文
    raw_json = config._read_settings_file()
    assert raw_json.get("GEMINI_API_KEY", "").startswith("enc:")
    assert raw_json.get("GEMINI_API_KEY") != test_key
    
    # 重設清除
    config.save({"GEMINI_API_KEY": ""})
    assert config.get("GEMINI_API_KEY") == ""


def test_h1_cors_allowed_origins():
    """H-1：CORS 中介軟體限制來源，不允許萬用字元 *。"""
    cors_middleware = None
    for m in app.user_middleware:
        if "CORSMiddleware" in str(m):
            cors_middleware = m
            break
    
    client = TestClient(app)
    
    # 允許的本地前端來源
    res = client.options("/health", headers={
        "Origin": "http://127.0.0.1:15273",
        "Access-Control-Request-Method": "GET"
    })
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:15273"
    
    # 未授權的外部惡意網站來源應被拒絕 Access-Control-Allow-Origin
    res_evil = client.options("/health", headers={
        "Origin": "http://evil-attacker.com",
        "Access-Control-Request-Method": "GET"
    })
    assert res_evil.headers.get("access-control-allow-origin") != "http://evil-attacker.com"
    assert res_evil.headers.get("access-control-allow-origin") != "*"


def test_h2_ssrf_blocks_private_and_local_ips():
    """H-2：SSRF 防禦應攔截私有 IP、localhost 及不合法協定。"""
    bad_urls = [
        "http://127.0.0.1/secret",
        "http://localhost:8080/admin",
        "http://192.168.1.1/router",
        "http://10.0.0.5/internal",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)"
    ]
    for url in bad_urls:
        try:
            _validate_safe_url(url)
            assert False, f"應攔截危險 URL: {url}"
        except ValueError as e:
            assert "禁止存取" in str(e) or "不支援" in str(e) or "無法解析" in str(e) or "缺少" in str(e)


def test_h3_route_content_url_scheme_whitelist():
    """H-3：route_content 應拒絕非 http/https 協定。"""
    invalid_urls = [
        "file:///c:/windows/system32/cmd.exe",
        "ftp://example.com/video.mp4",
        "rtmp://live.example.com/stream",
        "javascript:void(0)",
        "",
    ]
    for url in invalid_urls:
        try:
            route_content(url)
            assert False, f"應拒絕無效 URL: {url}"
        except ValueError as e:
            assert "無效的網址" in str(e)


def test_h4_env_file_not_in_viewable_whitelist():
    """H-4：.env 不在可預覽檔案類型白名單中。"""
    assert ".env" not in _VIEWABLE
    assert ".html" in _VIEWABLE
    assert ".md" in _VIEWABLE
    assert ".py" in _VIEWABLE


if __name__ == "__main__":
    test_c1_local_crypto_encryption_and_decryption()
    print("✅ C-1: Local Crypto 加解密測試通過")
    test_c1_config_saves_encrypted_and_reads_decrypted()
    print("✅ C-1: Config 自動加密儲存測試通過")
    test_h1_cors_allowed_origins()
    print("✅ H-1: CORS 來源限制測試通過")
    test_h2_ssrf_blocks_private_and_local_ips()
    print("✅ H-2: SSRF 私有 IP 阻擋測試通過")
    test_h3_route_content_url_scheme_whitelist()
    print("✅ H-3: URL Scheme 白名單測試通過")
    test_h4_env_file_not_in_viewable_whitelist()
    print("✅ H-4: .env 移出預覽白名單測試通過")
    print("\n🎉 全部安全性修復單元測試通過！")
