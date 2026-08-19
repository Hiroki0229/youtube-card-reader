"""本機硬體特徵衍生對稱加密模組（Local AES / Fernet）。

用於保護 settings.json 內的 API 金鑰等敏感資訊：
- 利用本機作業系統唯一硬體特徵（如 Windows MachineGuid、MAC 地址、主機特徵與使用者名稱）衍生密鑰
- 儲存時加密成 `enc:<token>` 格式；讀取時自動透明解密
- 若檔案被複製到其他電腦或以其他未授權使用者身分讀取，因衍生密鑰不同而無法解密
"""
import base64
import hashlib
import os
import platform
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_SALT = b"ycr_local_key_salt_2026_v1"
_PREFIX = "enc:"


def _get_machine_identifier() -> str:
    """收集本機硬體與使用者特徵識別字串。"""
    parts = [platform.node()]

    # Windows: 嘗試取得系統 MachineGuid
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    parts.append(str(guid))
        except Exception:
            pass

    # 補充 MAC 與使用者名稱
    parts.append(str(uuid.getnode()))
    user = os.environ.get("USERNAME") or os.environ.get("USER") or os.environ.get("LOGNAME") or "default"
    parts.append(user)

    return ":".join(parts)


def _get_cipher() -> Fernet:
    """由本機特徵透過 PBKDF2 衍生 Fernet (AES-128-CBC + HMAC) 實例。"""
    ident = _get_machine_identifier().encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(ident))
    return Fernet(key)


_cipher_instance = None


def _cipher() -> Fernet:
    global _cipher_instance
    if _cipher_instance is None:
        _cipher_instance = _get_cipher()
    return _cipher_instance


def encrypt_value(text: str) -> str:
    """將純文字加密為 enc: 前綴的密文字串；若原本已為密文或為空則直接回傳。"""
    if not text:
        return ""
    if text.startswith(_PREFIX):
        return text
    try:
        token = _cipher().encrypt(text.encode("utf-8")).decode("utf-8")
        return f"{_PREFIX}{token}"
    except Exception as e:
        print(f"[crypto] 加密失敗：{e}", flush=True)
        return text


def decrypt_value(cipher_text: str) -> str:
    """將 enc: 前綴的密文字串解密為純文字；向後相容未加密之純文字。"""
    if not cipher_text:
        return ""
    if not cipher_text.startswith(_PREFIX):
        return cipher_text
    raw_token = cipher_text[len(_PREFIX):]
    try:
        decrypted = _cipher().decrypt(raw_token.encode("utf-8")).decode("utf-8")
        return decrypted
    except InvalidToken:
        print("[crypto] 解密失敗：金鑰密文可能損毀或非來自本機。", flush=True)
        return ""
    except Exception as e:
        print(f"[crypto] 解密異常：{e}", flush=True)
        return ""
