"""原生前端（HTML/CSS/JS）托管测试：入口、静态资源、离线可用性。

约束（ADR-009 第 2 轮补充）：
- 不引入前端框架/CDN，页面必须能完全离线加载；
- 页面只调用 `/api/reviews` 系列接口，不在浏览器里判级。
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import WEB_DIR, create_app
from app.review_service import ReviewService


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(ReviewService.in_memory(), upload_dir=tmp_path / "uploads")
    with TestClient(app) as test_client:
        yield test_client


def test_index_serves_single_page_app(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    body = response.text
    assert 'lang="zh-CN"' in body
    assert "外贸合同智审助手" in body
    assert "/static/styles.css" in body
    assert "/static/app.js" in body


def test_frontend_assets_are_served(client: TestClient) -> None:
    styles = client.get("/static/styles.css")
    assert styles.status_code == 200
    assert styles.headers["content-type"].startswith("text/css")
    assert ":root" in styles.text

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "/api/reviews" in script.text
    assert "/api/rules" in script.text


def test_local_fonts_are_served(client: TestClient) -> None:
    """字体随包发布：不走 fonts.googleapis.com，断网也能保持排版。"""
    styles = client.get("/static/styles.css").text
    assert "/static/fonts/" in styles
    assert "@font-face" in styles

    font = client.get("/static/fonts/ibm-plex-sans-var.woff2")
    assert font.status_code == 200
    assert font.headers["content-type"].startswith("font/")
    assert len(font.content) > 10_000

    license_file = client.get("/static/fonts/OFL.txt")
    assert license_file.status_code == 200
    assert "SIL OPEN FONT LICENSE" in license_file.text.upper()


def test_frontend_has_no_external_dependency(client: TestClient) -> None:
    """离线约束：页面与脚本不得引用任何 http(s) 外链。

    唯一允许出现的是 SVG 的 XML 命名空间（`http://www.w3.org/2000/svg`），
    它是 data URI 内联图标的一部分，不会产生网络请求。
    """
    allowed = {"http://www.w3.org/2000/svg"}
    for path in ("/", "/static/app.js", "/static/styles.css"):
        body = client.get(path).text
        found = set(re.findall(r"https?://[^\s\"'()<>]+", body))
        assert found <= allowed, f"{path} 含外部引用：{sorted(found - allowed)}"
        assert "cdn." not in body, f"{path} 含 CDN 引用"


def test_frontend_never_judges_level_or_builds_command(client: TestClient) -> None:
    """页面只渲染后端返回的等级，不出现本地判级/拼 Command 的痕迹。"""
    script = client.get("/static/app.js").text
    assert "Command(" not in script
    # 不允许出现 `risk_level = ...` 这类赋值（`===` 比较不算）
    assert re.search(r"risk_level\s*=(?!=)", script) is None
    assert re.search(r"overall_level\s*=(?!=)", script) is None
    # 决定必须走 ReviewService 的 decisions 接口
    assert "/decisions" in script


def test_frontend_assets_exist_on_disk() -> None:
    for name in ("index.html", "styles.css", "app.js"):
        path = WEB_DIR / name
        assert path.is_file(), f"缺少前端资源 {name}"
        assert path.stat().st_size > 500
    # 资源里不写死端口/主机，部署到任意 host 都能用
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert re.search(r"localhost|127\.0\.0\.1", script) is None


def test_header_pick_button_targets_rendered_input() -> None:
    """顶部“选择合同”必须从当前视图取 input。

    `#file-input` 是渲染工作台时才创建的，启动时缓存 `dom.fileInput` 会是 undefined，
    点按钮直接抛错（真实缺陷：按钮点了没反应）。
    """
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "dom.fileInput" not in script
    assert re.search(r'on\("pick-file",\s*"click"', script) is not None
    assert 'querySelector("#file-input")' in script


def test_runtime_internals_stay_out_of_the_ui() -> None:
    """面向业务用户：侧栏不再展示接口版本 / checkpoint / RAG 开关等运行环境信息。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    for needle in ("运行环境", "rt-api", "rt-rules", "rt-checkpoint", "rt-rag"):
        assert needle not in page, f"index.html 仍包含内部信息：{needle}"
        assert needle not in script, f"app.js 仍包含内部信息：{needle}"
    assert ".runtime" not in styles
    # 保留的是对业务有用的入口，而不是调试信息
    assert "接口文档" in page

