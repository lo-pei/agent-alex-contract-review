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
    """Skill 仓库改成独立页面：侧栏入口是 #/skills，页面内不再有仓库弹窗。"""
    page = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="skills-dialog"' not in page
    assert 'href="#/skills"' in page
    assert 'renderSkillsPage' in script
    assert 'hash === "#/skills"' in script
    # 页面里有推荐 / 我的 / 新建三块，仍复用同一套 Skill API
    assert 'id="skill-form"' in script
    assert 'class="skill-list"' in script
    assert '"/api/skills"' in script
    assert ".skills-grid" in styles


def test_skill_repo_imports_markdown_files_and_folders() -> None:
    """Skill 仓库支持把 .md 文件或整个文件夹拖进来，自动建成 Skill。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 两个入口：多选 .md 与整目录（webkitdirectory）
    assert 'id="skill-import-input"' in script
    assert 'accept=".md,.markdown,text/markdown"' in script
    assert 'id="skill-import-dir"' in script
    assert "webkitdirectory" in script
    # 拖拽区 + 键盘可达（Enter / 空格也能选文件）
    assert 'id="skill-drop"' in script
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
    # 仍然复用现有 Skill API（不新增后端接口）
    assert 'api("/api/skills"' in script
    assert ".dropzone" in styles and ".import-log" in styles


def test_skill_rows_are_compact_and_editable() -> None:
    """仓库列表默认只占一行；点开才显示审查重点，推荐 Skill 可“存为我的”。"""
    script = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    # 一行：名称 + 标签 + 使用；展开区放说明与审查重点
    assert 'class="skill-head"' in script
    assert 'class="skill-toggle"' in script
    assert 'data-toggle-skill' in script
    assert 'class="skill-detail"' in script
    assert 'class="skill-instruction"' in script
    assert 'class="chip-mini"' in script or "chip chip-mini" in script
    # 推荐 Skill 只读，但可以填进表单另存为我的；自建可编辑/删除
    assert 'data-edit-skill' in script
    assert "存为我的" in script
    assert "fillSkillForm" in script
    assert 'method: editingId ? "PATCH" : "POST"' in script
    assert "/api/skills/" in script
    # 页头那段说明（用户要求删掉）不再渲染
    assert "开箱可用" not in script
    assert 'class="page-head"' not in script
    # 右栏两个卡片紧凑：小字号、小高度、无大段留白
    assert ".skill-form .field-compact input" in styles
    assert "height: 30px" in styles
    assert ".dropzone" in styles and "padding: 11px 8px" in styles


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

    # 通用：主题色 / 字号 / 两个交互开关 / 恢复默认
    assert 'data-theme-value="teal"' in page
    assert 'data-font-value="lg"' in page
    assert 'id="pref-motion"' in page
    assert 'id="pref-autofocus"' in page
    assert 'id="pref-reset"' in page
    assert "root.dataset.theme" in script and "root.dataset.font" in script
    assert "--ui-text-scale" in styles and 'html[data-font="lg"]' in styles
    assert ".theme-dot" in styles and ".account-nav" in styles

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
    # 头像在浏览器压成 128px 方图后走同一套 profile 接口
    assert "squareThumbnail" in script
    assert "/api/auth/profile" in script
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
