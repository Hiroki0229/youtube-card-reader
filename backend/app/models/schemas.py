from typing import List, Optional

from pydantic import BaseModel


class Card(BaseModel):
    heading: str
    summary: str
    visual: Optional[str] = None            # 對應的畫面重點（簡報／板書／程式碼），純口說卡無此欄
    timestamp_seconds: Optional[int] = None
    transcript_highlight: Optional[str] = None
    translation: Optional[str] = None


class SummarizeRequest(BaseModel):
    url: str
    # provider："auto"／None＝免費模型優先、失敗才備援到有金鑰的付費供應商；
    #           "gemini"＝只用 gemini-3.5-flash-lite；
    #           "opencode:／deepseek:／openai:／anthropic:<model_id>"＝只用該模型
    provider: Optional[str] = None
    # 深視覺：True 時 DeepSRT（Gemini 讀畫面）優先於字幕；預設關（字幕優先，省 Gemini 額度）
    deep_visual: bool = False


class AskMessage(BaseModel):
    role: str      # "user" / "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    video_id: Optional[str] = None   # 用來從快取撈逐字稿當背景知識
    history: List[AskMessage] = []   # 之前的對話（不含本次 question）
    provider: Optional[str] = None   # 同 SummarizeRequest；auto 時優先 Gemini（有搜尋工具）


class DeepDiveRequest(BaseModel):
    provider: Optional[str] = None
    source_title: str
    card: Card


class SaveNoteRequest(BaseModel):
    filename: str
    content: str
    folder: str = ""          # vault 內的相對資料夾；空字串代表預設筆記資料夾
    mode: str = "new"         # "new" 建立新筆記 / "append" 附加到現有筆記
    target_file: str = ""     # mode=append 時，要附加的現有 .md 檔名


class SettingsUpdate(BaseModel):
    # 只更新有提供的欄位；傳空字串代表清除該設定
    gemini_api_key: Optional[str] = None
    opencode_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    output_language: Optional[str] = None
    obsidian_vault_path: Optional[str] = None
    obsidian_notes_folder: Optional[str] = None
