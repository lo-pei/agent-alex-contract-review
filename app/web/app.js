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
    accountLine: document.getElementById("account-line"),
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
    const title = { upload: "上传合同", review: "风险点", empty: "当前审查" }[name] || "上传合同";
    if (dom.crumbs) dom.crumbs.textContent = title;
    const active = name === "upload" ? "upload" : "review";
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
    // 需求：Skill 仓库是侧栏入口；输入区不再放“Skill 仓库”按钮
    on("open-skills", "click", openSkills);
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
    if (dom.accountLine) {
      dom.accountLine.hidden = !user;
      if (!user) {
        dom.accountLine.textContent = "";
      } else {
        // 昵称与邮箱分开显示；没填昵称就只显示邮箱（避免 "a@b · a@b" 这种重复）
        const name = user.display_name || "";
        dom.accountLine.title = name && name !== user.email ? name + " · " + user.email : user.email;
        dom.accountLine.innerHTML = name
          ? '<span class="account-name">' +
            esc(name) +
            '</span><span class="account-mail">' +
            esc(user.email) +
            "</span>"
          : '<span class="account-mail">' + esc(user.email) + "</span>";
      }
    }
    if (dom.authLogin) dom.authLogin.hidden = !!user;
    if (dom.authLogout) dom.authLogout.hidden = !user;
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
      dom.authLogout.addEventListener("click", async () => {
        try {
          await api("/api/auth/logout", { method: "POST" });
        } catch (error) {
          /* 退出失败也要把本地状态清掉 */
        }
        state.user = null;
        state.llm = null;
        state.history = [];
        renderAccount();
        updateLlmState();
        renderUploadIfIdle();
        await loadSkills();
        if (historySubOpen()) loadHistory();
        closeDrawer();
      });
    }
    on("auth-form", "submit", submitAuth);
    on("auth-consent-terms", "click", () => openLegal("terms"));
    on("auth-consent-privacy", "click", () => openLegal("privacy"));
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
    // select 只在聊天输入区里存在；结果页不需要（也不应重渲染整页）
    const select = document.getElementById("skill-select");
    if (!select) return;
    // 默认就有几个内置 Skill 可选；最后一项固定为“Skill 仓库”（选中即打开仓库）
    const options = state.skills.map(
      (skill) =>
        '<option value="' +
        esc(skill.id) +
        '">' +
        esc(skill.name) +
        (skill.builtin ? "" : "（我的）") +
        "</option>",
    );
    options.push('<option value="' + SKILL_REPO_VALUE + '">Skill 仓库…</option>');
    select.innerHTML = options.join("");
    if (state.skillId && !skillById(state.skillId)) state.skillId = "";
    if (!state.skillId) state.skillId = defaultSkillId();
    select.value = state.skillId;
  }

  function onSkillSelectChange(select) {
    if (select.value === SKILL_REPO_VALUE) {
      // 仓库是“入口”不是“选项”：打开弹窗，下拉回到当前真实选择
      select.value = state.skillId;
      openSkills();
      return;
    }
    state.skillId = select.value;
  }

  function syncSkillSelectInView() {
    const select = document.getElementById("skill-select");
    if (select) select.value = state.skillId;
  }

  function skillRow(skill) {
    return (
      '<li class="skill-item">' +
      '<div class="skill-main">' +
      '<p class="skill-name">' +
      esc(skill.name) +
      (skill.builtin ? '<span class="skill-tag">推荐</span>' : '<span class="skill-tag">我的</span>') +
      "</p>" +
      '<p class="skill-desc">' +
      esc(skill.description || skill.instruction) +
      "</p>" +
      "</div>" +
      '<div class="skill-actions">' +
      '<button class="chip" type="button" data-use-skill="' +
      esc(skill.id) +
      '">使用</button>' +
      (skill.builtin
        ? ""
        : '<button class="chip chip-quiet" type="button" data-delete-skill="' +
          esc(skill.id) +
          '">删除</button>') +
      "</div>" +
      "</li>"
    );
  }

  function renderSkillList() {
    const builtinBox = document.getElementById("skill-builtin");
    const ownBox = document.getElementById("skill-own");
    if (builtinBox) {
      builtinBox.innerHTML = state.skills.filter((skill) => skill.builtin).map(skillRow).join("");
    }
    if (ownBox) {
      const own = state.skills.filter((skill) => !skill.builtin);
      ownBox.innerHTML = own.length
        ? own.map(skillRow).join("")
        : '<li class="skill-empty">' +
          (state.user ? "还没有自建 Skill，可以在下面写一个。" : "登录后可以创建自己的 Skill。") +
          "</li>";
    }
    const submit = document.getElementById("skill-submit");
    if (submit) submit.disabled = !state.user;
    const note = document.getElementById("skill-login-note");
    if (note) note.hidden = !!state.user;
  }

  function openSkills() {
    renderSkillList();
    openDialog("skills-dialog");
  }

  function bindSkills() {
    on("skills-dialog", "click", async (event) => {
      const useButton = event.target.closest("[data-use-skill]");
      if (useButton) {
        state.skillId = useButton.dataset.useSkill;
        syncSkillSelectInView();
        closeDialog("skills-dialog");
        return;
      }
      const deleteButton = event.target.closest("[data-delete-skill]");
      if (!deleteButton) return;
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
    });
    on("skill-form", "submit", submitSkill);
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
    try {
      const created = await api("/api/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.value.trim(),
          description: description ? description.value.trim() : "",
          instruction: instruction.value.trim(),
        }),
      });
      if (name) name.value = "";
      if (description) description.value = "";
      if (instruction) instruction.value = "";
      state.skillId = created.id;
      await loadSkills();
      renderSkillSelect();
    } catch (error) {
      if (error.status === 401) openAuth("login");
      showSkillError(error.message || "保存失败，请重试。");
    } finally {
      if (submit) {
        submit.disabled = !state.user;
        submit.textContent = "保存 Skill";
      }
    }
  }

  function showSkillError(text) {
    const box = document.getElementById("skill-error");
    if (!box) return;
    box.textContent = text;
    box.hidden = false;
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
      '<label class="sr-only" for="skill-select">选择 Skill</label>' +
      '<select class="tool-select" id="skill-select"></select>' +
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
    const select = document.getElementById("skill-select");

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

    if (select) {
      select.value = state.skillId;
      select.addEventListener("change", () => onSkillSelectChange(select));
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

  function renderResult(review) {
    state.busy = false;
    state.reviewId = review.review_id;

    if (review.status === "failed") {
      setBadge(0);
      failMessage(
        (review.errors && review.errors.join("；")) ||
          "合同没能被读取，请确认文件是文本型 PDF / Word / TXT。",
      );
      return;
    }
    if (review.status === "not_contract") {
      setBadge(0);
      renderNotContract(review);
      return;
    }
    // 红色风险会让流程真暂停：报告还没生成，先展示规则已定位的高风险
    if (review.awaiting_human && review.approval) {
      renderApproval(review);
      return;
    }

    const report = review.report;
    const findings = (report && report.findings) || [];
    const reds = findings.filter((item) => item.risk_level === "red").length;
    const yellows = findings.length - reds;
    setBadge(reds);

    let headline = "没有发现规则覆盖的风险点";
    let sub = "规则只覆盖常见问题，签署前仍建议请专业人士复核。";
    if (findings.length) {
      headline = "发现 " + findings.length + " 处需要关注";
      sub =
        (reds ? reds + " 处高风险" : "") +
        (reds && yellows ? " · " : "") +
        (yellows ? yellows + " 处需关注" : "");
    }

    const parts = [
      '<section class="result">',
      backLink(),
      '<p class="file-line">' + esc(review.source_filename) + "</p>",
      '<h1 class="headline">' + esc(headline) + "</h1>",
      '<p class="lead">' + esc(sub) + "</p>",
    ];

    if (review.focus) {
      parts.push(
        '<p class="fine">审查重点：' +
          esc(review.focus) +
          (review.skill_name ? "（Skill：" + esc(review.skill_name) + "）" : "") +
          "</p>",
      );
    }

    if (review.status === "rejected" || review.status === "changes_requested") {
      parts.push(
        '<p class="banner">' +
          esc(
            review.status === "rejected"
              ? "您已标记这份合同不能接受，下方问题清单可作为修改依据。"
              : "您已标记这份合同需要修改，修改后请重新上传审查。",
          ) +
          "</p>",
      );
    } else if (review.status === "unreviewed_red_risk") {
      parts.push(
        '<p class="banner">人工确认已超时，这份报告没有获得确认，不能当作可签署的结论。</p>',
      );
    }

    parts.push('<ol class="risks">');
    findings.forEach((finding) => parts.push(riskCard(finding)));
    parts.push("</ol>");

    if (report) {
      parts.push(
        '<div class="down">' +
          '<span>下载报告</span>' +
          '<a href="/api/reviews/' +
          encodeURIComponent(review.review_id) +
          '/report?format=markdown" data-format="markdown">Markdown</a>' +
          "</div>",
      );
    }

    parts.push(
      '<p class="fine">' +
        esc(
          report && report.overall_level
            ? "风险等级由规则引擎判定，解释只做说明，不会改变等级。"
            : "风险等级由规则引擎判定。",
        ) +
        "</p>",
      "</section>",
    );

    dom.view.innerHTML = parts.join("");
  }

  /* 待确认：规则结果已就绪（审批载荷），确认后才生成正式报告与解释 */
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
      '<section class="result">',
      backLink(),
      '<p class="file-line">' + esc(review.source_filename) + "</p>",
      '<h1 class="headline">发现 ' + total + " 处高风险，待您确认</h1>",
      '<p class="lead">规则已经定位到以下条款。请先核对；确认后生成完整报告' +
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

    parts.push(confirmPanel(total), "</section>");

    dom.view.innerHTML = parts.join("");
    bindConfirm();
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
  bindSkills();
  bindLlm();
  bindHistory();
  bindLegal();
  checkHealth();
  loadProviders();
  refreshSession();
  window.addEventListener("hashchange", route);
  route();
})();
