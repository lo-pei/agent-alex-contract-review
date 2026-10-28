/* 外贸合同智审助手 · 前端
 *
 * 侧边栏 = 导航壳 + 审查设定（指令 / 附件 / Skill）+ 账号与入口；
 * 右侧主区只有两屏：上传合同 / 风险点。
 * 约束（ADR-003 / ADR-009 / ADR-013）：不在浏览器判级、不拼 Command、后端文本一律先转义；
 * 账号口令与 API Key 只提交给后端，浏览器不保存明文（仅 Cookie 会话）。
 */
(() => {
  "use strict";

  const MAX_BYTES = 15 * 1024 * 1024;
  const ALLOWED = [".pdf", ".docx", ".txt", ".md", ".markdown"];
  /** Skill 下拉里的固定末项：选中即打开侧栏的 Skill 仓库 */
  const SKILL_REPO_VALUE = "__repo__";
  /** Markdown 批量导入：只吃文本型 Skill 定义，大小与服务端上限对齐 */
  const SKILL_IMPORT_SUFFIXES = [".md", ".markdown"];
  const MAX_IMPORT_FILES = 30;
  const MAX_SKILL_FILE_BYTES = 200 * 1024;
  const SKILL_NAME_MAX = 40;
  const SKILL_DESC_MAX = 160;
  const SKILL_INSTRUCTION_MAX = 1000;

  const STATUS_LABEL = {
    awaiting_human: "待确认",
    running: "审查中",
    approved: "已确认",
    rejected: "已拒绝",
    changes_requested: "需修改",
    unreviewed_red_risk: "未确认",
    completed: "已完成",
    not_contract: "不是合同",
    failed: "未完成",
  };

  const dom = {
    view: document.getElementById("view"),
    main: document.getElementById("main"),
    sidebar: document.getElementById("sidebar"),
    menuButton: document.getElementById("menu-button"),
    scrim: document.getElementById("scrim"),
    crumbs: document.getElementById("crumbs-current"),
    navItems: Array.from(document.querySelectorAll(".nav-item[data-nav]")),
    reviewBadge: document.getElementById("nav-review-badge"),
    apiStatus: document.getElementById("api-status"),
    apiStatusText: document.getElementById("api-status-text"),
    authLogin: document.getElementById("auth-login"),
    authLogout: document.getElementById("auth-logout"),
    llmState: document.getElementById("llm-state"),
  };

  const state = {
    file: null,
    reviewId: null,
    busy: false,
    reviewer: "",
    focus: "",
    skillId: "",
    user: null,
    envLlm: false,
    llm: null,
    skills: [],
    providers: [],
    history: [],
    authMode: "login",
    /** 正在编辑的自建 Skill id（空串 = 新建） */
    editingSkillId: "",
    /** 右侧表单预填来源（推荐 Skill 的“存为我的”会填进来，但仍按新建提交） */
    skillFormSource: "",
    /** 有审查任务没结束（上传中 / 待人工确认）：退出时要二次确认 */
    taskActive: false,
    /** 最近一次审查的状态（awaiting_human / running 也算任务未结束） */
    reviewStatus: "",
    /** 逐条审查视图：条款数据、当前选中、已点“一键更正”的条款 */
    clauseView: null,
    selectedClause: "",
    corrections: {},
    /** 对话式流式输出的定时器（切页/退出时要清掉） */
    streamTimer: 0,
  };

  /* ---------- 基础工具 ---------- */

  function esc(value) {
    return String(value === null || value === undefined ? "" : value).replace(
      /[&<>"']/g,
      (ch) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[ch],
    );
  }

  function on(id, type, handler) {
    const el = document.getElementById(id);
    if (el) el.addEventListener(type, handler);
  }

  function humanSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  function suffixOf(name) {
    const dot = name.lastIndexOf(".");
    return dot < 0 ? "" : name.slice(dot).toLowerCase();
  }

  function spinner() {
    return '<span class="spinner" aria-hidden="true"></span>';
  }

  function formatTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (number) => String(number).padStart(2, "0");
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes())
    );
  }

  function backLink(label) {
    return (
      '<a class="back" href="#/">' +
      '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">' +
      '<path d="M14.5 6 8.5 12l6 6" fill="none" stroke="currentColor" stroke-width="1.8" ' +
      'stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      esc(label || "换一份合同") +
      "</a>"
    );
  }

  function failMessage(text) {
    state.busy = false;
    dom.view.innerHTML =
      '<section class="result">' +
      backLink() +
      '<h1 class="headline">没能完成审查</h1>' +
      '<p class="lead">' +
      esc(text) +
      "</p>" +
      '<a class="btn btn-primary" href="#/">重新上传合同</a>' +
      "</section>";
  }

  /* ---------- 弹窗 ---------- */

  function openDialog(id) {
    const dialog = document.getElementById(id);
    if (!dialog) return;
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }

  function closeDialog(id) {
    const dialog = document.getElementById(id);
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function bindDialogs() {
    document.querySelectorAll("[data-close]").forEach((button) => {
      button.addEventListener("click", () => closeDialog(button.dataset.close));
    });
    document.querySelectorAll("dialog").forEach((dialog) => {
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
      });
    });
  }

  /* ---------- 侧边栏 / 顶栏 ---------- */

  function setShell(name) {
    const title = { upload: "上传合同", review: "风险点", skills: "Skill 仓库", empty: "当前审查" }[name] || "上传合同";
    if (dom.crumbs) dom.crumbs.textContent = title;
    const active = name === "empty" ? "review" : name;
    dom.navItems.forEach((item) => {
      if (item.dataset.nav === active) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });
    closeDrawer();
  }

  function closeDrawer() {
    if (!dom.sidebar) return;
    dom.sidebar.dataset.open = "false";
    if (dom.menuButton) dom.menuButton.setAttribute("aria-expanded", "false");
    if (dom.scrim) dom.scrim.hidden = true;
  }

  function bindDrawer() {
    if (dom.menuButton) {
      dom.menuButton.addEventListener("click", () => {
        const open = dom.sidebar.dataset.open === "true";
        dom.sidebar.dataset.open = String(!open);
        dom.menuButton.setAttribute("aria-expanded", String(!open));
        if (dom.scrim) dom.scrim.hidden = open;
      });
    }
    if (dom.scrim) dom.scrim.addEventListener("click", closeDrawer);
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDrawer();
    });
  }

  function setBadge(count) {
    if (!dom.reviewBadge) return;
    if (count > 0) {
      dom.reviewBadge.textContent = String(count);
      dom.reviewBadge.hidden = false;
      dom.reviewBadge.title = count + " 处高风险";
    } else {
      dom.reviewBadge.hidden = true;
      dom.reviewBadge.textContent = "";
    }
  }

  function setApiStatus(status) {
    if (!dom.apiStatus) return;
    dom.apiStatus.dataset.state = status;
    if (dom.apiStatusText) {
      dom.apiStatusText.textContent =
        status === "online" ? "服务正常" : status === "offline" ? "服务未连接" : "连接中";
    }
  }

  async function checkHealth() {
    try {
      const response = await fetch("/health", { cache: "no-store" });
      setApiStatus(response.ok ? "online" : "offline");
    } catch (error) {
      setApiStatus("offline");
    }
  }

  /* ---------- 网络 ---------- */

  async function api(path, options) {
    const response = await fetch(path, options);
    if (response.status === 204) return null;
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      body = null;
    }
    if (!response.ok) {
      const detail = body && body.detail ? body.detail : "服务返回 " + response.status;
      const error = new Error(typeof detail === "string" ? detail : "请求未被接受");
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function jsonBody(value) {
    return {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(value),
    };
  }

  /* ---------- 路由 ---------- */

  function route() {
    const hash = location.hash || "#/";
    if (hash === "#/skills" || hash === "#/skills/") {
      setShell("skills");
      renderSkillsPage();
      return;
    }
    const match = hash.match(/^#\/review\/([A-Za-z0-9_-]{1,64})$/);
    if (match) {
      setShell("review");
      loadReview(match[1]);
      return;
    }
    if (hash === "#/review" || hash === "#/review/") {
      setShell("review");
      if (state.reviewId) {
        loadReview(state.reviewId);
      } else {
        renderNoSession();
      }
      return;
    }
    setShell("upload");
    renderUpload();
  }

  /* ---------- 侧栏入口 ---------- */

  function bindSidebarActions() {
    on("open-llm", "click", openLlmDialog);
    // Skill 仓库是独立页面（#/skills）；输入区只保留下拉选择
  }

  /* ---------- 账号 ---------- */

  async function refreshSession() {
    try {
      const info = await api("/api/auth/me");
      state.user = info && info.authenticated ? info.user : null;
      state.envLlm = !!(info && info.env_llm);
      state.llm = info && info.llm ? info.llm : null;
    } catch (error) {
      state.user = null;
      state.llm = null;
    }
    renderAccount();
    updateLlmState();
    renderUploadIfIdle();
    loadSkills();
    loadLlmSettings();
  }

  function renderAccount() {
    const user = state.user;
    if (dom.authLogin) dom.authLogin.hidden = !!user;
    const row = document.getElementById("account-row");
    if (row) row.hidden = !user;
    if (dom.authLogout) dom.authLogout.hidden = !user;
    renderAvatar();
  }

  /* ---------- 个人账户：头像 / 设置 / 数据清除 ----------
   * 头像压到 128px 的方形 JPEG 后再 PATCH /api/auth/profile（库里只存 data URL），
   * 偏好只放 localStorage，不上传后端；清空审查记录要二次确认。 */

  const PREFS_KEY = "alex.prefs";
  const DRAFT_KEY = "alex.draft";
  const DEFAULT_PREFS = { motion: false, autofocus: true, theme: "teal", font: "md" };
  const THEMES = ["teal", "indigo", "graphite", "clay", "plum"];
  const FONTS = ["sm", "md", "lg"];
  const ACCOUNT_PANELS = ["profile", "general", "data", "about"];
  const prefs = readPrefs();
  let pendingClear = "";
  let accountPanel = "profile";

  function readPrefs() {
    try {
      const raw = localStorage.getItem(PREFS_KEY);
      const data = raw ? JSON.parse(raw) : {};
      return {
        motion: !!data.motion,
        autofocus: data.autofocus !== false,
        theme: THEMES.includes(data.theme) ? data.theme : DEFAULT_PREFS.theme,
        font: FONTS.includes(data.font) ? data.font : DEFAULT_PREFS.font,
      };
    } catch (error) {
      return { ...DEFAULT_PREFS };
    }
  }

  function writePrefs() {
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
    } catch (error) {
      /* 隐私模式下写不进去也不影响使用 */
    }
    applyPrefs();
  }

  function applyPrefs() {
    const root = document.documentElement;
    root.dataset.motion = prefs.motion ? "off" : "on";
    root.dataset.theme = prefs.theme;
    root.dataset.font = prefs.font;
  }

  function avatarInitial(user) {
    const name = (user && (user.display_name || user.email)) || "";
    return (String(name).trim()[0] || "A").toUpperCase();
  }

  function avatarMarkup(user) {
    if (user && user.avatar) {
      return '<img src="' + esc(user.avatar) + '" alt="" />';
    }
    return '<span class="avatar-initial">' + esc(avatarInitial(user)) + "</span>";
  }

  function renderAvatar() {
    const small = document.getElementById("account-avatar");
    if (small) small.innerHTML = avatarMarkup(state.user);
    const large = document.getElementById("account-avatar-large");
    if (large) large.innerHTML = avatarMarkup(state.user);
    const remove = document.getElementById("account-avatar-remove");
    if (remove) remove.hidden = !(state.user && state.user.avatar);
  }

  function showAccountError(text) {
    const box = document.getElementById("account-error");
    if (!box) return;
    box.hidden = !text;
    box.textContent = text || "";
  }

  function showAccountStatus(text) {
    const box = document.getElementById("account-status");
    if (!box) return;
    box.hidden = !text;
    box.textContent = text || "";
  }

  function cancelClear() {
    pendingClear = "";
    const box = document.getElementById("account-confirm");
    if (box) box.hidden = true;
    const yes = document.getElementById("account-confirm-yes");
    if (yes) {
      yes.disabled = false;
      yes.textContent = "确认清除";
    }
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  function syncPrefControls() {
    document.querySelectorAll("[data-theme-value]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.themeValue === prefs.theme));
    });
    document.querySelectorAll("[data-font-value]").forEach((button) => {
      const active = button.dataset.fontValue === prefs.font;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const motion = document.getElementById("pref-motion");
    const autofocus = document.getElementById("pref-autofocus");
    if (motion) motion.checked = prefs.motion;
    if (autofocus) autofocus.checked = prefs.autofocus;
  }

  /** 切换弹窗左侧分区；数据/关于按需拉取，避免每次打开都请求 */
  function setAccountPanel(name) {
    accountPanel = ACCOUNT_PANELS.includes(name) ? name : "profile";
    document.querySelectorAll("[data-account-panel]").forEach((button) => {
      const active = button.dataset.accountPanel === accountPanel;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll("[data-account-section]").forEach((section) => {
      const active = section.dataset.accountSection === accountPanel;
      section.hidden = !active;
      section.classList.toggle("is-active", active);
    });
    if (accountPanel === "data") loadAccountStats();
    if (accountPanel === "about") loadAboutInfo();
  }

  async function loadAccountStats() {
    const reviews = document.getElementById("data-review-count");
    const skills = document.getElementById("data-skill-count");
    if (skills) {
      skills.textContent = String(state.skills.filter((skill) => !skill.builtin).length);
    }
    if (!reviews) return;
    try {
      const data = await api("/api/reviews?limit=500");
      reviews.textContent = String(((data && data.reviews) || []).length);
    } catch (error) {
      reviews.textContent = state.history.length ? String(state.history.length) : "—";
    }
  }

  async function loadAboutInfo() {
    const box = document.getElementById("about-version");
    if (!box) return;
    try {
      const response = await fetch("/health", { cache: "no-store" });
      const data = await response.json();
      box.textContent = "版本 " + (data.version || "—");
    } catch (error) {
      box.textContent = "版本 —";
    }
  }

  function resetPrefs() {
    Object.assign(prefs, DEFAULT_PREFS);
    writePrefs();
    syncPrefControls();
    showAccountStatus("已恢复默认外观与交互设置。");
  }

  function renderAccountDialog() {
    const user = state.user;
    if (!user) return;
    const name = document.getElementById("account-name");
    const email = document.getElementById("account-email");
    const created = document.getElementById("account-created");
    const profileName = document.getElementById("profile-name");
    const profileMail = document.getElementById("profile-mail");
    if (name) name.value = user.display_name || "";
    if (email) email.value = user.email || "";
    if (created) created.value = formatDate(user.created_at);
    if (profileName) profileName.textContent = user.display_name || "未设置昵称";
    if (profileMail) profileMail.textContent = user.email || "";
    syncPrefControls();
    showAccountError("");
    showAccountStatus("");
    cancelClear();
    renderAvatar();
  }

  function openAccountDialog() {
    if (!state.user) {
      openAuth("login");
      return;
    }
    renderAccountDialog();
    setAccountPanel("profile");
    openDialog("account-dialog");
  }

  function pickAvatar() {
    const input = document.getElementById("account-avatar-input");
    if (input) input.click();
  }

  /** 居中裁成正方形并压到 size×size 的 JPEG，避免把整张原图塞进 SQLite */
  function squareThumbnail(file, size) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        try {
          const canvas = document.createElement("canvas");
          canvas.width = size;
          canvas.height = size;
          const context = canvas.getContext("2d");
          context.fillStyle = "#ffffff";
          context.fillRect(0, 0, size, size);
          const side = Math.min(image.width, image.height);
          context.drawImage(
            image,
            (image.width - side) / 2,
            (image.height - side) / 2,
            side,
            side,
            0,
            0,
            size,
            size,
          );
          resolve(canvas.toDataURL("image/jpeg", 0.85));
        } catch (error) {
          reject(error);
        } finally {
          URL.revokeObjectURL(url);
        }
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("图片读取失败，请换一张试试。"));
      };
      image.src = url;
    });
  }

  async function patchProfile(body) {
    return api("/api/auth/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function uploadAvatar(event) {
    const input = event.target;
    const file = input && input.files ? input.files[0] : null;
    if (input) input.value = "";
    if (!file) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      showAccountError("请选择 PNG / JPG / WebP 图片。");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showAccountError("图片请小于 5 MB。");
      return;
    }
    try {
      const dataUrl = await squareThumbnail(file, 128);
      state.user = await patchProfile({ avatar: dataUrl });
      renderAccount();
      renderAvatar();
      showAccountError("");
      showAccountStatus("头像已更新。");
    } catch (error) {
      if (error.status === 401) openAuth("login");
      showAccountError(error.message || "头像保存失败，请重试。");
    }
  }

  async function removeAvatar() {
    try {
      state.user = await patchProfile({ avatar: "" });
      renderAccount();
      renderAvatar();
      showAccountStatus("已恢复默认头像（昵称首字母）。");
    } catch (error) {
      showAccountError(error.message || "操作失败，请重试。");
    }
  }

  async function saveAccountProfile(event) {
    event.preventDefault();
    const name = document.getElementById("account-name");
    const value = name ? name.value.trim() : "";
    if (!value) {
      showAccountError("昵称不能为空。");
      return;
    }
    const save = document.getElementById("account-save");
    if (save) {
      save.disabled = true;
      save.textContent = "保存中…";
    }
    try {
      state.user = await patchProfile({ display_name: value });
      renderAccount();
      renderAccountDialog();
      showAccountStatus("资料已保存。");
    } catch (error) {
      if (error.status === 401) openAuth("login");
      showAccountError(error.message || "保存失败，请重试。");
    } finally {
      if (save) {
        save.disabled = false;
        save.textContent = "保存资料";
      }
    }
  }

  async function askClear(kind) {
    pendingClear = kind;
    showAccountError("");
    showAccountStatus("");
    const box = document.getElementById("account-confirm");
    const text = document.getElementById("account-confirm-text");
    if (kind === "reviews") {
      let count = state.history.length;
      try {
        const data = await api("/api/reviews?limit=500");
        count = data && data.reviews ? data.reviews.length : count;
      } catch (error) {
        /* 拉不到数量就按本地缓存的条数提示 */
      }
      if (!count) {
        pendingClear = "";
        showAccountStatus("还没有审查记录，不需要清除。");
        return;
      }
      if (text) {
        text.textContent =
          "将删除账号下 " + count + " 条审查记录（含上传的合同、报告与待确认项），不可恢复。确认清除？";
      }
    } else if (text) {
      text.textContent =
        "将清除浏览器里保存的界面偏好与草稿；账号里的审查记录、Skill 与头像不受影响。确认清除？";
    }
    if (box) box.hidden = false;
  }

  async function runClear() {
    const yes = document.getElementById("account-confirm-yes");
    if (yes) {
      yes.disabled = true;
      yes.textContent = "清除中…";
    }
    const kind = pendingClear;
    try {
      if (kind === "reviews") {
        const data = await api("/api/reviews?limit=500");
        const items = (data && data.reviews) || [];
        for (const item of items) {
          await api("/api/reviews/" + encodeURIComponent(item.review_id), {
            method: "DELETE",
          });
        }
        state.reviewId = null;
        state.history = [];
        if (historySubOpen()) await loadHistory();
        showAccountStatus("已清空 " + items.length + " 条审查记录。");
      } else {
        try {
          localStorage.removeItem(PREFS_KEY);
          localStorage.removeItem(DRAFT_KEY);
        } catch (error) {
          /* 隐私模式下删不掉也不报错 */
        }
        prefs.motion = DEFAULT_PREFS.motion;
        prefs.autofocus = DEFAULT_PREFS.autofocus;
        prefs.theme = DEFAULT_PREFS.theme;
        prefs.font = DEFAULT_PREFS.font;
        applyPrefs();
        renderAccountDialog();
        showAccountStatus("已清除本机缓存。");
      }
    } catch (error) {
      if (error.status === 401) openAuth("login");
      showAccountError(error.message || "清除失败，请重试。");
    } finally {
      pendingClear = "";
      if (yes) {
        yes.disabled = false;
        yes.textContent = "确认清除";
      }
      const box = document.getElementById("account-confirm");
      if (box) box.hidden = true;
    }
  }

  function bindAccount() {
    on("account-avatar", "click", openAccountDialog);
    on("account-avatar-large", "click", pickAvatar);
    on("account-avatar-pick", "click", pickAvatar);
    on("account-avatar-input", "change", uploadAvatar);
    on("account-avatar-remove", "click", removeAvatar);
    on("account-form", "submit", saveAccountProfile);

    const tabs = Array.from(document.querySelectorAll("[data-account-panel]"));
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => setAccountPanel(tab.dataset.accountPanel));
      tab.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
        event.preventDefault();
        const index = tabs.indexOf(tab);
        const step = event.key === "ArrowDown" ? 1 : -1;
        const next = tabs[(index + step + tabs.length) % tabs.length];
        setAccountPanel(next.dataset.accountPanel);
        next.focus();
      });
    });

    document.querySelectorAll("[data-theme-value]").forEach((button) => {
      button.addEventListener("click", () => {
        prefs.theme = button.dataset.themeValue;
        writePrefs();
        syncPrefControls();
      });
    });
    document.querySelectorAll("[data-font-value]").forEach((button) => {
      button.addEventListener("click", () => {
        prefs.font = button.dataset.fontValue;
        writePrefs();
        syncPrefControls();
      });
    });

    on("pref-reset", "click", resetPrefs);
    on("about-privacy", "click", () => openLegal("privacy"));
    on("about-terms", "click", () => openLegal("terms"));

    on("pref-motion", "change", (event) => {
      prefs.motion = event.target.checked;
      writePrefs();
    });
    on("pref-autofocus", "change", (event) => {
      prefs.autofocus = event.target.checked;
      writePrefs();
    });
    on("account-clear-cache", "click", () => askClear("cache"));
    on("account-clear-reviews", "click", () => askClear("reviews"));
    on("account-confirm-yes", "click", runClear);
    on("account-confirm-no", "click", cancelClear);
  }

  function setAuthMode(mode) {
    state.authMode = mode === "register" ? "register" : "login";
    const title = document.getElementById("auth-title");
    if (title) title.textContent = state.authMode === "register" ? "注册" : "登录";
    const nameField = document.getElementById("name-field");
    if (nameField) nameField.hidden = state.authMode !== "register";
    const submit = document.getElementById("auth-submit");
    if (submit) submit.textContent = state.authMode === "register" ? "注册并登录" : "登录";
    const note = document.getElementById("auth-note");
    if (note) {
      note.textContent =
        state.authMode === "register"
          ? "密码至少 8 位。口令只保存加盐哈希，不会回传。"
          : "登录后，上传的合同与审查结论会记录在你的账号下。";
    }
    document.querySelectorAll("[data-auth-tab]").forEach((tab) => {
      const active = tab.dataset.authTab === state.authMode;
      tab.setAttribute("aria-selected", String(active));
      tab.classList.toggle("is-active", active);
    });
    const error = document.getElementById("auth-error");
    if (error) error.hidden = true;
    // 每次切换模式都恢复“未勾选”，避免沿用上一次的同意状态
    const consent = document.getElementById("auth-consent");
    if (consent) consent.checked = false;
  }

  function openAuth(mode) {
    setAuthMode(mode);
    const consent = document.getElementById("auth-consent");
    if (consent) consent.checked = false;
    openDialog("auth-dialog");
    const email = document.getElementById("auth-email");
    if (email) email.focus();
  }

  function bindAuth() {
    document.querySelectorAll("[data-auth]").forEach((button) => {
      button.addEventListener("click", () => openAuth(button.dataset.auth));
    });
    document.querySelectorAll("[data-auth-tab]").forEach((tab) => {
      tab.addEventListener("click", () => setAuthMode(tab.dataset.authTab));
    });
    if (dom.authLogout) {
      dom.authLogout.addEventListener("click", () => {
        if (hasActiveTask()) {
          openDialog("logout-confirm");
          return;
        }
        doLogout();
      });
    }
    on("logout-cancel", "click", () => closeDialog("logout-confirm"));
    on("logout-confirm-yes", "click", () => {
      closeDialog("logout-confirm");
      doLogout();
    });
    on("auth-form", "submit", submitAuth);
    on("auth-consent-terms", "click", () => openLegal("terms"));
    on("auth-consent-privacy", "click", () => openLegal("privacy"));
  }

  /** 有没有“正在进行”的审查：上传/读取中，或停在人工确认（都算未结束）。 */
  function hasActiveTask() {
    if (state.busy || state.taskActive) return true;
    const review = state.reviewStatus;
    if (!review) return false;
    return review === "awaiting_human" || review === "running";
  }

  async function doLogout() {
    stopStream();
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch (error) {
      /* 退出失败也要把本地状态清掉 */
    }
    state.user = null;
    state.llm = null;
    state.history = [];
    state.taskActive = false;
    state.clauseView = null;
    state.corrections = {};
    closeDialog("account-dialog");
    cancelClear();
    renderAccount();
    updateLlmState();
    renderUploadIfIdle();
    await loadSkills();
    if (historySubOpen()) loadHistory();
    closeDrawer();
  }

  async function submitAuth(event) {
    event.preventDefault();
    const email = document.getElementById("auth-email");
    const password = document.getElementById("auth-password");
    const name = document.getElementById("auth-name");
    const consent = document.getElementById("auth-consent");
    const submit = document.getElementById("auth-submit");
    const errorBox = document.getElementById("auth-error");

    const emailValue = email ? email.value.trim() : "";
    const passwordValue = password ? password.value : "";
    if (errorBox) errorBox.hidden = true;

    if (!emailValue || !passwordValue) {
      showAuthError("请填写邮箱和密码。");
      return;
    }
    if (state.authMode === "register" && passwordValue.length < 8) {
      showAuthError("密码至少 8 位。");
      return;
    }
    // 需求：登录与注册都必须手动勾选同意隐私政策与使用条款（默认不勾选）
    if (!consent || !consent.checked) {
      showAuthError("请先勾选同意隐私条款与使用政策。");
      return;
    }

    const path = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
    const payload = {
      email: emailValue,
      password: passwordValue,
      display_name: name ? name.value.trim() : "",
    };
    if (submit) {
      submit.disabled = true;
      submit.innerHTML = spinner() + "请稍候…";
    }
    try {
      await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (password) password.value = "";
      if (name) name.value = "";
      closeDialog("auth-dialog");
      await refreshSession();
    } catch (error) {
      showAuthError(error.message || "登录失败，请重试。");
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = state.authMode === "register" ? "注册并登录" : "登录";
      }
    }
  }

  function showAuthError(text) {
    const box = document.getElementById("auth-error");
    if (!box) return;
    box.textContent = text;
    box.hidden = false;
  }

  /* ---------- Skill ---------- */

  function skillById(id) {
    if (!id) return null;
    return state.skills.find((skill) => skill.id === id) || null;
  }

  async function loadSkills() {
    try {
      const data = await api("/api/skills");
      state.skills = (data && data.skills) || [];
    } catch (error) {
      state.skills = [];
    }
    renderSkillSelect();
    renderSkillList();
    const count = document.getElementById("skill-count");
    if (count) {
      count.textContent = String(state.skills.length);
      count.hidden = state.skills.length === 0;
    }
  }

  /** 默认 Skill：内置「全量体检」，没有就取第一个可用的 */
  function defaultSkillId() {
    const full = state.skills.find((skill) => skill.id === "builtin:full");
    return full ? full.id : state.skills[0] ? state.skills[0].id : "";
  }

  function renderSkillSelect() {
    // 下拉只在聊天输入区里存在；结果页/仓库页不需要
    if (state.skillId && !skillById(state.skillId)) state.skillId = "";
    // 默认就有几个内置 Skill 可选；最后一项固定为“Skill 仓库”（选中即打开仓库页）
    if (!state.skillId) state.skillId = defaultSkillId();
    const menu = document.getElementById("skill-menu");
    if (menu) {
      menu.innerHTML =
        state.skills
          .map(
            (skill) =>
              '<li role="none"><button class="skill-option" type="button" role="option" ' +
              'data-skill="' +
              esc(skill.id) +
              '" aria-selected="' +
              (skill.id === state.skillId ? "true" : "false") +
              '">' +
              '<span class="skill-option-name">' +
              esc(skill.name) +
              "</span>" +
              '<span class="skill-option-tag">' +
              (skill.builtin ? "推荐" : "我的") +
              "</span></button></li>",
          )
          .join("") +
        '<li class="skill-menu-sep" role="separator"></li>' +
        '<li role="none"><button class="skill-option is-repo" type="button" role="option" ' +
        'data-skill="' +
        SKILL_REPO_VALUE +
        '" aria-selected="false">' +
        "<span>Skill 仓库…</span><span>管理</span></button></li>";
    }
    updateSkillTrigger();
  }

  function updateSkillTrigger() {
    const label = document.getElementById("skill-current");
    if (label) {
      const skill = skillById(state.skillId);
      label.textContent = skill ? skill.name : "选择 Skill";
      label.title = skill ? skill.name : "";
    }
    const menu = document.getElementById("skill-menu");
    if (!menu) return;
    menu.querySelectorAll("[data-skill]").forEach((option) => {
      option.setAttribute(
        "aria-selected",
        option.dataset.skill === state.skillId ? "true" : "false",
      );
    });
  }

  function closeSkillMenu() {
    const menu = document.getElementById("skill-menu");
    const trigger = document.getElementById("skill-select");
    if (menu) menu.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  }

  function toggleSkillMenu() {
    const menu = document.getElementById("skill-menu");
    const trigger = document.getElementById("skill-select");
    if (!menu || !trigger) return;
    const open = menu.hidden;
    menu.hidden = !open;
    trigger.setAttribute("aria-expanded", String(open));
    if (open) {
      const selected = menu.querySelector('[aria-selected="true"]');
      const target = selected || menu.querySelector("[data-skill]");
      if (target) target.focus();
    }
  }

  function onSkillSelectChange(value) {
    if (value === SKILL_REPO_VALUE) {
      // 仓库是入口不是选项：跳到独立页面，选择保持不变
      closeSkillMenu();
      location.hash = "#/skills";
      return;
    }
    state.skillId = value;
    updateSkillTrigger();
    closeSkillMenu();
    const trigger = document.getElementById("skill-select");
    if (trigger) trigger.focus();
  }

  /** 列表项：默认只占一行（名称 + 标签 + 使用），点开才显示审查重点与编辑按钮。 */
  function skillRow(skill) {
    const id = esc(skill.id);
    const detailId = "skill-detail-" + id;
    return (
      '<li class="skill-item' +
      (state.editingSkillId === skill.id ? " is-editing" : "") +
      '">' +
      '<div class="skill-head">' +
      '<button class="skill-toggle" type="button" data-toggle-skill="' +
      id +
      '" aria-expanded="false" aria-controls="' +
      detailId +
      '">' +
      '<span class="skill-name">' +
      esc(skill.name) +
      "</span>" +
      '<span class="skill-tag">我的</span>' +
      '<svg class="skill-caret" viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">' +
      '<path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      "</button>" +
      '<button class="chip chip-mini" type="button" data-use-skill="' +
      id +
      '">使用</button>' +
      "</div>" +
      '<div class="skill-detail" id="' +
      detailId +
      '" hidden>' +
      (skill.description ? '<p class="skill-desc">' + esc(skill.description) + "</p>" : "") +
      '<p class="skill-instruction">' +
      esc(skill.instruction) +
      "</p>" +
      '<div class="skill-actions">' +
      '<button class="chip chip-mini chip-quiet" type="button" data-edit-skill="' +
      id +
      '">编辑</button>' +
      '<button class="chip chip-mini chip-quiet" type="button" data-delete-skill="' +
      id +
      '">删除</button>' +
      "</div>" +
      "</div>" +
      "</li>"
    );
  }

  /** 推荐 Skill：正方形小方块（名称 + 两句说明 + 使用），点方块看详情或另存。 */
  function skillTile(skill) {
    const id = esc(skill.id);
    return (
      '<li class="skill-tile">' +
      '<button class="skill-tile-open" type="button" data-edit-skill="' +
      id +
      '" aria-label="查看 ' +
      esc(skill.name) +
      '">' +
      '<span class="skill-tile-name">' +
      esc(skill.name) +
      "</span>" +
      '<span class="skill-tile-desc">' +
      esc(skill.description || skill.instruction || "") +
      "</span>" +
      "</button>" +
      '<button class="chip chip-mini" type="button" data-use-skill="' +
      id +
      '">使用</button>' +
      "</li>"
    );
  }

  function renderSkillList() {
    const builtinBox = document.getElementById("skill-builtin");
    const ownBox = document.getElementById("skill-own");
    if (builtinBox) {
      builtinBox.innerHTML = state.skills.filter((skill) => skill.builtin).map(skillTile).join("");
    }
    if (ownBox) {
      const own = state.skills.filter((skill) => !skill.builtin);
      ownBox.innerHTML = own.length
        ? own.map(skillRow).join("")
        : '<li class="skill-empty">' +
          (state.user ? "还没有自建 Skill，点右上角“新建 Skill”写一个。" : "登录后可以创建自己的 Skill。") +
          "</li>";
    }
    const submit = document.getElementById("skill-submit");
    if (submit) submit.disabled = !state.user;
    const note = document.getElementById("skill-login-note");
    if (note) note.hidden = !!state.user;
    updateSkillFormMode();
  }

  function renderSkillsPage() {
    // 每次进入仓库页都从“新建”开始：编辑/预填状态不跨页面保留
    state.editingSkillId = "";
    state.skillFormSource = "";
    dom.view.innerHTML =
      '<section class="skills-page">' +
      '<header class="skills-head">' +
      '<div class="skills-head-text">' +
      '<h1 class="headline">Skill 仓库</h1>' +
      '<p class="skills-sub">推荐 Skill 可直接使用；点方块可查看审查重点或另存为我的 Skill。</p>' +
      "</div>" +
      '<div class="skills-head-actions">' +
      '<button class="btn btn-compact" type="button" id="skill-import-open">导入</button>' +
      '<button class="btn btn-primary btn-compact" type="button" id="skill-new-open">+ 新建 Skill</button>' +
      "</div>" +
      "</header>" +
      '<div class="skills-column">' +
      '<h2 class="panel-title">推荐 Skill</h2>' +
      '<ul class="skill-tiles" id="skill-builtin"></ul>' +
      '<h2 class="panel-title">我的 Skill</h2>' +
      '<ul class="skill-list" id="skill-own"></ul>' +
      "</div>" +
      "</section>";
    renderSkillList();
    // 进页面就拉一次：新导入/新建的 Skill 不必等刷新会话才出现
    loadSkills();
  }

  /** 弹窗表单的“新建 / 编辑 / 存为我的”状态（标题、按钮文案、取消按钮） */
  function updateSkillFormMode() {
    const editing = !!state.editingSkillId;
    const title = document.getElementById("skill-form-title");
    const submit = document.getElementById("skill-submit");
    const cancel = document.getElementById("skill-form-cancel");
    if (title) {
      title.textContent = editing
        ? "编辑我的 Skill"
        : state.skillFormSource
          ? "存为我的 Skill"
          : "新建 Skill";
    }
    if (submit) {
      submit.textContent = editing
        ? "保存修改"
        : state.skillFormSource
          ? "存为我的"
          : "保存 Skill";
    }
    if (cancel) cancel.hidden = false;
  }

  function resetSkillForm() {
    const name = document.getElementById("skill-name");
    const desc = document.getElementById("skill-desc");
    const instruction = document.getElementById("skill-instruction");
    if (name) name.value = "";
    if (desc) desc.value = "";
    if (instruction) instruction.value = "";
    state.editingSkillId = "";
    state.skillFormSource = "";
    const errorBox = document.getElementById("skill-error");
    if (errorBox) errorBox.hidden = true;
    updateSkillFormMode();
  }

  /** 点 Skill 的“编辑 / 存为我的”：把内容填进弹窗表单并打开。 */
  function fillSkillForm(skill) {
    if (!state.user) {
      openAuth("login");
      showSkillError("请先登录，再保存自己的 Skill。");
      return;
    }
    const name = document.getElementById("skill-name");
    const desc = document.getElementById("skill-desc");
    const instruction = document.getElementById("skill-instruction");
    if (!name || !desc || !instruction) return;
    if (skill.builtin) {
      state.editingSkillId = "";
      state.skillFormSource = skill.id;
      name.value = truncateText(skill.name + "（我的）", SKILL_NAME_MAX);
    } else {
      state.editingSkillId = skill.id;
      state.skillFormSource = "";
      name.value = skill.name;
    }
    desc.value = skill.description || "";
    instruction.value = skill.instruction || "";
    const errorBox = document.getElementById("skill-error");
    if (errorBox) errorBox.hidden = true;
    updateSkillFormMode();
    openDialog("skill-new-dialog");
    name.focus({ preventScroll: true });
  }

  /** 仓库页右上角“+ 新建 Skill”：清空表单后打开弹窗。 */
  function openSkillCreate() {
    if (!state.user) {
      openAuth("login");
      showSkillError("请先登录，再保存自己的 Skill。");
      return;
    }
    resetSkillForm();
    openDialog("skill-new-dialog");
    const name = document.getElementById("skill-name");
    if (name) name.focus({ preventScroll: true });
  }

  function openSkillImport() {
    if (!state.user) {
      openAuth("login");
      return;
    }
    showSkillImportError("");
    openDialog("skill-import-dialog");
  }

  function bindSkills() {
    // 列表在 #view 里、表单在静态弹窗里：统一在 document 上做事件委托
    document.addEventListener("click", async (event) => {
      if (event.target.closest("#skill-new-open")) {
        openSkillCreate();
        return;
      }
      if (event.target.closest("#skill-import-open")) {
        openSkillImport();
        return;
      }
      if (event.target.closest("#skill-form-cancel")) {
        resetSkillForm();
        closeDialog("skill-new-dialog");
        return;
      }
      const toggle = event.target.closest("[data-toggle-skill]");
      if (toggle) {
        const item = toggle.closest(".skill-item");
        const detail = item ? item.querySelector(".skill-detail") : null;
        if (detail) {
          const open = detail.hidden;
          detail.hidden = !open;
          item.classList.toggle("is-open", open);
          toggle.setAttribute("aria-expanded", String(open));
        }
        return;
      }
      const editButton = event.target.closest("[data-edit-skill]");
      if (editButton) {
        const skill = state.skills.find((item) => item.id === editButton.dataset.editSkill);
        if (skill) fillSkillForm(skill);
        return;
      }
      const useButton = event.target.closest("[data-use-skill]");
      if (useButton) {
        state.skillId = useButton.dataset.useSkill;
        location.hash = "#/";
        return;
      }
      const deleteButton = event.target.closest("[data-delete-skill]");
      if (deleteButton) {
        const id = deleteButton.dataset.deleteSkill;
        deleteButton.disabled = true;
        try {
          await api("/api/skills/" + encodeURIComponent(id), { method: "DELETE" });
          if (state.skillId === id) state.skillId = "";
          await loadSkills();
        } catch (error) {
          showSkillError(error.message || "删除失败，请重试。");
          deleteButton.disabled = false;
        }
        return;
      }
      if (event.target.closest("#skill-drop") || event.target.closest("#skill-import-files")) {
        pickSkillFiles();
        return;
      }
      if (event.target.closest("#skill-import-folder")) pickSkillFolder();
    });
    document.addEventListener("submit", (event) => {
      if (event.target && event.target.id === "skill-form") submitSkill(event);
    });
    // 文件夹 / 多选文件：input 在静态弹窗里，按 id 过滤
    document.addEventListener("change", (event) => {
      const target = event.target;
      if (!target || !target.files) return;
      if (target.id !== "skill-import-input" && target.id !== "skill-import-dir") return;
      const files = Array.from(target.files);
      target.value = "";
      importSkillFiles(files);
    });
    document.addEventListener("dragover", (event) => {
      const zone = event.target.closest("#skill-drop");
      if (!zone) return;
      event.preventDefault();
      zone.classList.add("is-over");
    });
    document.addEventListener("dragleave", (event) => {
      const zone = event.target.closest("#skill-drop");
      if (zone) zone.classList.remove("is-over");
    });
    document.addEventListener("drop", async (event) => {
      const zone = event.target.closest("#skill-drop");
      if (!zone) return;
      event.preventDefault();
      zone.classList.remove("is-over");
      importSkillFiles(await filesFromDataTransfer(event.dataTransfer));
    });
    document.addEventListener("keydown", (event) => {
      if (event.target.id !== "skill-drop") return;
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      pickSkillFiles();
    });
    // 下拉菜单：点空白处或按 Esc 收起（整个页面只绑一次）
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".skill-picker")) closeSkillMenu();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSkillMenu();
    });
  }

  async function submitSkill(event) {
    event.preventDefault();
    const name = document.getElementById("skill-name");
    const description = document.getElementById("skill-desc");
    const instruction = document.getElementById("skill-instruction");
    const submit = document.getElementById("skill-submit");
    const errorBox = document.getElementById("skill-error");
    if (errorBox) errorBox.hidden = true;

    if (!state.user) {
      openAuth("login");
      showSkillError("请先登录，再保存自己的 Skill。");
      return;
    }
    if (!name || !instruction || !name.value.trim() || !instruction.value.trim()) {
      showSkillError("名称与审查重点指令都不能为空。");
      return;
    }
    if (submit) {
      submit.disabled = true;
      submit.innerHTML = spinner() + "保存中…";
    }
    const editingId = state.editingSkillId;
    try {
      const saved = await api(
        editingId ? "/api/skills/" + encodeURIComponent(editingId) : "/api/skills",
        {
          method: editingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name.value.trim(),
            description: description ? description.value.trim() : "",
            instruction: instruction.value.trim(),
          }),
        },
      );
      if (name) name.value = "";
      if (description) description.value = "";
      if (instruction) instruction.value = "";
      state.editingSkillId = "";
      state.skillFormSource = "";
      state.skillId = saved.id;
      await loadSkills();
      renderSkillSelect();
      updateSkillFormMode();
      closeDialog("skill-new-dialog");
    } catch (error) {
      if (error.status === 401) openAuth("login");
      showSkillError(error.message || "保存失败，请重试。");
    } finally {
      if (submit) {
        submit.disabled = !state.user;
        updateSkillFormMode();
      }
    }
  }

  function showSkillError(text) {
    const box = document.getElementById("skill-error");
    if (!box) return;
    box.textContent = text;
    box.hidden = false;
  }

  /* ---------- Skill：Markdown / 文件夹批量导入 ---------- */

  function pickSkillFiles() {
    const input = document.getElementById("skill-import-input");
    if (input) input.click();
  }

  function pickSkillFolder() {
    const input = document.getElementById("skill-import-dir");
    if (input) input.click();
  }

  function showSkillImportError(text) {
    const box = document.getElementById("skill-import-error");
    if (!box) return;
    box.textContent = text || "";
    box.hidden = !text;
  }

  function truncateText(value, limit) {
    const text = String(value || "");
    return text.length > limit ? text.slice(0, limit).trim() : text;
  }

  function plainInline(value) {
    return String(value || "")
      .replace(/`([^`]*)`/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/\[([^\]]+)\]\(([^)]*)\)/g, "$1")
      .replace(/\s+/g, " ")
      .trim();
  }

  /** 解析一个 Markdown 文件：frontmatter（name/description/instruction）优先，其次标题与首段。 */
  function parseSkillMarkdown(fileName, rawText) {
    const text = String(rawText || "").replace(/\r\n?/g, "\n");
    const meta = {};
    let body = text;
    const front = text.match(/^---\n([\s\S]*?)\n---\n?/);
    if (front) {
      front[1].split("\n").forEach((line) => {
        const pair = line.match(/^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$/);
        if (pair) meta[pair[1].toLowerCase()] = pair[2].trim().replace(/^["']|["']$/g, "");
      });
      body = text.slice(front[0].length);
    }
    const heading = (body.match(/^#\s+(.+)$/m) || [])[1];
    const baseName = String(fileName || "未命名").replace(/\.[^.]+$/, "");
    const name = truncateText(plainInline(meta.name || heading || baseName), SKILL_NAME_MAX);
    const paragraph = body
      .split("\n")
      .map((line) => line.trim())
      .find(
        (line) =>
          line &&
          !/^#{1,6}\s/.test(line) &&
          !/^[-*+>]\s/.test(line) &&
          !/^\|/.test(line) &&
          !/^---+$/.test(line),
      );
    const description = truncateText(
      plainInline(meta.description || paragraph || ""),
      SKILL_DESC_MAX,
    );
    const normalized = (meta.instruction || body).trim().replace(/\n{3,}/g, "\n\n");
    return {
      name,
      description,
      instruction: truncateText(normalized, SKILL_INSTRUCTION_MAX),
      truncated: normalized.length > SKILL_INSTRUCTION_MAX,
    };
  }

  function readEntryFiles(entry) {
    if (!entry) return Promise.resolve([]);
    if (entry.isFile) {
      return new Promise((resolve) => {
        entry.file(
          (file) => resolve([file]),
          () => resolve([]),
        );
      });
    }
    if (!entry.isDirectory) return Promise.resolve([]);
    return new Promise((resolve) => {
      const reader = entry.createReader();
      const collected = [];
      const readNext = () => {
        reader.readEntries(
          (batch) => {
            if (!batch.length) {
              resolve(collected);
              return;
            }
            Promise.all(batch.map(readEntryFiles)).then((groups) => {
              groups.forEach((group) => collected.push(...group));
              readNext();
            });
          },
          () => resolve(collected),
        );
      };
      readNext();
    });
  }

  /** 拖入的可能是文件夹（webkitGetAsEntry），逐个读成文件列表。 */
  async function filesFromDataTransfer(transfer) {
    const items = transfer && transfer.items ? Array.from(transfer.items) : [];
    const entries = items
      .map((item) => (item.webkitGetAsEntry ? item.webkitGetAsEntry() : null))
      .filter(Boolean);
    if (entries.length) {
      const groups = await Promise.all(entries.map(readEntryFiles));
      return groups.flat();
    }
    return transfer && transfer.files ? Array.from(transfer.files) : [];
  }

  async function importSkillFiles(files) {
    showSkillImportError("");
    const log = document.getElementById("skill-import-log");
    const lines = [];
    if (log) {
      log.innerHTML = "";
      log.hidden = true;
    }
    const addLog = (text, kind) => {
      lines.push('<li class="' + kind + '">' + text + "</li>");
      if (log) {
        log.innerHTML = lines.join("");
        log.hidden = false;
      }
    };
    if (!state.user) {
      showSkillImportError("请先登录，再导入 Skill。");
      openAuth("login");
      return;
    }
    const list = (files || []).filter((file) =>
      SKILL_IMPORT_SUFFIXES.includes(suffixOf(file.name)),
    );
    if (!list.length) {
      showSkillImportError("没有可导入的 Markdown（.md / .markdown）文件。");
      return;
    }
    if (list.length > MAX_IMPORT_FILES) {
      showSkillImportError("一次最多导入 " + MAX_IMPORT_FILES + " 个文件，请分批拖入。");
      return;
    }
    const existing = new Set(state.skills.map((skill) => skill.name.trim().toLowerCase()));
    let imported = 0;
    for (const file of list) {
      const label = esc(file.webkitRelativePath || file.name);
      if (file.size > MAX_SKILL_FILE_BYTES) {
        addLog(label + "：超过 " + humanSize(MAX_SKILL_FILE_BYTES) + "，已跳过", "bad");
        continue;
      }
      let text = "";
      try {
        text = await file.text();
      } catch (error) {
        addLog(label + "：读不出内容", "bad");
        continue;
      }
      const parsed = parseSkillMarkdown(file.name, text);
      if (!parsed.name || !parsed.instruction) {
        addLog(label + "：没有可用的名称或审查重点", "bad");
        continue;
      }
      if (existing.has(parsed.name.toLowerCase())) {
        addLog(label + "：已有同名 Skill「" + esc(parsed.name) + "」，跳过", "skip");
        continue;
      }
      try {
        const created = await api("/api/skills", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: parsed.name,
            description: parsed.description,
            instruction: parsed.instruction,
          }),
        });
        existing.add(created.name.trim().toLowerCase());
        imported += 1;
        addLog(
          label +
            " → 「" +
            esc(created.name) +
            "」" +
            (parsed.truncated ? "（审查重点已截断到 " + SKILL_INSTRUCTION_MAX + " 字）" : ""),
          "ok",
        );
      } catch (error) {
        if (error.status === 401) {
          addLog(label + "：登录状态失效，导入已停止", "bad");
          openAuth("login");
          break;
        }
        addLog(label + "：" + esc(error.message || "导入失败"), "bad");
      }
    }
    if (imported) {
      await loadSkills();
      renderSkillList();
      renderSkillSelect();
    } else {
      showSkillImportError("这次没有导入成功的文件，原因见下方列表。");
    }
  }

  /* ---------- 模型配置（BYOK） ---------- */

  function updateLlmState() {
    if (!dom.llmState) return;
    let label = "未配置";
    if (state.llm && state.llm.has_key) label = "已接入";
    else if (state.llm) label = "需填 Key";
    else if (state.envLlm) label = "默认模型";
    dom.llmState.textContent = label;
    dom.llmState.dataset.state = label === "未配置" ? "off" : "on";
  }

  async function loadProviders() {
    try {
      const data = await api("/api/llm/providers");
      state.providers = (data && data.providers) || [];
    } catch (error) {
      state.providers = [];
    }
    const select = document.getElementById("llm-provider");
    if (!select) return;
    select.innerHTML = state.providers
      .map((provider) => '<option value="' + esc(provider.id) + '">' + esc(provider.label) + "</option>")
      .join("");
    syncProvider(true);
  }

  function currentProvider() {
    const select = document.getElementById("llm-provider");
    const id = select ? select.value : "";
    return state.providers.find((provider) => provider.id === id) || null;
  }

  function syncProvider(fillDefaults) {
    const provider = currentProvider();
    const base = document.getElementById("llm-base");
    const model = document.getElementById("llm-model");
    const models = document.getElementById("llm-models");
    const note = document.getElementById("llm-provider-note");
    if (!provider) return;
    if (fillDefaults) {
      if (base && provider.base_url) base.value = provider.base_url;
      if (model) model.value = provider.models && provider.models[0] ? provider.models[0] : "";
    }
    if (models) {
      models.innerHTML = (provider.models || [])
        .map((item) => '<option value="' + esc(item) + '"></option>')
        .join("");
    }
    if (note) note.textContent = provider.note || "";
  }

  async function loadLlmSettings() {
    if (!state.user) {
      state.llm = null;
      updateLlmState();
      renderLlmForm();
      return;
    }
    try {
      state.llm = await api("/api/llm");
    } catch (error) {
      state.llm = null;
    }
    updateLlmState();
    renderLlmForm();
  }

  function renderLlmForm() {
    const saved = document.getElementById("llm-saved");
    const loginNote = document.getElementById("llm-login-note");
    const key = document.getElementById("llm-key");
    if (loginNote) loginNote.hidden = !!state.user;
    if (saved) {
      saved.hidden = !state.llm;
      saved.textContent =
        state.llm && state.llm.provider
          ? "已保存：" + state.llm.provider + " · " + state.llm.model +
            (state.llm.has_key ? "（Key " + state.llm.key_hint + "）" : "（未设置 Key）")
          : "";
    }
    if (key) {
      key.disabled = !state.user;
      key.value = "";
    }
    if (state.llm) {
      const select = document.getElementById("llm-provider");
      const base = document.getElementById("llm-base");
      const model = document.getElementById("llm-model");
      if (select && state.llm.provider) select.value = state.llm.provider;
      if (base) base.value = state.llm.base_url || "";
      if (model) model.value = state.llm.model || "";
      syncProvider(false);
    }
  }

  function openLlmDialog() {
    renderLlmForm();
    showLlmStatus("");
    openDialog("llm-dialog");
  }

  function bindLlm() {
    on("llm-provider", "change", () => syncProvider(true));
    on("llm-form", "submit", saveLlm);
    on("llm-test", "click", testLlm);
    on("llm-clear", "click", clearLlm);
  }

  function llmPayload() {
    const provider = document.getElementById("llm-provider");
    const base = document.getElementById("llm-base");
    const model = document.getElementById("llm-model");
    const key = document.getElementById("llm-key");
    return {
      provider: provider ? provider.value : "",
      base_url: base ? base.value.trim() : "",
      model: model ? model.value.trim() : "",
      api_key: key ? key.value.trim() : "",
    };
  }

  async function saveLlm(event) {
    event.preventDefault();
    if (!state.user) {
      openAuth("login");
      showLlmError("请先登录，Key 才能加密保存到账号。");
      return;
    }
    const payload = llmPayload();
    if (!payload.provider || !payload.model) {
      showLlmError("请选择厂商并填写模型名称。");
      return;
    }
    showLlmError("");
    const save = document.getElementById("llm-save");
    if (save) {
      save.disabled = true;
      save.innerHTML = spinner() + "保存中…";
    }
    try {
      state.llm = await api("/api/llm", jsonBody(payload));
      const key = document.getElementById("llm-key");
      if (key) key.value = "";
      updateLlmState();
      renderLlmForm();
      showLlmStatus("已保存。下次审查会用这个模型做抽取与解释。");
    } catch (error) {
      showLlmError(error.message || "保存失败，请重试。");
    } finally {
      if (save) {
        save.disabled = false;
        save.textContent = "保存";
      }
    }
  }

  async function testLlm() {
    if (!state.user) {
      openAuth("login");
      showLlmError("请先登录再测试。");
      return;
    }
    const payload = llmPayload();
    if (!payload.provider || !payload.model) {
      showLlmError("请选择厂商并填写模型名称。");
      return;
    }
    const button = document.getElementById("llm-test");
    if (button) {
      button.disabled = true;
      button.innerHTML = spinner() + "测试中…";
    }
    showLlmError("");
    try {
      const result = await api("/api/llm/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showLlmStatus(
        (result && result.ok ? "连接成功：" : "连接失败：") +
          (result && result.detail ? result.detail : ""),
        !(result && result.ok),
      );
    } catch (error) {
      showLlmStatus("连接失败：" + (error.message || "请检查地址与 Key。"), true);
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "测试连通性";
      }
    }
  }

  async function clearLlm() {
    if (!state.user) return;
    try {
      await api("/api/llm", { method: "DELETE" });
      state.llm = null;
      updateLlmState();
      renderLlmForm();
      showLlmStatus("已清除保存的模型配置。");
    } catch (error) {
      showLlmError(error.message || "清除失败，请重试。");
    }
  }

  function showLlmError(text) {
    const box = document.getElementById("llm-error");
    if (!box) return;
    box.textContent = text;
    box.hidden = !text;
  }

  function showLlmStatus(text, isError) {
    const box = document.getElementById("llm-status");
    if (!box) return;
    box.textContent = text;
    box.hidden = !text;
    box.classList.toggle("is-error", !!isError);
  }

  /* ---------- 审查历史（侧栏子目录：改名 / 置顶 / 删除） ---------- */

  function bindHistory() {
    const toggle = document.getElementById("open-history");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const sub = document.getElementById("history-sub");
        if (!sub) return;
        const open = sub.hidden;
        sub.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        if (open) loadHistory();
      });
    }
    on("history-list", "click", onHistoryClick);
    on("history-list", "submit", onHistoryRename);
  }

  function historySubOpen() {
    const sub = document.getElementById("history-sub");
    return !!sub && !sub.hidden;
  }

  function setHistoryError(text) {
    const box = document.getElementById("history-error");
    if (!box) return;
    box.textContent = text || "";
    box.hidden = !text;
  }

  async function loadHistory() {
    const list = document.getElementById("history-list");
    const hint = document.getElementById("history-hint");
    setHistoryError("");
    if (!state.user) {
      state.history = [];
      if (hint) {
        hint.textContent = "登录后可以查看过往审查记录。";
        hint.hidden = false;
      }
      if (list) list.innerHTML = "";
      setBadge(0);
      return;
    }
    if (hint) hint.hidden = true;
    if (list) list.innerHTML = '<li class="skill-empty">正在读取…</li>';
    try {
      const data = await api("/api/reviews?limit=20");
      state.history = (data && data.reviews) || [];
      renderHistory();
      setBadge(latestRedCount());
    } catch (error) {
      if (list) list.innerHTML = "";
      setHistoryError(error.message || "读取记录失败。");
    }
  }

  function latestRedCount() {
    const first = state.history[0];
    return first ? Math.max(0, first.reds || 0) : 0;
  }

  function recordTitle(item) {
    return item.title || item.source_filename;
  }

  function recordMeta(item) {
    const meta = [STATUS_LABEL[item.status] || item.status];
    if (item.reds) meta.push(item.reds + " 处高风险");
    if (item.yellows) meta.push(item.yellows + " 处需关注");
    return meta.join(" · ");
  }

  function renderHistory() {
    const list = document.getElementById("history-list");
    if (!list) return;
    if (!state.history.length) {
      list.innerHTML = '<li class="skill-empty">还没有记录，先上传一份合同吧。</li>';
      return;
    }
    list.innerHTML = state.history
      .map((item) => {
        const id = esc(item.review_id);
        return (
          '<li class="rec-item" data-review-id="' +
          id +
          '">' +
          '<div class="rec-row">' +
          '<a class="rec-link" href="#/review/' +
          encodeURIComponent(item.review_id) +
          '">' +
          '<span class="rec-title">' +
          (item.pinned ? '<span class="rec-pin" aria-hidden="true">置顶</span>' : "") +
          esc(recordTitle(item)) +
          "</span>" +
          '<span class="rec-meta">' +
          esc(recordMeta(item)) +
          "</span>" +
          "</a>" +
          '<div class="rec-tools">' +
          '<button class="rec-tool" type="button" data-pin title="' +
          (item.pinned ? "取消置顶" : "置顶") +
          '">' +
          (item.pinned ? "↓" : "↑") +
          "</button>" +
          '<button class="rec-tool" type="button" data-rename title="重命名">✎</button>' +
          '<button class="rec-tool" type="button" data-delete title="删除">×</button>' +
          "</div>" +
          "</div>" +
          '<form class="rec-rename" hidden>' +
          '<input type="text" maxlength="60" placeholder="' +
          esc(item.source_filename) +
          '" value="' +
          esc(item.title || "") +
          '" aria-label="审查记录标签名" />' +
          '<button class="chip" type="submit">保存</button>' +
          '<button class="chip chip-quiet" type="button" data-cancel>取消</button>' +
          "</form>" +
          '<span class="rec-time">' +
          esc(formatTime(item.created_at)) +
          "</span>" +
          "</li>"
        );
      })
      .join("");
  }

  function recordOf(reviewId) {
    return state.history.find((item) => item.review_id === reviewId) || null;
  }

  function replaceRecord(updated) {
    state.history = state.history.map((item) =>
      item.review_id === updated.review_id ? updated : item,
    );
    renderHistory();
  }

  async function onHistoryClick(event) {
    const row = event.target.closest("[data-review-id]");
    if (!row) return;
    const reviewId = row.dataset.reviewId;

    const cancel = event.target.closest("[data-cancel]");
    if (cancel) {
      const form = row.querySelector(".rec-rename");
      if (form) form.hidden = true;
      return;
    }

    const rename = event.target.closest("[data-rename]");
    if (rename) {
      const form = row.querySelector(".rec-rename");
      if (!form) return;
      form.hidden = !form.hidden;
      if (!form.hidden) {
        const input = form.querySelector("input");
        if (input) input.focus();
      }
      return;
    }

    const pin = event.target.closest("[data-pin]");
    if (pin) {
      const item = recordOf(reviewId);
      if (!item) return;
      pin.disabled = true;
      try {
        const updated = await api("/api/reviews/" + encodeURIComponent(reviewId), {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pinned: !item.pinned }),
        });
        replaceRecord(updated);
      } catch (error) {
        setHistoryError(error.message || "操作失败，请重试。");
        pin.disabled = false;
      }
      return;
    }

    const remove = event.target.closest("[data-delete]");
    if (remove) {
      const item = recordOf(reviewId);
      const label = item ? recordTitle(item) : reviewId;
      if (!window.confirm("删除审查记录“" + label + "”？删除后无法恢复。")) return;
      remove.disabled = true;
      try {
        await api("/api/reviews/" + encodeURIComponent(reviewId), { method: "DELETE" });
        state.history = state.history.filter((entry) => entry.review_id !== reviewId);
        renderHistory();
        if (state.reviewId === reviewId) {
          state.reviewId = null;
          location.hash = "#/";
        }
      } catch (error) {
        setHistoryError(error.message || "删除失败，请重试。");
        remove.disabled = false;
      }
    }
  }

  async function onHistoryRename(event) {
    const form = event.target.closest(".rec-rename");
    if (!form) return;
    event.preventDefault();
    const row = form.closest("[data-review-id]");
    if (!row) return;
    const input = form.querySelector("input");
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    try {
      const updated = await api("/api/reviews/" + encodeURIComponent(row.dataset.reviewId), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: input ? input.value.trim() : "" }),
      });
      replaceRecord(updated);
    } catch (error) {
      setHistoryError(error.message || "保存失败，请重试。");
      if (button) button.disabled = false;
    }
  }

  /* ---------- 隐私条款 / 使用政策 ---------- */

  const LEGAL = {
    privacy: {
      title: "隐私条款",
      updated: "2026-10-27",
      sections: [
        [
          "我们收集什么",
          "注册时收集邮箱、昵称与口令（只保存加盐哈希，不保存明文）；使用时保存你上传的合同文件、审查结论、审查重点、Skill 与模型配置。",
        ],
        [
          "文件存在哪里",
          "合同与报告保存在部署这台服务器的本地目录（默认 .data/uploads 与 .data/pending），不会上传到本项目以外的存储。",
        ],
        [
          "第三方模型",
          "如果你在“API 配置”里接入自己的大模型厂商，合同文本与相关条款片段会发送到该厂商的接口，用于要素抽取与风险解释；请先确认该厂商的数据政策。未配置时使用部署方设置的默认模型。",
        ],
        [
          "不使用你的合同训练模型",
          "本项目不训练模型，也不会把你的合同用于训练或对外共享。",
        ],
        [
          "谁能看到你的审查",
          "登录后上传的审查与账号绑定，只有该账号（凭会话 Cookie）能读取；未登录的审查凭不可猜测的审查编号读取。",
        ],
        [
          "保存期限与删除",
          "审查记录随账号保留，直至你或部署方删除；当前版本未提供自助注销账号，如需删除请联系部署方管理员。",
        ],
        [
          "安全边界",
          "会话 Cookie 为 HttpOnly；模型 API Key 以本机密文保存（删除 .data/secret.key 会让已保存的 Key 失效）。请不要上传与审查无关的个人敏感信息。",
        ],
      ],
    },
    terms: {
      title: "使用政策",
      updated: "2026-10-27",
      sections: [
        [
          "服务定位",
          "本工具是合同预审辅助，输出不是法律意见，也不构成对合同效力、合法性或可签署性的结论；签署前请由专业律师复核。",
        ],
        [
          "规则覆盖有限",
          "只覆盖常见条款类型（付款、交付、检验、贸易术语、争议解决等）。没有命中规则不代表没有风险，报告中的“未发现风险点”不等于“没有风险”。",
        ],
        [
          "高风险必须人工确认",
          "红色风险会暂停并等待人工确认；确认只表示“已经看过”，不会改变风险等级。确认超时或未确认的报告不能当作通过结论。",
        ],
        [
          "账号与操作",
          "请妥善保管口令；通过你账号提交的上传与人工决定视为你本人操作。发现异常请立即退出登录并更换口令。",
        ],
        [
          "上传内容",
          "你应确保对上传文件拥有合法使用权；请勿上传违法内容，或在未获授权的情况下上传他人商业秘密。",
        ],
        [
          "模型输出可能出错",
          "模型只做要素抽取与解释，可能出错；以规则结果与合同原文为准，页面提供原文引用便于核对。",
        ],
        [
          "可用性",
          "演示与自部署环境不承诺服务等级；维护或重启可能让进行中的审查需要重新提交。",
        ],
        [
          "政策变更",
          "政策更新会在本页面更新日期；继续使用视为接受更新后的条款。",
        ],
      ],
    },
  };

  function openLegal(kind) {
    const doc = LEGAL[kind] || LEGAL.privacy;
    const title = document.getElementById("legal-title");
    const body = document.getElementById("legal-body");
    if (title) title.textContent = doc.title;
    if (body) {
      body.innerHTML =
        '<p class="legal-lead">' +
        esc(doc.title) +
        " · 更新日期 " +
        esc(doc.updated) +
        " · 适用于本页面的全部审查功能</p>" +
        doc.sections
          .map(
            ([heading, text], index) =>
              '<section class="legal-section"><h3><span class="legal-no">' +
              String(index + 1).padStart(2, "0") +
              "</span>" +
              esc(heading) +
              "</h3><p>" +
              esc(text) +
              "</p></section>",
          )
          .join("");
    }
    openDialog("legal-dialog");
  }

  function bindLegal() {
    on("open-privacy", "click", () => openLegal("privacy"));
    on("open-terms", "click", () => openLegal("terms"));
  }

  /* ---------- 上传页 ---------- */

  /** 登录态变化后刷新首屏；已经选了文件/正在上传时不动，避免打断操作 */
  function renderUploadIfIdle() {
    if (state.file || state.busy) return;
    if ((location.hash || "#/") !== "#/") return;
    renderUpload();
  }

  function chatTitle() {
    const user = state.user;
    const name = user ? user.display_name || (user.email || "").split("@")[0] : "";
    return name ? "欢迎回来，" + name : "今天想审查哪份合同？";
  }

  function renderUpload() {
    state.file = null;
    state.busy = false;
    dom.view.innerHTML =
      '<section class="chat">' +
      '<div class="chat-hero">' +
      '<span class="chat-mark" aria-hidden="true">' +
      '<svg viewBox="0 0 24 24" width="18" height="18">' +
      '<path d="M6 18 12 5l6 13M8.5 14h7" fill="none" stroke="currentColor" ' +
      'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      "</span>" +
      '<h1 class="chat-title">' +
      esc(chatTitle()) +
      "</h1>" +
      "</div>" +
      '<div class="composer-box" id="drop">' +
      '<input id="file-input" type="file" accept=".pdf,.docx,.txt,.md" hidden />' +
      '<label class="sr-only" for="focus-input">审查重点</label>' +
      '<textarea class="composer-text" id="focus-input" rows="2" maxlength="800" ' +
      'placeholder="说明这次最想盯住什么，例如：重点看预付款比例与交付期限"></textarea>' +
      '<div class="composer-tools">' +
      '<button class="tool" type="button" id="attach-button" aria-label="添加合同文件">' +
      '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">' +
      '<path d="M15.5 8.5 9 15a2.5 2.5 0 0 0 3.5 3.5l7-7a4.5 4.5 0 0 0-6.5-6.5l-7 7a6.5 6.5 0 0 0 9 9" ' +
      'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>' +
      "<span>合同</span></button>" +
      '<span class="tool-file" id="attach-file">未添加文件</span>' +
      '<button class="tool-clear" type="button" id="clear-attach" aria-label="移除已选文件" hidden>×</button>' +
      '<div class="skill-picker">' +
      '<button class="tool-skill" type="button" id="skill-select" aria-haspopup="listbox" ' +
      'aria-expanded="false" aria-controls="skill-menu">' +
      '<span class="tool-skill-key">Skill</span>' +
      '<span class="tool-skill-name" id="skill-current">全量体检</span>' +
      '<svg class="tool-caret" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">' +
      '<path d="m6 9 6 6 6-6"/></svg>' +
      "</button>" +
      '<ul class="skill-menu" id="skill-menu" role="listbox" aria-label="选择 Skill" hidden></ul>' +
      "</div>" +
      '<button class="send" type="button" id="start" aria-label="开始审查" title="开始审查" disabled>' +
      '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
      '<path d="M12 19V6m0 0-5 5m5-5 5 5" fill="none" stroke="currentColor" stroke-width="1.8" ' +
      'stroke-linecap="round" stroke-linejoin="round"/></svg></button>' +
      "</div>" +
      "</div>" +
      '<p class="alert chat-error" id="form-error" role="alert" hidden></p>' +
      "</section>";

    const input = dom.view.querySelector("#file-input");
    const drop = document.getElementById("drop");
    const focus = document.getElementById("focus-input");

    if (focus) {
      focus.addEventListener("input", () => {
        state.focus = focus.value.slice(0, 800);
      });
      focus.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.shiftKey) return;
        event.preventDefault();
        if (!state.file) {
          showFormError("先添加合同文件，再发送审查指令。");
          return;
        }
        startReview();
      });
    }

    renderSkillSelect();
    // 偏好“自动聚焦输入框”：只在不打扰弹窗/已有焦点时聚焦
    if (prefs.autofocus && focus && !document.querySelector("dialog[open]")) {
      focus.focus({ preventScroll: true });
    }
    const trigger = document.getElementById("skill-select");
    const menu = document.getElementById("skill-menu");
    if (trigger) trigger.addEventListener("click", toggleSkillMenu);
    if (menu) {
      menu.addEventListener("click", (event) => {
        const option = event.target.closest("[data-skill]");
        if (option) onSkillSelectChange(option.dataset.skill);
      });
      menu.addEventListener("keydown", (event) => {
        const options = Array.from(menu.querySelectorAll("[data-skill]"));
        const index = options.indexOf(document.activeElement);
        if (event.key === "Escape") {
          event.preventDefault();
          closeSkillMenu();
          if (trigger) trigger.focus();
          return;
        }
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
        if (!options.length) return;
        event.preventDefault();
        const step = event.key === "ArrowDown" ? 1 : -1;
        const next = options[(index + step + options.length) % options.length];
        if (next) next.focus();
      });
    }

    on("attach-button", "click", () => dom.view.querySelector("#file-input")?.click());
    on("clear-attach", "click", clearAttachment);
    on("start", "click", startReview);

    if (input) {
      input.addEventListener("change", () => {
        if (input.files && input.files[0]) accept(input.files[0]);
      });
    }

    if (drop) {
      ["dragenter", "dragover"].forEach((type) =>
        drop.addEventListener(type, (event) => {
          event.preventDefault();
          drop.classList.add("is-over");
        }),
      );
      ["dragleave", "dragend", "drop"].forEach((type) =>
        drop.addEventListener(type, () => drop.classList.remove("is-over")),
      );
      drop.addEventListener("drop", (event) => {
        event.preventDefault();
        const file = event.dataTransfer && event.dataTransfer.files[0];
        if (file) accept(file);
      });
    }

    renderSkillSelect();
  }

  function accept(file) {
    const suffix = suffixOf(file.name);
    if (!ALLOWED.includes(suffix)) {
      showFormError("只支持 PDF、Word（.docx）、TXT 或 Markdown 文件。");
      return;
    }
    if (file.size > MAX_BYTES) {
      showFormError("文件超过 15 MB，请压缩或拆分后再上传。");
      return;
    }
    if (file.size === 0) {
      showFormError("这个文件是空的，请换一份。");
      return;
    }
    const error = document.getElementById("form-error");
    if (error) error.hidden = true;
    state.file = file;

    const label = document.getElementById("attach-file");
    if (label) {
      label.textContent = file.name + " · " + humanSize(file.size);
      label.classList.add("is-set");
    }
    const clear = document.getElementById("clear-attach");
    if (clear) clear.hidden = false;
    const start = document.getElementById("start");
    if (start) start.disabled = false;
  }

  function clearAttachment() {
    state.file = null;
    const input = dom.view.querySelector("#file-input");
    if (input) input.value = "";
    const label = document.getElementById("attach-file");
    if (label) {
      label.textContent = "未添加文件";
      label.classList.remove("is-set");
    }
    const clear = document.getElementById("clear-attach");
    if (clear) clear.hidden = true;
    const start = document.getElementById("start");
    if (start) start.disabled = true;
    const error = document.getElementById("form-error");
    if (error) error.hidden = true;
  }

  function showFormError(text) {
    const error = document.getElementById("form-error");
    if (!error) return;
    error.textContent = text;
    error.hidden = false;
  }

  async function startReview() {
    if (!state.file || state.busy) return;
    const start = document.getElementById("start");
    const box = document.getElementById("drop");
    const focus = document.getElementById("focus-input");
    state.focus = focus ? focus.value.slice(0, 800) : state.focus;
    state.busy = true;
    if (start) {
      start.disabled = true;
      start.innerHTML = spinner();
      start.classList.add("is-busy");
    }
    if (box) box.classList.add("is-dim");

    const form = new FormData();
    form.append("file", state.file, state.file.name);
    form.append("focus", state.focus.trim());
    form.append("skill_id", state.skillId || "");

    try {
      const summary = await api("/api/reviews", { method: "POST", body: form });
      state.reviewId = summary.review_id;
      // 只换 hash 不新增历史记录：刷新 / 分享链接时还能回到这次结果
      history.replaceState(null, "", "#/review/" + summary.review_id);
      setShell("review");
      renderResult(summary);
    } catch (error) {
      state.busy = false;
      if (start) {
        start.disabled = false;
        start.classList.remove("is-busy");
        start.innerHTML = sendIcon();
      }
      if (box) box.classList.remove("is-dim");
      showFormError(
        error instanceof TypeError
          ? "服务没有响应，请确认服务已启动后重试。"
          : error.message || "上传失败，请重试。",
      );
    }
  }

  function sendIcon() {
    return (
      '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
      '<path d="M12 19V6m0 0-5 5m5-5 5 5" fill="none" stroke="currentColor" ' +
      'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    );
  }

  /* ---------- 结果页 ---------- */

  function renderNoSession() {
    setBadge(0);
    dom.view.innerHTML =
      '<section class="result">' +
      '<h1 class="headline">还没有审查记录</h1>' +
      '<p class="lead">先上传一份合同；审查结果会自动出现在这里，刷新页面也不会丢。</p>' +
      '<a class="btn btn-primary" href="#/">上传合同</a>' +
      "</section>";
  }

  async function loadReview(reviewId) {
    if (state.busy) return;
    state.busy = true;
    state.reviewId = reviewId;
    dom.view.innerHTML =
      '<section class="result is-loading">' + backLink() + spinner() + "</section>";
    try {
      const summary = await api("/api/reviews/" + encodeURIComponent(reviewId));
      renderResult(summary);
    } catch (error) {
      failMessage(error.message || "读取审查结果失败。");
    } finally {
      state.busy = false;
    }
  }

  async function renderResult(review) {
    state.busy = false;
    state.reviewId = review.review_id;
    state.reviewStatus = review.status || "";
    // 待人工确认 / 运行中都算“任务没结束”，退出登录需要二次确认
    state.taskActive = review.status === "awaiting_human" || review.status === "running";

    if (review.status === "failed") {
      state.taskActive = false;
      setBadge(0);
      failMessage(
        (review.errors && review.errors.join("；")) ||
          "合同没能被读取，请确认文件是文本型 PDF / Word / TXT。",
      );
      return;
    }
    if (review.status === "not_contract") {
      state.taskActive = false;
      setBadge(0);
      renderNotContract(review);
      return;
    }

    const report = review.report;
    const findings = (report && report.findings) || [];
    const reds = findings.filter((item) => item.risk_level === "red").length;
    if (review.awaiting_human && review.approval) {
      const total =
        typeof review.approval.findings_total === "number"
          ? review.approval.findings_total
          : (review.approval.findings || []).length;
      setBadge(total);
    } else if (findings.length) {
      setBadge(reds);
    } else {
      setBadge(0);
    }
    await renderReviewWorkspace(review);
  }

  /* ---------- 审查结果：对话式流式输出 + 左右分屏逐条审查 ---------- */

  /** 把已有结果整理成“助手说的话”；等页面跑过一次就逐句吐出来（内容都是真实数据）。 */
  function chatNarrative(review, view) {
    const lines = ["已读取《" + review.source_filename + "》，判定为国际货物销售合同，开始审查。"];
    if (review.focus) lines.push("审查重点：" + review.focus + "。");
    if (view && view.clauses.length) {
      const red = view.clauses.filter((item) => item.risk_level === "red").length;
      const yellow = view.clauses.filter((item) => item.risk_level === "yellow").length;
      const pass = view.clauses.filter((item) => item.risk_level === "pass").length;
      lines.push(
        "已按标题与段落切分为 " +
          view.clauses.length +
          " 条条款：规则在其中命中 " +
          red +
          " 条高风险、" +
          yellow +
          " 条需关注，" +
          pass +
          " 条未见规则命中。",
      );
      if (view.contract_findings.length) {
        lines.push(
          "另有 " +
            view.contract_findings.length +
            " 处问题不指向具体条款（例如缺失的适用法律），已单独归类为“全合同”。",
        );
      }
    } else {
      lines.push("条款视图暂时读取失败，下面只展示风险清单。");
    }
    if (review.awaiting_human) {
      lines.push("红色风险需要你确认后才会生成正式报告；右侧可以先逐条查看意见与示例条款。");
    } else if (review.status === "rejected" || review.status === "changes_requested") {
      lines.push("你已标记这份合同需要修改，可以按右侧建议逐条更正后再导出一份修订稿。");
    } else {
      lines.push("下面按“左原文、右意见”逐条展开；点“一键更正”即采用示例条款，可随时撤销。");
    }
    lines.push("风险等级只由规则判定，修改建议不构成法律意见。");
    return lines;
  }

  function stopStream() {
    if (state.streamTimer) {
      clearInterval(state.streamTimer);
      state.streamTimer = 0;
    }
  }

  /** 逐段输出：内容来自真实审查结果，只是把一次性结果按句显示；减少动效时直接整段出现。 */
  function streamText(lines, done) {
    const target = document.getElementById("ai-stream");
    if (!target) {
      done();
      return;
    }
    stopStream();
    const full = lines.join("\n");
    if (prefs.motion) {
      target.textContent = full;
      done();
      return;
    }
    let index = 0;
    state.streamTimer = setInterval(() => {
      if (!document.body.contains(target)) {
        stopStream();
        return;
      }
      index += 3;
      target.textContent = full.slice(0, index);
      if (index >= full.length) {
        stopStream();
        done();
      }
    }, 18);
  }

  function statusChip(review) {
    const label = STATUS_LABEL[review.status] || review.status || "";
    return label ? '<span class="status-chip">' + esc(label) + "</span>" : "";
  }

  async function renderReviewWorkspace(review) {
    state.clauseView = null;
    state.corrections = {};
    state.selectedClause = "";
    stopStream();

    let view = null;
    try {
      view = await api(
        "/api/reviews/" + encodeURIComponent(review.review_id) + "/clauses",
      );
    } catch (error) {
      view = null;
    }
    state.clauseView = view;
    if (view && view.clauses.length) {
      const first = view.clauses.find((item) => item.risk_level !== "pass") || view.clauses[0];
      state.selectedClause = first.clause_id;
    } else if (view && view.contract_findings.length) {
      state.selectedClause = "__contract__";
    }

    const userLine = [
      "合同：" + review.source_filename,
      review.focus ? "审查重点：" + review.focus : "",
      review.skill_name ? "Skill：" + review.skill_name : "",
    ]
      .filter(Boolean)
      .map(esc)
      .join("<br>");

    const parts = [
      '<section class="review-shell">',
      '<div class="review-head">',
      backLink(),
      '<div class="review-head-main">',
      '<p class="file-line">' + esc(review.source_filename) + statusChip(review) + "</p>",
      "</div>",
      "</div>",
      '<div class="chat-thread" id="chat-thread">',
      '<div class="msg is-user"><div class="msg-bubble">' + userLine + "</div></div>",
      '<div class="msg is-ai"><div class="msg-bubble"><span id="ai-stream"></span>' +
        '<span class="stream-caret" aria-hidden="true"></span></div></div>',
      '<div id="approval-slot"></div>',
      "</div>",
    ];

    if (view) {
      const revised = view.revised_count || 0;
      parts.push(
        '<div class="workbench" id="workbench" hidden>',
        '<div class="workbench-bar">',
        '<div class="workbench-title">逐条审查',
        '<span class="workbench-meta" id="clause-meta"></span>',
        "</div>",
        '<div class="workbench-actions">',
        revised
          ? '<button class="btn btn-compact" type="button" data-apply-all>全部更正</button>'
          : "",
        '<span class="export-label">导出修订稿</span>',
        '<button class="btn btn-compact" type="button" data-export="docx">DOCX</button>',
        '<button class="btn btn-compact" type="button" data-export="pdf">PDF</button>',
        "</div>",
        "</div>",
        '<div class="workbench-grid">',
        '<ol class="clause-list" id="clause-list" aria-label="合同条款"></ol>',
        '<div class="clause-detail" id="clause-detail"></div>',
        "</div>",
        '<p class="alert" id="export-error" role="alert" hidden></p>',
        "</div>",
      );
    } else {
      parts.push(
        '<div class="down">' +
          '<span>下载报告</span>' +
          '<a href="/api/reviews/' +
          encodeURIComponent(review.review_id) +
          '/report?format=markdown">Markdown</a>' +
          "</div>",
      );
    }
    parts.push("</section>");
    dom.view.innerHTML = parts.join("");

    // 待确认面板跟着“助手说完”再出现，顺序像对话（先说结论，再让你确认）
    const approvalHtml =
      review.awaiting_human && review.approval ? renderApproval(review) : "";
    const showApproval = () => {
      if (!approvalHtml) return;
      const slot = document.getElementById("approval-slot");
      if (!slot) return;
      slot.innerHTML = approvalHtml;
      bindConfirm();
    };

    if (!view) {
      const stream = document.getElementById("ai-stream");
      if (stream) stream.textContent = chatNarrative(review, view).join("\n");
      showApproval();
      return;
    }

    streamText(chatNarrative(review, view), () => {
      showApproval();
      const box = document.getElementById("workbench");
      if (box) {
        box.hidden = false;
        // 分屏是这一屏的重点；若被上面的对话挤出可视区，就把它带到视口顶部
        const rect = box.getBoundingClientRect();
        if (rect.top > window.innerHeight - 120) {
          box.scrollIntoView({ block: "start", behavior: prefs.motion ? "auto" : "smooth" });
        }
      }
      renderWorkbench();
    });
  }

  function clauseLevelLabel(level) {
    if (level === "red") return "高风险";
    if (level === "yellow") return "需关注";
    return "未见问题";
  }

  function renderWorkbench() {
    const view = state.clauseView;
    if (!view) return;
    const applied = Object.keys(state.corrections).length;
    const meta = document.getElementById("clause-meta");
    if (meta) {
      meta.textContent =
        "共 " + view.clauses.length + " 条 · 已更正 " + applied + " 条";
    }
    const list = document.getElementById("clause-list");
    if (list) {
      const items = [];
      if (view.contract_findings.length) {
        // “全合同”分组的颜色取组内最严重的等级（规则判定，不在这里重判）
        const contractLevel = view.contract_findings.some(
          (item) => item.risk_level === "red",
        )
          ? "red"
          : "yellow";
        items.push(
          '<li class="clause-item clause-global' +
            (state.selectedClause === "__contract__" ? " is-active" : "") +
            '"><button class="clause-jump" type="button" data-clause="__contract__">' +
            '<span class="clause-index">※</span>' +
            '<span class="clause-name">全合同</span>' +
            '<span class="clause-flag is-' +
            contractLevel +
            '">' +
            view.contract_findings.length +
            " 处</span>" +
            "</button></li>",
        );
      }
      view.clauses.forEach((clause) => {
        const flag =
          clause.risk_level === "pass"
            ? '<span class="clause-dot is-pass" aria-label="未见问题"></span>'
            : '<span class="clause-flag is-' +
              clause.risk_level +
              '">' +
              clauseLevelLabel(clause.risk_level) +
              "</span>";
        items.push(
          '<li class="clause-item' +
            (state.selectedClause === clause.clause_id ? " is-active" : "") +
            '"><button class="clause-jump" type="button" data-clause="' +
            esc(clause.clause_id) +
            '">' +
            '<span class="clause-index">' +
            String(clause.index).padStart(2, "0") +
            "</span>" +
            '<span class="clause-name">' +
            esc(clause.title || "第 " + clause.index + " 条") +
            "</span>" +
            (state.corrections[clause.clause_id]
              ? '<span class="clause-applied" aria-label="已更正">✓</span>'
              : "") +
            flag +
            "</button></li>",
        );
      });
      list.innerHTML = items.join("");
      // 只滚动条款列表自身（不要用 scrollIntoView，否则整页会跟着跳）
      const active = list.querySelector(".clause-item.is-active");
      if (active) {
        const listBox = list.getBoundingClientRect();
        const itemBox = active.getBoundingClientRect();
        const delta = itemBox.top - listBox.top;
        list.scrollTop += delta - (list.clientHeight - itemBox.height) / 2;
      }
    }
    renderClauseDetail();
  }

  function findingBlock(finding) {
    const quotes = finding.quotes || [];
    return [
      '<article class="finding is-' + esc(finding.risk_level) + '">',
      '<div class="finding-head">',
      '<span class="tag">' + esc(clauseLevelLabel(finding.risk_level)) + "</span>",
      '<h4 class="finding-title">' + esc(finding.title || finding.reason) + "</h4>",
      "</div>",
      '<p class="finding-reason">' + esc(finding.reason) + "</p>",
      finding.explanation_summary && finding.explanation_summary !== finding.reason
        ? '<p class="finding-note">' + esc(finding.explanation_summary) + "</p>"
        : "",
      finding.suggestion
        ? '<p class="finding-fix"><span>建议</span>' + esc(finding.suggestion) + "</p>"
        : "",
      '<details class="why"><summary>原文依据与规则</summary>',
      quotes.map((quote) => "<blockquote>" + esc(quote) + "</blockquote>").join(""),
      finding.explanation_citation
        ? '<p class="cite">位置：' + esc(finding.explanation_citation) + "</p>"
        : "",
      (finding.knowledge_citations || []).length
        ? '<p class="cite">知识引用：' +
          esc(finding.knowledge_citations.join("、")) +
          "</p>"
        : "",
      '<p class="cite">规则编号：' + esc(finding.rule_id) + "</p>",
      "</details>",
      "</article>",
    ].join("");
  }

  function renderClauseDetail() {
    const view = state.clauseView;
    const box = document.getElementById("clause-detail");
    if (!view || !box) return;

    if (state.selectedClause === "__contract__") {
      box.innerHTML = [
        '<div class="detail-head">',
        '<h3 class="detail-title">全合同问题</h3>',
        '<p class="detail-meta">这些规则不指向具体条款（例如缺失的适用法律），需要新增一段。</p>',
        "</div>",
        view.contract_findings.map(findingBlock).join(""),
        view.contract_revised_text
          ? '<div class="revision"><div class="revision-head"><span>建议新增条款</span>' +
            '<span class="revision-note">' +
            esc(view.contract_revision_note || "") +
            "</span></div>" +
            '<pre class="revision-text">' +
            esc(view.contract_revised_text) +
            "</pre></div>"
          : "",
      ].join("");
      return;
    }

    const clause = view.clauses.find((item) => item.clause_id === state.selectedClause);
    if (!clause) {
      box.innerHTML = '<p class="detail-empty">从左侧选择一条条款查看审查意见。</p>';
      return;
    }
    const corrected = state.corrections[clause.clause_id];
    const draft = corrected || clause.revised_text || "";
    const parts = [
      '<div class="detail-head">',
      "<div>",
      '<h3 class="detail-title">' +
        esc(clause.title || "第 " + clause.index + " 条") +
        "</h3>",
      '<p class="detail-meta">第 ' +
        clause.index +
        " 条 · 第 " +
        clause.page +
        " 页 · " +
        clauseLevelLabel(clause.risk_level) +
        (corrected ? " · 已更正" : "") +
        "</p>",
      "</div>",
      "</div>",
      '<h4 class="detail-sub">合同原文</h4>',
      '<blockquote class="clause-text">' + esc(clause.text) + "</blockquote>",
    ];

    if (clause.findings.length) {
      parts.push('<h4 class="detail-sub">审查意见</h4>');
      clause.findings.forEach((finding) => parts.push(findingBlock(finding)));
    } else {
      parts.push('<p class="detail-empty is-pass">这条没有命中规则，可按原文保留。</p>');
    }

    if (clause.revised_text) {
      parts.push(
        '<div class="revision">',
        '<div class="revision-head"><span>修改后的条款（可编辑）</span>',
        '<span class="revision-note">' + esc(clause.revision_note || "") + "</span></div>",
        '<textarea class="revision-input" id="revised-input" data-clause-input="' +
          esc(clause.clause_id) +
          '" rows="5">' +
          esc(draft) +
          "</textarea>",
        '<div class="revision-actions">',
        '<button class="btn btn-primary btn-compact" type="button" data-apply="' +
          esc(clause.clause_id) +
          '">一键更正</button>',
        '<button class="btn btn-compact" type="button" data-revert="' +
          esc(clause.clause_id) +
          '"' +
          (corrected ? "" : " hidden") +
          '>撤销更正</button>',
        "</div>",
        "</div>",
      );
    } else if (clause.findings.length) {
      parts.push('<p class="detail-empty">这条规则只给文字建议，没有可套用的示例条款。</p>');
    }

    box.innerHTML = parts.join("");
  }

  function showExportError(text) {
    const box = document.getElementById("export-error");
    if (!box) return;
    box.textContent = text || "";
    box.hidden = !text;
  }

  function applyCorrection(clauseId) {
    const input = document.querySelector('[data-clause-input="' + clauseId + '"]');
    const text = input ? input.value.trim() : "";
    if (!text) {
      showExportError("修订文本为空，无法更正。");
      return;
    }
    state.corrections[clauseId] = text;
    showExportError("");
    renderWorkbench();
  }

  function revertCorrection(clauseId) {
    delete state.corrections[clauseId];
    showExportError("");
    renderWorkbench();
  }

  function applyAllCorrections() {
    const view = state.clauseView;
    if (!view) return;
    view.clauses.forEach((clause) => {
      if (clause.revised_text) state.corrections[clause.clause_id] = clause.revised_text;
    });
    showExportError("");
    renderWorkbench();
  }

  function filenameFromDisposition(header, fallback) {
    if (!header) return fallback;
    const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (star) {
      try {
        return decodeURIComponent(star[1].trim());
      } catch (error) {
        /* 回退到普通 filename */
      }
    }
    const plain = /filename="([^"]+)"/i.exec(header);
    return plain ? plain[1] : fallback;
  }

  async function exportRevised(fmt) {
    if (!state.reviewId) return;
    showExportError("");
    const clauses = Object.keys(state.corrections).map((clauseId) => ({
      clause_id: clauseId,
      text: state.corrections[clauseId],
    }));
    try {
      const response = await fetch(
        "/api/reviews/" + encodeURIComponent(state.reviewId) + "/export",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ format: fmt, clauses: clauses }),
        },
      );
      if (!response.ok) {
        let detail = "导出失败，请重试。";
        try {
          const data = await response.json();
          detail = data.detail || detail;
        } catch (error) {
          /* 非 JSON 错误体 */
        }
        throw new Error(detail);
      }
      const blob = await response.blob();
      const fallback = "审查稿." + fmt;
      const name = filenameFromDisposition(
        response.headers.get("Content-Disposition"),
        fallback,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch (error) {
      showExportError(error.message || "导出失败，请重试。");
    }
  }

  /** 逐条审查的交互只绑一次：切条款 / 一键更正 / 撤销 / 全部更正 / 导出。 */
  function bindWorkbenchEvents() {
    dom.view.addEventListener("click", (event) => {
      const jump = event.target.closest("[data-clause]");
      if (jump) {
        state.selectedClause = jump.dataset.clause;
        renderWorkbench();
        return;
      }
      const apply = event.target.closest("[data-apply]");
      if (apply) {
        applyCorrection(apply.dataset.apply);
        return;
      }
      const revert = event.target.closest("[data-revert]");
      if (revert) {
        revertCorrection(revert.dataset.revert);
        return;
      }
      if (event.target.closest("[data-apply-all]")) {
        applyAllCorrections();
        return;
      }
      const exportButton = event.target.closest("[data-export]");
      if (exportButton) exportRevised(exportButton.dataset.export);
    });
  }

  /* 待确认：规则结果已就绪（审批载荷），确认后才生成正式报告与解释。
   * 只返回 HTML，由调用方挂进对话流（#approval-slot）后再 bindConfirm()。 */
  function renderApproval(review) {
    const approval = review.approval || {};
    const findings = approval.findings || [];
    const total =
      typeof approval.findings_total === "number"
        ? approval.findings_total
        : findings.length;
    const truncated = approval.truncated || 0;
    setBadge(total);

    const parts = [
      '<div class="approval">',
      '<h3 class="approval-title">发现 ' + total + " 处高风险，待您确认</h3>",
      '<p class="approval-lead">规则已经定位到以下条款。请先核对；确认后生成完整报告' +
        "（含修改建议与原文依据）。</p>",
      '<ol class="risks">',
    ];
    findings.forEach((finding) => parts.push(approvalCard(finding)));
    parts.push("</ol>");

    if (truncated) {
      parts.push(
        '<p class="fine">另有 ' + truncated + " 条高风险未在此展开，确认后可在报告中查看全部。</p>",
      );
    }

    parts.push(confirmPanel(total), "</div>");
    return parts.join("");
  }

  /* 审批载荷只含规则判定与证据，没有 LLM 解释 */
  function approvalCard(finding) {
    const quotes = finding.quotes || [];
    const citations = finding.citations || [];
    const detail = [
      '<details class="why">',
      "<summary>查看合同原文与依据</summary>",
      quotes.map((quote) => "<blockquote>" + esc(quote) + "</blockquote>").join(""),
      citations.length
        ? '<p class="cite">位置：' + esc(citations.join("、")) + "</p>"
        : "",
      '<p class="cite">规则编号：' + esc(finding.rule_id) + "</p>",
      "</details>",
    ].join("");

    return (
      '<li class="risk is-red">' +
      '<div class="risk-head"><span class="tag">高风险</span></div>' +
      '<h2 class="risk-title">' +
      esc(finding.title || finding.reason) +
      "</h2>" +
      '<p class="risk-explain">' +
      esc(finding.reason) +
      "</p>" +
      (finding.suggestion
        ? '<p class="risk-fix"><span>建议</span>' + esc(finding.suggestion) + "</p>"
        : "") +
      detail +
      "</li>"
    );
  }

  function riskCard(finding) {
    const red = finding.risk_level === "red";
    const tag = red ? "高风险" : "需关注";
    const summary =
      finding.explanation_summary && finding.explanation_summary !== finding.reason
        ? finding.explanation_summary
        : "";
    const quote = finding.explanation_quote || "";
    const where = finding.explanation_citation || (finding.citations || [])[0] || "";
    const knowledge = finding.knowledge_citations || [];

    const detail = [
      '<details class="why">',
      "<summary>查看合同原文与依据</summary>",
      quote ? "<blockquote>" + esc(quote) + "</blockquote>" : "",
      where ? '<p class="cite">位置：' + esc(where) + "</p>" : "",
      knowledge.length ? '<p class="cite">知识引用：' + esc(knowledge.join("、")) + "</p>" : "",
      '<p class="cite">规则编号：' + esc(finding.rule_id) + "</p>",
      "</details>",
    ].join("");

    return (
      '<li class="risk ' +
      (red ? "is-red" : "is-yellow") +
      '">' +
      '<div class="risk-head"><span class="tag">' +
      esc(tag) +
      "</span></div>" +
      '<h2 class="risk-title">' +
      esc(finding.reason) +
      "</h2>" +
      (summary ? '<p class="risk-explain">' + esc(summary) + "</p>" : "") +
      (finding.suggestion
        ? '<p class="risk-fix"><span>建议</span>' + esc(finding.suggestion) + "</p>"
        : "") +
      detail +
      "</li>"
    );
  }

  function confirmPanel(count) {
    return (
      '<div class="confirm">' +
      '<p class="confirm-text">请核对以上 ' +
      count +
      " 处高风险。确认只表示已经人工看过，不会改变风险等级；确认后生成报告。" +
      "</p>" +
      '<label class="confirm-field">复核人（可留空）' +
      '<input id="reviewer" type="text" maxlength="40" placeholder="例如：张三" autocomplete="off" />' +
      "</label>" +
      '<p class="alert" id="confirm-error" role="alert" hidden></p>' +
      '<button class="btn btn-primary btn-block" type="button" id="approve">确认这些风险</button>' +
      '<button class="link confirm-reject" type="button" id="reject">不能接受这份合同</button>' +
      '<p class="fine">风险等级由规则引擎判定，人工确认不会改写等级。</p>' +
      "</div>"
    );
  }

  function bindConfirm() {
    const input = document.getElementById("reviewer");
    if (input) {
      input.addEventListener("input", () => {
        state.reviewer = input.value.trim();
      });
    }
    on("approve", "click", () => decide("approve"));
    on("reject", "click", () => decide("reject"));
  }

  async function decide(action) {
    if (state.busy || !state.reviewId) return;
    state.busy = true;

    const approveButton = document.getElementById("approve");
    const rejectButton = document.getElementById("reject");
    [approveButton, rejectButton].forEach((button) => {
      if (button) button.disabled = true;
    });
    const target = action === "reject" ? rejectButton : approveButton;
    if (target) {
      target.innerHTML = spinner() + (action === "reject" ? "正在记录…" : "正在生成报告…");
    }

    try {
      const summary = await api(
        "/api/reviews/" + encodeURIComponent(state.reviewId) + "/decisions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: action,
            reviewer: state.reviewer || (state.user ? state.user.display_name : "") || "本机用户",
          }),
        },
      );
      renderResult(summary);
    } catch (error) {
      state.busy = false;
      const box = document.getElementById("confirm-error");
      if (box) {
        box.textContent = error.message || "提交失败，请重试。";
        box.hidden = false;
      }
      if (approveButton) {
        approveButton.disabled = false;
        approveButton.textContent = "确认这些风险";
      }
      if (rejectButton) {
        rejectButton.disabled = false;
        rejectButton.textContent = "不能接受这份合同";
      }
    }
  }

  /* ---------- 不是合同 ---------- */

  function renderNotContract(review) {
    const check = review.document_check || {};
    const reasons = check.reasons || [];
    const hints = check.hints || [];
    dom.view.innerHTML =
      '<section class="result">' +
      backLink() +
      '<p class="file-line">' +
      esc(review.source_filename) +
      "</p>" +
      '<h1 class="headline">这份文件不是合同</h1>' +
      '<p class="lead">它更像论文、法规或其他材料，所以没有开始审查，也不会给出风险结论。</p>' +
      (reasons.length
        ? '<ul class="reasons">' +
          reasons.map((item) => "<li>" + esc(item) + "</li>").join("") +
          "</ul>"
        : "") +
      (hints.length ? '<p class="fine">' + hints.map(esc).join(" ") + "</p>" : "") +
      '<a class="btn btn-primary" href="#/">换一份合同</a>' +
      "</section>";
  }

  /* ---------- 启动 ---------- */

  // 跳转链接不能改 hash：hash 路由会把 "#main" 当成首页重新渲染
  document.addEventListener("click", (event) => {
    const skip = event.target.closest && event.target.closest(".skip-link");
    if (!skip) return;
    event.preventDefault();
    if (dom.main) dom.main.focus();
  });

  bindDrawer();
  bindDialogs();
  bindSidebarActions();
  bindAuth();
  bindAccount();
  bindSkills();
  bindWorkbenchEvents();
  bindLlm();
  bindHistory();
  bindLegal();
  checkHealth();
  applyPrefs();
  loadProviders();
  refreshSession();
  window.addEventListener("hashchange", route);
  route();
})();
