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
    # 结果页的“下载报告”必须指向报告接口，而不是审查详情接口
    assert "/report?format=markdown" in script.text
    # 极简页没有规则集视图，不再请求规则目录
    assert "/api/rules" not in script.text


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
    """离线约束：页面不得从外网加载任何资源。

    只检查真正会发起请求的引用（`src` / `href` / `url()` / `@import`）；
    厂商目录里的“默认服务地址”只是输入框占位文本，不会在加载时请求。
    """
    for path in ("/", "/static/app.js", "/static/styles.css"):
        body = client.get(path).text
        remote = set(
            re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)""", body)
        )
        remote |= set(re.findall(r"""url\(\s*["']?(https?://[^)"']+)""", body))
        # SVG 的 XML 命名空间只是字符串常量，不是加载请求
        remote = {item for item in remote if not item.startswith("http://www.w3.org/")}
        assert not remote, f"{path} 含外部资源引用：{sorted(remote)}"
        assert "@import" not in body, f"{path} 使用了 @import"
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


def test_attachment_button_targets_rendered_input() -> None:
    """对话输入区的“合同”按钮必须从当前视图取 input。

    `#file-input` 是渲染输入区时才创建的，启动时缓存成 `dom.fileInput` 会是 undefined，
    点按钮直接抛错（真实缺陷：按钮点了没反应）。
    """
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "dom.fileInput" not in script
    assert re.search(r'on\("attach-button",\s*"click"', script) is not None
    assert 'querySelector("#file-input")' in script


def test_sidebar_kept_but_main_content_is_minimal() -> None:
    """侧栏保留，右侧主区只做“上传合同 → 看风险点”。

    用户口径：信息过多指的是右侧主体（流水线、规则集、KPI、抽取要素、核对清单）；
    左侧导航壳保留，仍提供“上传合同 / 当前审查 / API 配置 / 接口文档”入口。
    """
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 侧栏保留：导航壳 + 两个入口 + 文档入口
    assert '<aside class="sidebar"' in page
    assert 'id="sidebar"' in page
    assert 'data-nav="upload"' in page
    assert 'data-nav="review"' in page
    assert "接口文档" in page
    assert 'id="view"' in page

    # 右侧主区不再出现工作台信息
    for needle in ("审查流水线", "抽取要素", "待核对", "复核记录", "规则集", "运行环境"):
        assert needle not in page, f"index.html 仍包含工作台信息：{needle}"
        assert needle not in script, f"app.js 仍包含工作台信息：{needle}"

    # 导航壳的样式必须在（否则侧栏会“裸奔”），主区只剩上传与风险点
    assert ".sidebar" in styles
    assert ".sheet" in styles
    assert "上传合同" in page
    assert "确认这些风险" in script
    assert "/decisions" in script


def test_review_focus_lives_in_main_composer_not_sidebar() -> None:
    """审查重点 / 附件 / Skill 选择属于右侧对话输入区；仓库入口在侧栏。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    sidebar = page.split('<header class="topbar"', 1)[0]
    for needle in ("focus-input", "attach-button", "skill-select"):
        assert needle not in sidebar, f"侧栏仍包含输入组件：{needle}"
        assert needle in script, f"app.js 缺少输入组件：{needle}"

    # Skill 仓库是侧栏入口；输入区不再重复放一个“Skill 仓库”按钮
    assert 'id="open-skills"' in sidebar
    assert 'id="open-skills"' not in script.split('id="composer-box"', 1)[-1]
    assert "open-skills" not in page.split('class="composer-tools"', 1)[-1].split("</div>", 1)[0]

    # 输入区按对话式排布：文本域 + 工具行 + 圆形发送键
    assert 'class="composer-box"' in script
    assert 'class="composer-tools"' in script
    assert 'class="send"' in script
    # Enter 发送、Shift+Enter 换行（代码里是 event.shiftKey）
    assert "event.key" in script and "shiftKey" in script


def test_skill_select_defaults_to_repo_last_and_no_empty_option() -> None:
    """Skill 下拉默认给几个内置 Skill，最后一项固定为 Skill 仓库。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'SKILL_REPO_VALUE = "__repo__"' in script
    assert "Skill 仓库…" in script
    # 旧的“不使用 Skill”占位已删除
    assert "不使用 Skill" not in script
    # 默认选中内置“全量体检”
    assert "builtin:full" in script
    # 选中仓库项时不当作 Skill，而是跳转仓库页
    assert "onSkillSelectChange" in script
    assert 'location.hash = "#/skills"' in script
    # 仓库项排在所有真实 Skill 之后（分隔线 → 仓库入口）
    assert script.index("skill-menu-sep") < script.index("Skill 仓库…")
    # 不再使用系统 select（外观难统一），改为自绘 listbox
    assert 'class="tool-select"' not in script
    assert 'id="skill-menu"' in script and 'role="listbox"' in script
    assert "toggleSkillMenu" in script
    assert ".tool-skill" in styles and ".skill-menu" in styles


def test_skill_repo_is_standalone_page_not_dialog() -> None:
    """Skill 仓库仍是独立页面；新建/导入改为右上角按钮 + 弹窗，不再占用右栏。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="skills-dialog"' not in page
    assert 'href="#/skills"' in page
    assert "renderSkillsPage" in script
    assert 'hash === "#/skills"' in script
    # 页面只有“推荐 / 我的”两块；新建与导入是两个静态弹窗
    assert 'class="skills-head-actions"' in script
    assert 'id="skill-new-open"' in script
    assert 'id="skill-import-open"' in script
    assert 'id="skill-new-dialog"' in page
    assert 'id="skill-import-dialog"' in page
    assert 'id="skill-form"' in page
    # 仍复用同一套 Skill API（不新增后端接口）
    assert '"/api/skills"' in script
    # 右栏（.skills-grid）已删除，改成方块 + 弹窗
    assert ".skill-tiles" in styles
    assert ".skills-grid" not in styles


def test_skill_repo_imports_markdown_files_folders_and_zip() -> None:
    """Skill 仓库支持 .md / 文件夹 / zip 包导入；zip 走服务端解析，其余在浏览器解析。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 导入弹窗里有两个入口：多选 .md/.zip 与整目录（webkitdirectory）
    dialog = page.split('id="skill-import-dialog"', 1)[1].split("</dialog>", 1)[0]
    assert 'id="skill-import-input"' in dialog
    assert 'accept=".md,.markdown,.zip,text/markdown,application/zip"' in dialog
    assert 'id="skill-import-dir"' in dialog
    assert "webkitdirectory" in dialog
    # 拖拽区 + 键盘可达（Enter / 空格也能选文件）
    assert 'id="skill-drop"' in dialog
    assert "filesFromDataTransfer" in script
    assert "webkitGetAsEntry" in script
    assert 'event.key !== "Enter"' in script
    # 解析规则：frontmatter / 一级标题 / 首段，长度与服务端上限一致
    assert "parseSkillMarkdown" in script
    assert "meta.instruction" in script
    assert "SKILL_NAME_MAX = 40" in script
    assert "SKILL_DESC_MAX = 160" in script
    assert "SKILL_INSTRUCTION_MAX = 1000" in script
    # 单文件大小与数量上限、同名跳过
    assert "MAX_IMPORT_FILES = 30" in script
    assert "MAX_SKILL_FILE_BYTES" in script
    assert "已有同名 Skill" in script
    # zip 包交给后端解析（SKILL.md + references/），不执行包内脚本
    assert 'suffixOf(file.name) === ".zip"' in script
    assert "MAX_SKILL_ZIP_BYTES" in script
    assert 'api("/api/skills/import"' in script
    # 仍然复用现有 Skill API（Markdown 导入不新增接口）
    assert 'api("/api/skills"' in script
    assert ".dropzone" in styles and ".import-log" in styles


def test_skill_rows_are_compact_and_editable() -> None:
    """推荐 Skill 是正方形方块；自建仍是一行折叠，点名称展开审查重点。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 推荐方块：1:1 网格 + 名称/说明（两行截断）+ 右下角“使用”
    assert "function skillTile" in script
    assert 'class="skill-tile"' in script
    assert 'class="skill-tile-open"' in script
    assert 'class="skill-tile-name"' in script
    assert 'class="skill-tile-desc"' in script
    assert "grid-template-columns: repeat(auto-fill" in styles
    assert "aspect-ratio: 1 / 1" in styles
    assert ".skill-tile .chip" in styles

    # 自建 Skill：一行 + 展开区（名称 / 标签 / 使用 / 编辑 / 删除）
    assert 'class="skill-head"' in script
    assert 'class="skill-toggle"' in script
    assert 'data-toggle-skill' in script
    assert 'class="skill-detail"' in script
    assert 'class="skill-instruction"' in script
    assert 'data-edit-skill' in script
    assert "存为我的" in script
    assert "fillSkillForm" in script
    assert 'method: editingId ? "PATCH" : "POST"' in script
    assert "/api/skills/" in script
    # 页头那段说明（用户要求删掉）不再渲染
    assert "开箱可用" not in script
    assert 'class="page-head"' not in script
    # Skill 弹窗比默认 460px 宽一点（类选择器要带 .dialog 才有更高优先级）
    assert ".dialog.skill-dialog" in styles


def test_skill_dialog_events_are_delegated_to_document() -> None:
    """表单/导入弹窗在 #view 外：事件必须挂在 document 上，否则按钮点了没反应。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")

    assert "表单在静态弹窗里" in script
    assert 'document.addEventListener("click"' in script
    assert 'document.addEventListener("submit"' in script
    assert 'document.addEventListener("change"' in script
    assert 'document.addEventListener("drop"' in script
    # 弹窗本身是 index.html 的静态节点（不靠每次渲染重建）
    assert page.index('id="skill-new-dialog"') < page.index("/static/app.js")
    assert 'id="skill-form"' in page


def test_skill_can_declare_tools_and_attach_text_files() -> None:
    """Skill 不只有提示词：可勾选“调用工具”，也可附加 .py / .md 文本（只读，不执行）。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 表单里两块新区域：工具多选 + 附件（明确写“不会被运行”）
    assert 'id="skill-tools"' in page
    assert 'id="skill-asset-pick"' in page
    assert 'id="skill-asset-input"' in page
    assert 'id="skill-asset-list"' in page
    assert "不会被运行" in page
    assert 'accept=".py,.md,.markdown,.txt"' in page

    # 前端从后端工具目录取选项，并随表单一起提交 tools / assets
    assert 'api("/api/skills/tools")' in script
    assert "function loadSkillTools" in script
    assert "function renderToolChips" in script
    assert "function renderAssetList" in script
    assert "function addSkillAssets" in script
    assert "tools: state.skillTools" in script
    assert "assets: state.skillAssets" in script
    assert "SKILL_ASSET_SUFFIXES" in script
    assert "MAX_SKILL_ASSETS" in script
    # 启动就加载工具目录（否则弹窗里一个胶囊都没有）
    assert script.count("loadSkillTools()") >= 2

    # 列表/方块上显示“几个工具 · 几个附件”，附件只读展示在展开区
    assert "function skillMetaLine" in script
    assert "skill-tile-meta" in script
    assert "skill-asset-readonly" in script
    assert ".tool-chips" in styles and ".tool-chip" in styles
    assert ".asset-list" in styles and ".asset-code" in styles
    assert ".skill-tile-meta" in styles and ".skill-asset-readonly" in styles


def test_review_history_refreshes_right_after_review_and_decision() -> None:
    """第 6 条：审查完一份合同后侧栏历史立刻多一条，不用刷新页面。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "async function refreshHistory" in script
    # 静默拉取 + 重渲染；不覆盖审批徽标
    body = script.split("async function refreshHistory()", 1)[1][:600]
    assert '"/api/reviews?limit=20"' in body
    assert "renderHistory()" in body
    assert "setBadge" not in body

    # 两个入口都调用：开始审查成功后、人工确认成功后
    start = script.split("async function startReview(", 1)[1].split("\n  function", 1)[0]
    assert "await refreshHistory()" in start
    decide = script.split("async function decide(", 1)[1].split("\n  function", 1)[0]
    assert "await refreshHistory()" in decide

    # 登录后“登录后可以查看…”提示要收起
    assert "hint.hidden = true" in script


def test_clause_toc_uses_contract_numbering() -> None:
    """左栏原文块用合同标题（去掉重复编号）；前言仍叫“前言”。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "function clauseName" in script
    assert "function clauseNumber" not in script
    assert "function clauseLabel" not in script
    # 前言不叫“第 1 条”
    assert 'if (clause.is_preamble) return "前言";' in script
    # 名称列去掉与序号列重复的编号
    assert "replace(/^\\s*\\d{1,3}\\s*[.、]\\s*/, \"\")" in script


def test_llm_form_does_not_trigger_password_autofill() -> None:
    """API 配置不是账号密码：阻止浏览器把保存的账号密码“快捷填入”。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="llm-form" autocomplete="off"' in page
    assert 'name="llm_api_key"' in page
    assert 'autocomplete="new-password"' in page
    assert 'data-lpignore="true"' in page
    # 不要把 Key 输入框伪装成登录表单（浏览器会据此弹出账号密码建议）
    llm_form = page.split('id="llm-form"', 1)[1].split("</form>", 1)[0]
    assert "current-password" not in llm_form
    assert 'name="password"' not in llm_form
    assert 'name="email"' not in llm_form


def test_account_dialog_has_profile_settings_and_confirm_clear() -> None:
    """退出登录右侧的头像打开 B 端设置弹窗：左侧分区 + 资料 / 外观 / 数据 / 关于。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 侧栏：退出登录 + 圆形头像按钮在同一个操作行；不再显示昵称 / 邮箱
    assert 'id="account-row"' in page
    assert 'id="account-avatar"' in page
    assert 'class="avatar account-avatar"' in page
    assert 'id="account-line"' not in page
    assert "accountLine" not in script
    assert ".account-line" not in styles

    # 弹窗：左侧分区导航（个人信息 / 通用 / 数据管理 / 关于）
    assert 'id="account-dialog"' in page
    assert 'class="account-nav"' in page
    for panel in ("profile", "general", "data", "about"):
        assert f'data-account-panel="{panel}"' in page
        assert f'id="account-panel-{panel}"' in page
    assert "setAccountPanel" in script

    # 个人信息：头像 / 昵称 / 邮箱 / 注册时间
    assert 'id="account-avatar-input"' in page
    assert 'accept="image/png,image/jpeg,image/webp"' in page
    assert 'id="account-name"' in page
    assert 'id="account-created"' in page

    # 通用：配色模式（白天 / 黑夜 / 跟随系统）+ 字号 + 两个交互开关 + 恢复默认
    assert 'data-scheme-value="light"' in page
    assert 'data-scheme-value="dark"' in page
    assert 'data-scheme-value="system"' in page
    # 主题色已下线：不再有 5 套主题点
    assert 'data-theme-value="teal"' not in page
    assert "data-theme=" not in styles and ".theme-dot" not in styles
    assert 'data-font-value="lg"' in page
    assert 'id="pref-motion"' in page
    assert 'id="pref-autofocus"' in page
    assert 'id="pref-reset"' in page
    assert "root.dataset.scheme" in script and "root.dataset.font" in script
    assert "function resolvedScheme" in script
    assert 'matchMedia("(prefers-color-scheme: dark)")' in script
    assert 'html[data-scheme="dark"]' in styles
    assert "--ui-text-scale" in styles and 'html[data-font="lg"]' in styles
    assert ".account-nav" in styles
    assert ".seg-item .seg-icon" in styles

    # 数据管理：统计 / 清除本机缓存 / 清空审查记录
    assert 'id="data-review-count"' in page
    assert 'id="data-skill-count"' in page
    assert 'id="account-clear-cache"' in page
    assert 'id="account-clear-reviews"' in page
    # 清除数据必须再次确认
    assert 'id="account-confirm"' in page
    assert 'id="account-confirm-yes"' in page
    assert 'id="account-confirm-no"' in page
    assert "askClear" in script and "runClear" in script
    # 头像：选图后先裁剪（拖动 / 缩放）再压成 128px 方图，走同一套 profile 接口
    assert 'id="avatar-crop-dialog"' in page
    assert 'id="avatar-crop-canvas"' in page
    assert 'id="avatar-crop-zoom"' in page
    assert "function cropResult" in script
    assert "function cropGeometry" in script
    assert "function openCropDialog" in script
    assert "128" in script
    assert "/api/auth/profile" in script
    assert ".crop-stage" in styles
    assert ".avatar-large" in styles and ".account-confirm" in styles


def test_composer_is_compact_and_footer_spans_full_width() -> None:
    """对话框收窄一点；页脚铺满整行，政策链接贴住页面右侧且不占高度。"""
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    composer = styles.split(".composer-box {", 1)[1].split("}", 1)[0]
    assert "max-width: 720px" in composer
    assert "min-height: 44px" in styles.split(".composer-text {", 1)[1].split("}", 1)[0]

    footer = styles.split(".sheet-foot {", 1)[1].split("}", 1)[0]
    assert "width: 100%" in footer
    assert "max-width: none" in footer
    assert "padding-top: 8px" in footer
    assert "margin: 0 0 0 auto" in styles.split(".foot-links {", 1)[1].split("}", 1)[0]


def test_upload_limit_is_raised_for_scanned_contracts() -> None:
    """上传上限放宽到 30 MB（扫描件更大），提示文案与常量保持一致。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "const MAX_BYTES = 30 * 1024 * 1024;" in script
    assert "文件超过 30 MB" in script
    assert "15 MB" not in script


def test_sidebar_has_skill_repo_and_history_submenu() -> None:
    """侧栏有 Skill 仓库入口；“审查历史”展开为子目录，可改名 / 置顶 / 删除。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert "Skill 仓库" in page
    assert 'id="open-skills"' in page
    assert 'id="open-history"' in page
    assert "审查历史" in page
    assert 'id="history-sub"' in page
    # 记录操作走 PATCH / DELETE，不改等级
    assert 'method: "PATCH"' in script
    assert 'method: "DELETE"' in script
    assert "data-rename" in script and "data-pin" in script and "data-delete" in script
    assert ".rec-item" in styles and ".rec-rename" in styles


def test_auth_dialog_keeps_single_entry_and_stable_size() -> None:
    """侧栏只保留“登录”；注册在弹窗内切换，切换时高度不跳动、字段间距均匀。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    sidebar = page.split('<header class="topbar"', 1)[0]
    assert 'id="auth-login"' in sidebar
    assert 'id="auth-register"' not in sidebar
    assert 'data-auth="register"' not in sidebar

    assert 'data-auth-tab="register"' in page
    # 昵称栏直接放在表单里（登录时隐藏），邮箱与密码之间不再插一块占位
    form = page.split('id="auth-form"', 1)[1].split("</form>", 1)[0]
    assert 'id="name-field"' in form
    assert "auth-extra" not in form
    assert "auth-switch-hint" not in page
    # 弹窗正文有固定最小高度：多一个昵称栏也不会把弹窗撑大
    assert "#auth-dialog .dialog-body" in styles
    assert "min-height: 396px" in styles
    # 字段之间只有统一间距（邮箱→密码 = 10px）
    assert "gap: 10px" in styles.split(".dialog-form", 1)[1][:80]


def test_login_and_register_require_manual_consent() -> None:
    """登录与注册都必须手动勾选同意隐私条款与使用政策，默认不勾选。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="auth-consent"' in page
    assert 'type="checkbox"' in page
    assert "checked" not in page.split('id="auth-consent"', 1)[1].split(">", 1)[0]
    assert "请先勾选同意隐私条款与使用政策。" in script
    # 切到登录/注册时都复位成未勾选
    assert "consent.checked = false" in script


def test_footer_disclaimer_and_legal_dialogs() -> None:
    """免责声明放在主体底部一行；隐私条款/使用政策在右下角并弹出带编号的条款。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    main = page.split('<main class="sheet"', 1)[1].split("</main>", 1)[0]
    assert "只做合同预审辅助，不构成法律意见。" in main
    assert 'id="open-privacy"' in main
    assert 'id="open-terms"' in main
    assert 'class="sheet-foot"' in main
    # 页脚只有一行：免责在左、政策在右（不再停在 820px 阅读宽度内）
    assert 'class="foot-note"' in main and 'class="foot-links"' in main

    assert "LEGAL" in script
    assert "legal-no" in script
    assert "隐私条款" in script and "使用政策" in script
    # 每个条款都有序号（01、02…）与标题
    assert 'padStart(2, "0")' in script
    assert ".legal-no" in styles


def test_report_guide_entry_is_removed_and_coverage_is_honest() -> None:
    """界面轮 17：删掉“这份报告怎么读”与结果页抽取提示；诚实说明留在后端报告里。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
    report = (WEB_DIR.parents[1] / "app" / "nodes" / "report.py").read_text(encoding="utf-8")

    assert "这份报告怎么读" not in script
    assert "data-guide" not in script
    assert "function openGuide" not in script

    # 用户口径：结果页不再放抽取降级提示（这些信息都能删）；但报告 limitation 必须保留
    assert "review.extraction_status" not in script
    assert "review-note" not in script and ".review-note" not in styles
    assert "依赖字段的规则已跳过" not in script
    assert "未执行要素抽取" in report

    # 未命中规则时不承诺“没问题”，只说明规则没命中
    assert "规则未命中" in script
    assert "未命中不代表没有风险" in script
    assert "这一条没有发现需要修改的地方" not in script


def test_pending_review_shows_rule_findings_before_confirmation() -> None:
    """上传后立刻看到风险点：待确认状态用审批载荷里的规则结果渲染。

    真实缺陷：报告要等人工确认后才生成，若页面只看 `report.findings`，
    用户会先看到“0 处风险”再被要求确认，等于没看到风险点。
    """
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "renderApproval" in script
    assert "approval.findings" in script
    assert "findings_total" in script
    assert "待您确认" in script


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


def test_review_is_left_contract_highlight_right_reasons() -> None:
    """界面轮 16：结果页直接左原文（问题处红线/高亮）/ 右原因与修改意见。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 旧版多余信息全部删除
    for gone in (
        "review-chips",
        "function reviewChip",
        "function statusChip",
        "function focusLine",
        "逐条审查",
        "data-apply-all",
        "全部采用建议",
        "这份报告怎么读",
    ):
        assert gone not in script, f"结果页仍保留多余信息：{gone}"
    assert "导出修订稿" not in script
    assert ".review-chips" not in styles

    # 结果页顶栏（返回 / 文件名 / DOCX / PDF）与过程卡片、抽取提示都已删除：
    # 只留审批区 + 左右两栏审查内容
    workspace = script.split("function renderReviewWorkspace", 1)[1].split(
        "function clauseLevelLabel", 1
    )[0]
    for gone in ("review-bar", "review-file", "data-export", "process-slot", "review-note"):
        assert gone not in workspace, f"结果页仍保留多余信息：{gone}"
    for gone in ("review-bar", "review-file", "review-note"):
        assert gone not in styles, f"样式里仍有已删除的 {gone}"
    assert "process-slot" in script, "上传页仍需过程卡片"

    # 结果页没有过程卡片，也就不再为它轮询进度接口；轮询只在上传页生效
    result = script.split("async function renderResult", 1)[1].split(
        "function locateClauses", 1
    )[0]
    assert "beginProcess(" not in result
    assert "resumeProcessPolling" not in script
    assert "resetProcess();" in result

    # 侧栏删除历史不再二次确认
    assert "window.confirm" not in script

    # 左右两栏
    assert 'id="doc-pane"' in script and 'id="clause-detail"' in script
    assert "workbench-grid" in script

    # 左栏：整篇原文按条款分块；命中引文高亮，问题条款左侧红线
    assert "function buildDocBlocks" in script
    assert "function locateClauses" in script
    assert "function highlightedText" in script
    assert '<mark class="hl' in script
    assert ".doc-block.is-red" in styles
    assert "border-left-color: var(--negative)" in styles
    assert "mark.hl.is-red" in styles

    # 点条款联动右栏（鼠标 + 键盘）
    assert "function renderWorkbench" in script
    assert 'data-clause="' in script
    assert 'event.key !== "Enter"' in script and 'event.key !== " "' in script

    # 两栏独立滚动
    for selector in (".doc-pane {", ".clause-detail {"):
        block = styles.split(selector, 1)[1].split("}", 1)[0]
        assert "overflow-y: auto" in block, selector
        assert "overscroll-behavior: contain" in block, selector
    assert "grid-template-columns: minmax(0, 1fr)" in styles.split("@media (max-width: 900px)")[1]

    # 内容来自真实审查结果（条款聚合接口），不是前端编造
    assert "/clauses" in script
    assert "state.clauseView" in script


def test_clause_detail_offers_keep_or_fix_and_friendly_pass_note() -> None:
    """有问题的条款给修改建议 + 可编辑修订稿，可选择“采用修改 / 保留原文”并可撤销。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert "function findingBlock" in script
    assert "finding-fix" in script
    assert "建议条款（可编辑）" in script
    assert 'class="revision-input"' in script
    # 每条都能选“采用修改 / 保留原文”，已更正可撤销
    assert 'data-apply="' in script and "采用修改" in script
    assert 'data-keep="' in script and "保留原文" in script
    assert 'data-revert="' in script and "撤销更正" in script
    assert "function applyCorrection" in script
    assert "function keepClause" in script
    assert "function revertCorrection" in script
    assert "state.corrections" in script and "state.kept" in script
    assert ".detail-actions" in styles and ".clause-kept" in styles

    # 没命中规则时说“规则未命中”，并说明未命中不等于没有风险
    assert "const PASS_NOTE" in script
    assert "规则未命中" in script
    assert "未命中不代表没有风险" in script
    assert "这一条和当前规则库对照过" not in script
    assert ".pass-block" in styles and ".pass-text" in styles

    # 导出修订稿：结果页不再放 DOCX / PDF 按钮，但下载能力仍保留（POST /export）
    assert "function exportRevised" in script
    assert "filenameFromDisposition" in script
    assert "URL.createObjectURL" in script and "URL.revokeObjectURL" in script
    assert "导出修订稿" not in script


def test_logout_requires_second_confirmation_while_review_runs() -> None:
    """有审查任务没结束时，退出登录必须先弹窗说明会中断任务，再确认。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="logout-confirm"' in page
    assert "审查任务仍在进行" in page
    assert "退出会中断这次任务" in page
    assert 'id="logout-cancel"' in page
    assert 'id="logout-confirm-yes"' in page

    # 判断覆盖：上传/读取中、待人工确认、running
    assert "function hasActiveTask" in script
    assert "state.taskActive" in script
    assert 'review === "awaiting_human" || review === "running"' in script
    # 登出时清掉逐条审查的本地状态（更正 / 保留），避免串到下一个账号
    logout_body = script.split("async function doLogout()", 1)[1][:400]
    assert "state.clauseView = null" in logout_body
    assert "state.kept = {}" in logout_body
    assert "stopStream" not in logout_body
    # 取消按钮只是关弹窗，不退出
    assert 'on("logout-cancel", "click", () => closeDialog("logout-confirm"))' in script
    assert ".dialog.confirm-dialog" in styles


def test_expert_opinions_and_agent_trace_are_shown_separately() -> None:
    """专家意见只作参考（不画等级）、Agent 轨迹默认折叠；两者的样式与结构都要在。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 专家意见：中性样式 + 明确的“不判级”文案
    assert "function expertBlocks" in script
    assert "agent_trace" in script
    assert "expert_findings" in script
    assert "（参考 · " in script or "参考 · " in script
    assert "专家意见只作补充参考，不代表风险等级" in script
    assert ".expert-block" in styles and ".expert-tag" in styles and ".expert-quote" in styles

    # 轨迹：折叠面板，失败也列出，附引用
    assert "function agentTraceBlock" in script
    assert "Agent 轨迹" in script
    assert "trace-item" in script and "is-failed" in script
    assert ".trace summary" in styles and ".trace-item" in styles

    # 降级原因翻成人话（不能让用户读到 not_configured / degraded 这类枚举）
    assert "EXPERT_NOTE_LABELS" in script
    assert "未配置模型" in script and "引文未能在原文定位" in script
    assert "降级原因" in script
    assert "EXPERT_STATUS_LABELS" in script and "部分降级" in script

    # 边界：专家意见不得使用红黄绿语义色（避免被误读成等级）
    expert_css = styles.split(".expert-block", 1)[1].split("/* Agent 轨迹", 1)[0]
    for token in ("--red-bg", "--red-ink", "--amber-bg", "--green-bg"):
        assert token not in expert_css
