"""Streamlit 界面冒烟测试：脚本可加载、首屏无异常（不触碰真实上传）。"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_ui_boots_without_exception() -> None:
    app = AppTest.from_file(str(PROJECT_ROOT / "app" / "ui.py"), default_timeout=120)
    app.run()

    assert list(app.exception) == []
    assert app.title[0].value == "Agent Alex · 外贸合同智审助手"
    assert any("请上传合同" in item.value for item in app.info)
