"""/notes 端點與 Obsidian vault 存檔相關單元測試。"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from app.core import config, messages  # noqa: E402
from app.main import app  # noqa: E402
from app.models.schemas import SaveNoteRequest  # noqa: E402
from app.api.notes import _safe_name, _safe_filename, _safe_relpath  # noqa: E402

client = TestClient(app)


def test_safe_name_and_safe_filename():
    # 特殊字元清理與空白收斂
    assert _safe_name(r'React: What? "New" / <Feature> * | 100%') == "React What New Feature 100%"
    # 結尾點號清理
    assert _safe_name("Some Note...") == "Some Note"
    # 空檔名回退預設日期
    fallback = _safe_name("")
    assert fallback.startswith("筆記 ") or fallback.startswith("Note ")

    # 現有檔名清理
    assert _safe_filename(r"subdir\..\target") == "target.md"
    assert _safe_filename("already.md") == "already.md"
    assert _safe_filename("already.MD") == "already.MD"


def test_safe_relpath():
    assert _safe_relpath("").as_posix() == "."
    assert _safe_relpath("a/b/c").as_posix() == "a/b/c"
    assert _safe_relpath(r"a\..\b").as_posix() == "a/b"
    assert _safe_relpath('foo:*?"<>|/bar').as_posix() == "foo/bar"


def test_save_notes_integration():
    tmp_vault = Path(tempfile.mkdtemp(prefix="test_vault_"))
    original_vault = config.get("OBSIDIAN_VAULT_PATH")
    original_folder = config.get("OBSIDIAN_NOTES_FOLDER")

    try:
        config._cache["OBSIDIAN_VAULT_PATH"] = str(tmp_vault)
        config._cache["OBSIDIAN_NOTES_FOLDER"] = "Youtube Card Reader"

        # 1. 建立新筆記（指定資料夾）
        res = client.post("/notes/save", json={
            "filename": "【React 19】Complete Guide / Tutorial: Part 1",
            "content": "# Test Note\n\nContent here",
            "folder": "Youtube Card Reader",
            "mode": "new",
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["ok"] is True
        assert data["mode"] == "new"
        saved_file = Path(data["saved_to"])
        assert saved_file.exists()
        assert saved_file.read_text(encoding="utf-8").startswith("# Test Note")

        # 2. 同名檔自動遞增
        res2 = client.post("/notes/save", json={
            "filename": "【React 19】Complete Guide / Tutorial: Part 1",
            "content": "# Test Note 2",
            "folder": "Youtube Card Reader",
            "mode": "new",
        })
        assert res2.status_code == 200
        saved_file2 = Path(res2.json()["saved_to"])
        assert saved_file2.name.endswith("2.md")
        assert saved_file2.exists()

        # 3. 附加到現有筆記
        res3 = client.post("/notes/save", json={
            "filename": "",
            "content": "## Appended Section",
            "folder": "Youtube Card Reader",
            "mode": "append",
            "target_file": saved_file.name,
        })
        assert res3.status_code == 200
        assert res3.json()["mode"] == "append"
        assert "## Appended Section" in saved_file.read_text(encoding="utf-8")

        # 4. 存入根目錄（folder=""）
        res4 = client.post("/notes/save", json={
            "filename": "Root Note",
            "content": "# In Root",
            "folder": "",
            "mode": "new",
        })
        assert res4.status_code == 200
        root_file = Path(res4.json()["saved_to"])
        assert root_file.parent.resolve() == tmp_vault.resolve()

        # 5. 防路徑逃逸測試
        res5 = client.post("/notes/save", json={
            "filename": "Escape",
            "content": "# Hack",
            "folder": "../../outside",
            "mode": "new",
        })
        # _safe_relpath 移除了 ..，因此路徑仍限制在 vault 內
        assert res5.status_code == 200
        escape_file = Path(res5.json()["saved_to"])
        assert tmp_vault.resolve() in escape_file.resolve().parents

        # 6. Status 端點測試
        st = client.get("/notes/status").json()
        assert st["configured"] is True
        assert st["exists"] is True

        # 7. Folders 端點測試
        flds = client.get("/notes/folders").json()
        assert "Youtube Card Reader" in flds["folders"]

        # 8. Files 端點測試
        fls = client.get("/notes/files?folder=Youtube Card Reader").json()
        assert saved_file.name in fls["files"]

    finally:
        config._cache["OBSIDIAN_VAULT_PATH"] = original_vault
        config._cache["OBSIDIAN_NOTES_FOLDER"] = original_folder
        shutil.rmtree(tmp_vault, ignore_errors=True)


if __name__ == "__main__":
    test_safe_name_and_safe_filename()
    test_safe_relpath()
    test_save_notes_integration()
    print("✅ 全部 Obsidian 筆記單元測試通過！")
