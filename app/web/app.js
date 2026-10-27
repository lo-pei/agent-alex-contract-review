/* Agent Alex · 合同审查工作台（原生 JS，无框架 / 无构建 / 无外部依赖）
 *
 * 边界（ADR-009）：
 * - 浏览器只渲染服务端返回的 `ReviewSummary` / `ReviewReport`，不判定风险等级；
 * - 人工决定只 POST `/api/reviews/{id}/decisions`，由 `ReviewService.resume()` 恢复图；
 * - 任何动态文本先 `esc()`，合同原文可能包含 HTML。
 */

(() => {
  "use strict";

  const REVIEWS = "/api/reviews";
  const RULES = "/api/rules";
  const HEALTH = "/health";
  const STORAGE_KEY = "agent-alex.review-id";
  const MAX_UPLOAD_MB = 15;
  const ALLOWED = new Set([".txt", ".md", ".markdown", ".pdf", ".docx"]);
  const POLL_INTERVAL_MS = 1500;
  const POLL_MAX_TRIES = 80;

  const LEVELS = { red: "红色", yellow: "黄色", pass: "通过", unknown: "未知" };
  const LEVEL_TONE = { red: "red", yellow: "yellow", pass: "pass", unknown: "neutral" };
  const STATUSES = {
    running: "进行中",
    completed: "已完成",
    failed: "失败",
    approved: "已批准",
    rejected: "已拒绝",
    changes_requested: "要求修改",
    unreviewed_red_risk: "未确认（超时）",
    not_contract: "未执行（不是合同）",
  };
  const STATUS_TONE = {
    approved: "pass",
    changes_requested: "yellow",
    rejected: "red",
    unreviewed_red_risk: "red",
    failed: "red",
  };
  const ACTIONS = {
    approve: { title: "批准", note: "已人工确认红色风险，接受当前条款" },
    request_changes: { title: "要求修改", note: "退回业务或法务，按意见修订后重新审查" },
    reject: { title: "拒绝", note: "风险不可接受，终止本次合作审查" },
  };
  const EXTRACTION = { ok: "成功", degraded: "部分降级", skipped: "未执行" };
  const EXPLANATION = { ok: "模型解释", fallback: "规则兜底", skipped: "未执行" };
  const EXPLANATION_SOURCE = { llm: "模型", rule: "规则兜底", none: "无" };
  const CATEGORIES = {
    trade_term: "贸易术语",
    payment: "付款",
    delivery: "交付",
    inspection: "检验",
    warranty: "质保",
    liability: "责任",
    dispute: "争议解决",
    force_majeure: "不可抗力",
    compliance: "合规",
    preamble: "序言",
  };
  const FIELDS = {
    seller: "卖方",
    buyer: "买方",
    goods_description: "货物描述",
    quantity: "数量",
    unit_price: "单价",
    total_amount: "合同总额",
    currency: "币种",
    incoterms: "贸易术语",
    incoterms_version: "术语版本",
    delivery_date: "交货时间",
    payment_method: "付款方式",
    payment_terms: "付款条件",
    inspection_standard: "检验标准",
    warranty_period: "质保期",
    liability_cap: "责任上限",
    governing_law: "适用法律",
    dispute_resolution: "争议解决",
  };
  const FIELD_ORDER = Object.keys(FIELDS);

  const ICON_UPLOAD =
    '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">' +
    '<path d="M12 16V4m0 0L8 8m4-4 4 4"/>' +
    '<path d="M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"/></svg>';
  const ICON_CARET =
    '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="m6 3.5 4.5 4.5L6 12.5"/></svg>';
  const ICON_INFO =
    '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="8.5"/><path d="M12 10.5v5M12 7.6v.4"/></svg>';

  const state = {
    reviewId: null,
    review: null,
    rules: null,
    rulesError: null,
    health: null,
    file: null,
    busy: false,
    pollTimer: null,
    pollTries: 0,
    draft: null,
  };

  const dom = {};

  // ------------------------------------------------------------------ 基础工具
  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[ch]);

  function fmtBytes(bytes) {
    if (!Number.isFinite(bytes)) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function fmtTime(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "—";
    const pad = (n) => String(n).padStart(2, "0");
    return (
      `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
      `${pad(date.getHours())}:${pad(date.getMinutes())}`
    );
  }

  function levelPill(level) {
    const key = LEVELS[level] ? level : "unknown";
    return `<span class="level-pill ${LEVEL_TONE[key]}">${LEVELS[key]}</span>`;
  }

  function statusPill(status) {
    const key = STATUSES[status] ? status : "completed";
    return `<span class="level-pill ${STATUS_TONE[key] || "neutral"}">${STATUSES[key]}</span>`;
  }

  function ruleTitle(ruleId) {
    const rule = state.rules && state.rules.rules.find((item) => item.rule_id === ruleId);
    return rule ? rule.title : ruleId;
  }

  function toast(message, tone = "info") {
    if (!dom.toast) return;
    dom.toastText.textContent = message;
    dom.toast.dataset.tone = tone;
    dom.toast.dataset.visible = "true";
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => {
      dom.toast.dataset.visible = "false";
    }, tone === "error" ? 7000 : 3600);
  }

  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, options);
    } catch {
      const error = new Error("无法连接本地服务，请确认服务仍在运行");
      error.status = 0;
      throw error;
    }
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    if (!response.ok) {
      const detail = data && typeof data.detail === "string" ? data.detail : null;
      const error = new Error(detail || `请求失败（HTTP ${response.status}）`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function remember(reviewId) {
    try {
      if (reviewId) localStorage.setItem(STORAGE_KEY, reviewId);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* 隐私模式下 localStorage 可能不可用，忽略 */
    }
  }

  function readStored() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function route() {
    const raw = window.location.hash.replace(/^#\/?/, "");
    const parts = raw.split("/").filter(Boolean);
    return { name: parts[0] || "workbench", id: parts[1] || null };
  }

  function navigate(name, id = null) {
    const target = `#/${name}${id ? `/${id}` : ""}`;
    if (window.location.hash === target) render();
    else window.location.hash = target;
  }

  function on(selector, event, handler) {
    const node = dom.view.querySelector(selector);
    if (node) node.addEventListener(event, handler);
  }

  function onAll(selector, event, handler) {
    dom.view.querySelectorAll(selector).forEach((node) => node.addEventListener(event, handler));
  }

  // ------------------------------------------------------------------ 视图框架
  function setChrome(name) {
    const crumbs = {
      workbench: "审查工作台",
      review: "当前审查",
      report: "复核报告",
      rules: "规则集",
    };
    dom.crumbs.textContent = crumbs[name] || crumbs.workbench;
    dom.navItems.forEach((item) => {
      if (item.dataset.nav === name) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    });
  }

  function updateBadges() {
    const review = state.review;
    const approval = review && review.approval;
    if (approval && review.awaiting_human) {
      dom.reviewBadge.textContent = String(approval.findings_total);
      dom.reviewBadge.hidden = false;
    } else {
      dom.reviewBadge.hidden = true;
    }
    if (state.rules) {
      dom.rulesBadge.textContent = String(state.rules.count);
      dom.rulesBadge.hidden = false;
    } else {
      dom.rulesBadge.hidden = true;
    }
  }

  function setApiState(online) {
    dom.apiStatus.dataset.state = online ? "online" : "offline";
    dom.apiStatusText.textContent = online ? "服务在线" : "服务离线";
  }

  async function checkHealth() {
    try {
      state.health = await api(HEALTH);
      setApiState(true);
    } catch {
      setApiState(false);
    }
  }

  async function loadRules() {
    try {
      state.rules = await api(RULES);
      state.rulesError = null;
    } catch (error) {
      state.rules = null;
      state.rulesError = error.message;
    }
    updateBadges();
    if (route().name === "rules" || route().name === "workbench") render();
  }

  // ------------------------------------------------------------------ 渲染入口
  function render() {
    const current = route();
    setChrome(current.name);
    updateBadges();

    if (current.name !== "review") stopPolling();

    if (current.name === "rules") {
      renderRules();
      return;
    }
    if (current.name === "workbench") {
      renderWorkbench();
      return;
    }
    if (!state.review) {
      renderNoSession(current.name);
      return;
    }
    if (state.review.status === "not_contract") {
      renderNotContract(state.review);
      return;
    }
    if (current.name === "review") {
      if (state.review.report && !state.review.awaiting_human) {
        navigate("report", state.review.review_id);
        return;
      }
      renderReview();
      return;
    }
    if (current.name === "report") {
      renderReport();
      return;
    }
    renderWorkbench();
  }

  // ------------------------------------------------------------------ 工作台
  function renderWorkbench() {
    const review = state.review;
    const rules = state.rules;
    const reviewLevel = review
      ? review.status === "not_contract"
        ? statusPill(review.status)
        : levelPill(review.overall_level)
      : "";
    const fileRow = state.file
      ? `<div class="file-row">
           <span class="file-name">${esc(state.file.name)}</span>
           <span class="meta">${fmtBytes(state.file.size)}</span>
           <button class="btn small" id="clear-file" type="button">移除</button>
         </div>`
      : "";

    const session = review
      ? `<div class="session">
           <div class="file-row">
             <span class="file-name">${esc(review.source_filename)}</span>
             ${reviewLevel}
           </div>
           <dl class="kv">
             <dt>状态</dt><dd>${esc(STATUSES[review.status] || review.status)}</dd>
             <dt>审查编号</dt><dd>${esc(review.review_id)}</dd>
             <dt>抽取</dt><dd>${esc(EXTRACTION[review.extraction_status] || review.extraction_status)}</dd>
           </dl>
           <div class="form-actions">
             <a class="btn small" href="#/review/${esc(review.review_id)}">${
               review.status === "not_contract" ? "查看未执行原因" : "查看审查"
             }</a>
             ${review.report ? `<a class="btn small" href="#/report/${esc(review.review_id)}">查看报告</a>` : ""}
           </div>
         </div>`
      : `<div class="empty-line">还没有审查记录。上传一份合同即可开始。</div>`;

    const preview = rules
      ? `<div class="rule-preview">
           ${rules.rules
             .slice(0, 3)
             .map(
               (rule) => `<div class="rule-preview-row">
                 <span class="level-pill ${LEVEL_TONE[rule.risk_level]}">${LEVELS[rule.risk_level]}</span>
                 <span class="rule-preview-name"><span class="mono">${esc(rule.rule_id)}</span> · ${esc(rule.title)}</span>
               </div>`,
             )
             .join("")}
         </div>`
      : state.rulesError
        ? `<div class="empty-line">规则集加载失败：${esc(state.rulesError)}</div>`
        : `<div class="rule-preview">
             ${[0, 1, 2]
               .map(() => `<div class="rule-preview-row"><span class="skl w-40"></span><span class="skl w-80"></span></div>`)
               .join("")}
           </div>`;

    dom.view.innerHTML = `
      <header class="title-row">
        <div class="title-main">
          <h1>审查工作台</h1>
          <p class="subline">上传合同 → 规则判级 → 人工确认红色风险 → 生成可追溯报告。等级只由 Python 规则决定，模型只做抽取与解释。</p>
        </div>
        <div class="title-actions">
          ${
            review
              ? `<a class="btn" href="#/review/${esc(review.review_id)}">${
                  review.status === "not_contract" ? "查看上次结果" : "继续上次审查"
                }</a>`
              : ""
          }
          <button class="btn primary" type="button" id="pick-file">选择合同</button>
        </div>
      </header>

      <div class="notice">${ICON_INFO}<span>上传后会先判断这是不是国际货物销售合同：论文、法规、说明书等材料会被直接拒绝，不进入判级。等级只由 Python 规则决定，模型只做抽取与解释。</span></div>

      <div class="grid-main">
        <section class="panel">
          <header class="panel-head">
            <h2>上传合同</h2>
            <span class="meta">TXT / MD / PDF / DOCX · ≤ ${MAX_UPLOAD_MB} MB</span>
          </header>
          <div class="panel-body">
            <div class="dropzone" id="dropzone" role="button" tabindex="0" data-dragging="false" aria-describedby="drop-note">
              <span class="dropzone-icon">${ICON_UPLOAD}</span>
              <span class="drop-title">拖拽合同到这里，或点击选择文件</span>
              <span class="drop-note" id="drop-note">文本型 PDF / DOCX；扫描件需先 OCR，当前不支持</span>
            </div>
            <input class="visually-hidden" id="file-input" type="file" accept=".txt,.md,.markdown,.pdf,.docx" />
            ${fileRow}
            <div class="form-actions">
              <button class="btn primary" type="button" id="start-button" ${state.file && !state.busy ? "" : "disabled"}>
                ${state.busy ? "正在提交…" : "开始审查"}
              </button>
              <span class="meta">${state.file ? "将执行 13 条规则的完整链路" : "选择文件后可开始"}</span>
            </div>

            <ol class="pipeline">
              <li><span class="pipeline-index">1</span><span class="pipeline-label">解析文档</span><span class="pipeline-note">页码与字符偏移</span></li>
              <li><span class="pipeline-index">2</span><span class="pipeline-label">判断类型</span><span class="pipeline-note">不是合同直接停止</span></li>
              <li><span class="pipeline-index">3</span><span class="pipeline-label">切分条款</span><span class="pipeline-note">标题优先，段落兜底</span></li>
              <li><span class="pipeline-index">4</span><span class="pipeline-label">抽取要素</span><span class="pipeline-note">17 个字段，可降级</span></li>
              <li><span class="pipeline-index">5</span><span class="pipeline-label">规则判级</span><span class="pipeline-note">13 条规则，唯一等级来源</span></li>
              <li><span class="pipeline-index">6</span><span class="pipeline-label">人工确认</span><span class="pipeline-note">仅红色风险触发</span></li>
            </ol>
          </div>
        </section>

        <div class="stack">
          <section class="panel">
            <header class="panel-head">
              <h2>本次会话</h2>
              <span class="meta">${review ? "已保存到本机" : "等待上传"}</span>
            </header>
            <div class="panel-body">${session}</div>
          </section>

          <section class="panel">
            <header class="panel-head">
              <h2>规则集</h2>
              <a class="text-link" href="#/rules">查看全部</a>
            </header>
            <div class="panel-body">${preview}</div>
          </section>

          <section class="panel">
            <header class="panel-head"><h2>判级口径</h2><span class="meta">Python 规则唯一来源</span></header>
            <div class="panel-body">
              <ul class="bullet-list">
                <li><span>模型只做要素抽取与解释，不参与风险判级。</span></li>
                <li><span>红色风险触发暂停，人工确认后才生成报告。</span></li>
                <li><span>未命中不等于无风险，报告会列出已知限制。</span></li>
              </ul>
            </div>
          </section>
        </div>
      </div>`;

    // 文件 input 是随工作台一起渲染的，不能在启动时缓存（否则 undefined）。
    on("pick-file", "click", () => dom.view.querySelector("#file-input")?.click());

    on("clear-file", "click", () => {
      state.file = null;
      render();
    });
    on("start-button", "click", startReview);
    bindUpload();
  }

  function bindUpload() {
    const dropzone = dom.view.querySelector("#dropzone");
    const input = dom.view.querySelector("#file-input");
    if (!dropzone || !input) return;

    dropzone.addEventListener("click", (event) => {
      if (event.target === input) return;
      input.click();
    });
    dropzone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", () => {
      const [file] = input.files || [];
      if (file) acceptFile(file);
    });
    ["dragenter", "dragover"].forEach((name) =>
      dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        dropzone.dataset.dragging = "true";
      }),
    );
    ["dragleave", "dragend"].forEach((name) =>
      dropzone.addEventListener(name, () => {
        dropzone.dataset.dragging = "false";
      }),
    );
    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropzone.dataset.dragging = "false";
      const [file] = (event.dataTransfer && event.dataTransfer.files) || [];
      if (file) acceptFile(file);
    });
  }

  function acceptFile(file) {
    const name = file.name || "";
    const dot = name.lastIndexOf(".");
    const ext = dot >= 0 ? name.slice(dot).toLowerCase() : "";
    if (!ALLOWED.has(ext)) {
      toast(`不支持的文件类型 ${ext || "（无扩展名）"}；支持 .txt / .md / .pdf / .docx`, "error");
      return;
    }
    if (file.size === 0) {
      toast("文件为空，请检查后重新选择", "error");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      toast(`文件超过 ${MAX_UPLOAD_MB} MB 上限`, "error");
      return;
    }
    state.file = file;
    render();
  }

  async function startReview() {
    if (!state.file || state.busy) return;
    state.busy = true;
    render();
    const body = new FormData();
    body.append("file", state.file);
    try {
      const review = await api(REVIEWS, { method: "POST", body });
      state.review = review;
      state.reviewId = review.review_id;
      state.draft = null;
      state.file = null;
      remember(review.review_id);
      if (review.status === "not_contract") {
        toast("这份文件不是合同，已停止审查", "error");
      } else {
        toast("审查已提交");
      }
      navigate("review", review.review_id);
    } catch (error) {
      toast(error.message || "提交失败", "error");
      if (error.status === 413) state.file = null;
    } finally {
      state.busy = false;
      if (route().name === "workbench") render();
    }
  }

  // ------------------------------------------------------------------ 审查 / 审批
  function renderReview() {
    const review = state.review;
    if (review.status === "not_contract") {
      renderNotContract(review);
      return;
    }
    if (review.status === "failed") {
      renderFailure(review);
      return;
    }
    if (review.awaiting_human && review.approval) {
      renderApproval(review);
      return;
    }
    renderRunning(review);
  }

  function reviewHeader(review, title, subline, actions, metaSuffix = "") {
    return `
      <header class="title-row">
        <div class="title-main">
          <p class="meta mono">${esc(review.source_filename)} · 审查 ${esc(review.review_id)}${esc(
            metaSuffix,
          )}</p>
          <h1>${esc(title)}</h1>
          <p class="subline">${subline}</p>
        </div>
        <div class="title-actions">${actions}</div>
      </header>`;
  }

  function renderRunning(review) {
    dom.view.innerHTML = `
      ${reviewHeader(
        review,
        "正在审查",
        "正在执行规则审查：解析 → 切分 → 抽取 → 判级。若出现红色风险，流程会暂停并等待人工确认。",
        `<span class="pill" data-state="pending"><span class="dot"></span>进行中</span>
         <button class="btn" type="button" id="refresh">刷新状态</button>`,
      )}

      <div class="kpi-row">
        <div class="kpi"><p class="kpi-label">红色风险</p><p class="kpi-value"><span class="skl h-24 w-40"></span></p></div>
        <div class="kpi"><p class="kpi-label">黄色风险</p><p class="kpi-value"><span class="skl h-24 w-40"></span></p></div>
        <div class="kpi"><p class="kpi-label">抽取状态</p><p class="kpi-value small"><span class="skl w-60"></span></p></div>
        <div class="kpi"><p class="kpi-label">规则集</p><p class="kpi-value small"><span class="skl w-40"></span></p></div>
      </div>

      <section class="panel">
        <header class="panel-head"><h2>风险台账</h2><span class="meta">正在计算</span></header>
        <div class="ledger">
          ${[0, 1, 2]
            .map(
              () => `<div class="skl-row">
                <span class="skl w-40"></span><span class="skl w-60"></span><span class="skl w-80"></span>
              </div>`,
            )
            .join("")}
        </div>
      </section>`;

    on("refresh", "click", () => refreshReview());
    startPolling();
  }

  function renderApproval(review) {
    const approval = review.approval;
    const findings = approval.findings || [];
    const draft = state.draft || {};
    const selected = draft.action || "";

    const ledger = findings.length
      ? findings.map((finding) => findingRow(finding, { open: false })).join("")
      : `<div class="panel-body"><div class="empty-line">载荷中没有红色风险条目，请刷新状态后重试。</div></div>`;

    const truncated = approval.truncated
      ? `<p class="fineprint">另有 ${approval.truncated} 条红色风险未在载荷中展开，报告会包含全部条目。</p>`
      : "";

    const verify = (approval.to_verify || []).length
      ? `<section class="panel">
           <header class="panel-head"><h2>待人工核对</h2><span class="meta">抽取与校验提示</span></header>
           <div class="panel-body">
             ${approval.to_verify.map((item) => `<div class="verify-item"><span>${esc(item)}</span></div>`).join("")}
           </div>
         </section>`
      : "";

    const noticeList = (items) =>
      `<ul class="bullet-list">${items.map((item) => `<li><span>${esc(item)}</span></li>`).join("")}</ul>`;
    const diagnostics = [
      review.errors.length
        ? `<div class="notice is-error">${ICON_INFO}<div class="notice-body">
             <p class="notice-title">本次审查的错误</p>${noticeList(review.errors)}
           </div></div>`
        : "",
      review.warnings.length
        ? `<div class="notice">${ICON_INFO}<div class="notice-body">
             <p class="notice-title">降级与提示</p>${noticeList(review.warnings)}
           </div></div>`
        : "",
    ].join("");

    dom.view.innerHTML = `
      ${reviewHeader(
        review,
        "确认红色风险",
        `检测到 ${approval.findings_total} 条红色风险，流程已暂停；人工确认后才生成报告。`,
        `<span class="level-pill red">待人工确认</span>
         <button class="btn" type="button" id="refresh">刷新状态</button>
         <a class="btn ghost" href="#/workbench">新建审查</a>`,
      )}

      <div class="notice">${ICON_INFO}<span>${esc(approval.instructions)}</span></div>
      ${diagnostics}

      <div class="kpi-row">
        <div class="kpi">
          <p class="kpi-label">红色风险</p>
          <p class="kpi-value is-red"><span class="num">${approval.findings_total}</span><span class="unit">条</span></p>
          <p class="kpi-note">全部需要人工确认</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">待人工核对</p>
          <p class="kpi-value ${approval.to_verify.length ? "is-amber" : ""}"><span class="num">${approval.to_verify.length}</span><span class="unit">项</span></p>
          <p class="kpi-note">抽取与校验提示</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">抽取状态</p>
          <p class="kpi-value small">${esc(EXTRACTION[approval.extraction_status] || approval.extraction_status)}</p>
          <p class="kpi-note">字段规则随之中止</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">规则集</p>
          <p class="kpi-value small">${state.rules ? `v${state.rules.ruleset_version} · ${state.rules.count} 条` : "—"}</p>
          <p class="kpi-note">Python 规则唯一判级</p>
        </div>
      </div>

      <div class="grid-side">
        <div class="stack">
          <section class="panel">
            <header class="panel-head">
              <h2>红色风险</h2>
              <span class="meta">展示 ${findings.length} 条 / 共 ${approval.findings_total} 条</span>
            </header>
            <div class="ledger">${ledger}</div>
            ${truncated ? `<div class="panel-body">${truncated}</div>` : ""}
          </section>

          <section class="panel">
            <header class="panel-head"><h2>复核要点</h2><span class="meta">三步</span></header>
            <div class="panel-body">
              <ol class="pipeline compact">
                <li><span class="pipeline-index">1</span><span class="pipeline-label">展开风险条目</span><span class="pipeline-note">核对规则理由与原文摘录</span></li>
                <li><span class="pipeline-index">2</span><span class="pipeline-label">核对抽取要素</span><span class="pipeline-note">金额、术语与争议解决</span></li>
                <li><span class="pipeline-index">3</span><span class="pipeline-label">记录结论</span><span class="pipeline-note">复核人与意见写入审计记录</span></li>
              </ol>
            </div>
          </section>
        </div>

        <div class="stack">
          <form class="panel" id="decision-form" novalidate>
            <header class="panel-head"><h2>人工复核</h2><span class="meta">必填项已标注</span></header>
            <div class="panel-body">
              <div class="field">
                <label class="field-label" for="reviewer">复核人</label>
                <input class="input" id="reviewer" name="reviewer" maxlength="64" autocomplete="name"
                  placeholder="姓名或工号" value="${esc(draft.reviewer || "")}" />
              </div>

              <div class="field">
                <span class="field-label" id="action-label">复核结论</span>
                <div class="choices" role="radiogroup" aria-labelledby="action-label">
                  ${Object.entries(ACTIONS)
                    .map(
                      ([value, action]) => `<label class="choice" data-selected="${selected === value}">
                        <input type="radio" name="action" value="${value}" ${selected === value ? "checked" : ""} />
                        <span class="choice-text">
                          <span class="choice-title">${esc(action.title)}</span>
                          <span class="choice-note">${esc(action.note)}</span>
                        </span>
                      </label>`,
                    )
                    .join("")}
                </div>
              </div>

              <div class="field">
                <label class="field-label" for="comment">复核意见（可选）</label>
                <textarea class="textarea" id="comment" name="comment" maxlength="2000"
                  placeholder="记录核对依据、需对方修改的条款等">${esc(draft.comment || "")}</textarea>
              </div>

              <div class="form-actions">
                <button class="btn primary" type="submit">提交复核结论</button>
                <button class="btn ghost" type="button" id="timeout-button">标记超时</button>
              </div>
              <p class="form-error" id="decision-error" role="alert"></p>
              <p class="fineprint">提交后流程恢复并生成报告。标记超时的结果为“未确认”，绝不会自动通过；复核人、结论与意见会写入审计记录。</p>
            </div>
          </form>
          ${verify}
        </div>
      </div>`;

    const form = dom.view.querySelector("#decision-form");
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitDecision();
    });
    form.addEventListener("change", () => {
      const action = form.querySelector('input[name="action"]:checked');
      form.querySelectorAll(".choice").forEach((choice) => {
        const input = choice.querySelector("input");
        choice.dataset.selected = String(Boolean(input && input.checked));
      });
      state.draft = {
        reviewer: form.reviewer.value,
        comment: form.comment.value,
        action: action ? action.value : "",
      };
    });
    form.addEventListener("input", () => {
      const action = form.querySelector('input[name="action"]:checked');
      state.draft = {
        reviewer: form.reviewer.value,
        comment: form.comment.value,
        action: action ? action.value : "",
      };
    });
    on("timeout-button", "click", () => {
      if (!window.confirm("确认标记为超时未确认？该结果会写入报告，且不会自动通过。")) return;
      requestDecision("timeout");
    });
    on("refresh", "click", () => refreshReview());
  }

  function findingRow(finding, options = {}) {
    const level = finding.risk_level === "red" ? "red" : "yellow";
    const title = finding.title || ruleTitle(finding.rule_id);
    const clauses = (finding.clause_ids || [])
      .map((id) => `<span class="chip">${esc(id)}</span>`)
      .join("");
    const citation = (finding.citations || [])[0];
    const quotes = (finding.quotes || [])
      .map((quote) => `<blockquote class="quote">${esc(quote)}</blockquote>`)
      .join("");

    let explanation = "";
    if (options.showExplanation) {
      const source = EXPLANATION_SOURCE[finding.explanation_source] || "无";
      const parts = [];
      if (finding.explanation_summary) {
        parts.push(`<p class="explain-summary">${esc(finding.explanation_summary)}</p>`);
      }
      if (finding.explanation_quote) {
        parts.push(`<blockquote class="quote">${esc(finding.explanation_quote)}</blockquote>`);
      }
      if (parts.length) {
        const foot = [`来源 ${source}`];
        if (finding.explanation_grounded) foot.push("引文已核对");
        if (finding.explanation_citation) {
          foot.push(`<span class="mono">${esc(finding.explanation_citation)}</span>`);
        }
        explanation = `<dt>解释</dt><dd><div class="explain-block">${parts.join("")}
          <div class="explain-foot">${foot.map((item) => `<span>${item}</span>`).join("")}</div>
        </div></dd>`;
      }
    }

    const knowledge = (finding.knowledge_citations || [])
      .map((id) => `<span class="chip">${esc(id)}</span>`)
      .join("");
    const knowledgeRow = knowledge
      ? `<dt>知识引用</dt><dd>${knowledge}</dd>`
      : "";

    return `
      <details class="finding"${options.open ? " open" : ""}>
        <summary class="finding-row">
          <span class="level-pill ${level}">${LEVELS[level]}</span>
          <span class="finding-id">${esc(finding.rule_id)}</span>
          <span class="finding-title">
            <span class="finding-name">${esc(title)}</span>
            <span class="finding-reason">${esc(finding.reason)}</span>
          </span>
          <span class="finding-meta">${clauses}</span>
          <span class="caret">${ICON_CARET}</span>
        </summary>
        <div class="finding-body">
          <dl class="detail-list">
            <dt>规则理由</dt><dd>${esc(finding.reason)}</dd>
            ${finding.suggestion ? `<dt>处理建议</dt><dd>${esc(finding.suggestion)}</dd>` : ""}
            <dt>涉及条款</dt><dd>${clauses || `<span class="meta">未定位</span>`}</dd>
            <dt>原文摘录</dt><dd>${
              quotes || `<span class="meta">载荷未提供摘录，请在原文核对</span>`
            }${citation ? `<span class="cite">${esc(citation)}</span>` : ""}</dd>
            ${explanation}
            ${knowledgeRow}
          </dl>
        </div>
      </details>`;
  }

  function setFormDisabled(form, disabled) {
    if (!form) return;
    form.querySelectorAll("input, textarea, button").forEach((node) => {
      node.disabled = disabled;
    });
  }

  function submitDecision() {
    const form = dom.view.querySelector("#decision-form");
    if (!form) return;
    const reviewer = form.reviewer.value.trim();
    const action = form.querySelector('input[name="action"]:checked');
    const comment = form.comment.value.trim();
    state.draft = { reviewer, comment, action: action ? action.value : "" };
    if (!reviewer) {
      showDecisionError("请填写复核人（写入审计记录）");
      form.reviewer.focus();
      return;
    }
    if (!action) {
      showDecisionError("请选择复核结论");
      return;
    }
    requestDecision(action.value);
  }

  function showDecisionError(message) {
    const node = dom.view.querySelector("#decision-error");
    if (node) node.textContent = message;
  }

  async function requestDecision(action) {
    const form = dom.view.querySelector("#decision-form");
    const draft = state.draft || {};
    if (!form || state.busy) return;
    const reviewer = (form.reviewer.value || "").trim();
    if (!reviewer) {
      showDecisionError("标记超时也需要复核人，用于审计记录");
      form.reviewer.focus();
      return;
    }
    const payload = {
      action,
      reviewer,
      comment: (form.comment.value || "").trim() || null,
    };
    state.busy = true;
    setFormDisabled(form, true);
    showDecisionError("");
    try {
      const updated = await api(`${REVIEWS}/${state.review.review_id}/decisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.busy = false;
      state.review = updated;
      state.draft = null;
      toast(action === "timeout" ? "已标记为未确认" : "复核结论已提交");
      if (updated.report) navigate("report", updated.review_id);
      else render();
    } catch (error) {
      state.busy = false;
      if (error.status === 404) {
        remember(null);
        state.review = null;
        state.reviewId = null;
        toast("审查记录已失效，请重新上传合同", "error");
        navigate("workbench");
        return;
      }
      if (error.status === 409) {
        try {
          state.review = await api(`${REVIEWS}/${state.review.review_id}`);
        } catch {
          /* 失败时保留当前状态，由用户刷新 */
        }
        toast("状态已变化，已重新加载最新审批载荷", "error");
        render();
        return;
      }
      toast(error.message || "提交失败", "error");
      render();
      showDecisionError(error.message || "提交失败");
    }
  }

  async function refreshReview() {
    if (!state.review || state.busy) return;
    state.busy = true;
    try {
      state.review = await api(`${REVIEWS}/${state.review.review_id}`);
      toast("已刷新");
    } catch (error) {
      if (error.status === 404) {
        remember(null);
        state.review = null;
        state.reviewId = null;
        toast("审查记录已失效，请重新上传合同", "error");
        navigate("workbench");
        return;
      }
      toast(error.message || "刷新失败", "error");
    } finally {
      state.busy = false;
    }
    render();
  }

  function startPolling() {
    if (state.pollTimer) return;
    state.pollTries = 0;
    const tick = async () => {
      state.pollTimer = null;
      const current = state.review;
      if (!current) return;
      if (current.awaiting_human || current.report || current.status !== "running") return;
      state.pollTries += 1;
      if (state.pollTries > POLL_MAX_TRIES) {
        toast("审查耗时较长，已停止自动刷新，可手动刷新状态");
        return;
      }
      try {
        const next = await api(`${REVIEWS}/${current.review_id}`);
        if (current.review_id !== state.reviewId) return;
        state.review = next;
        if (next.awaiting_human || next.report || next.status !== "running") {
          render();
          return;
        }
      } catch (error) {
        if (error.status === 404) {
          remember(null);
          state.review = null;
          state.reviewId = null;
          navigate("workbench");
          return;
        }
      }
      if (!state.pollTimer) state.pollTimer = setTimeout(tick, POLL_INTERVAL_MS);
    };
    state.pollTimer = setTimeout(tick, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
  }

  // ------------------------------------------------------------------ 报告
  function renderReport() {
    const review = state.review;
    const report = review && review.report;
    if (review && review.status === "not_contract") {
      renderNotContract(review);
      return;
    }
    if (!report) {
      renderNoSession("report");
      return;
    }
    const findings = [...(report.findings || [])].sort((a, b) =>
      a.risk_level === b.risk_level ? 0 : a.risk_level === "red" ? -1 : 1,
    );
    const red = findings.filter((item) => item.risk_level === "red").length;
    const yellow = findings.length - red;

    const allFields = [
      ...FIELD_ORDER.map((key) => [key, FIELDS[key], report.extracted_fields[key]]),
      ...Object.keys(report.extracted_fields || {})
        .filter((key) => !FIELDS[key])
        .map((key) => [key, key, report.extracted_fields[key]]),
    ];
    const filled = allFields.filter(
      ([, , value]) => value !== null && value !== undefined && String(value).trim() !== "",
    );
    const fieldsGrid = filled
      .map(([key, label, value]) => fieldRow(key, value, label))
      .join("");

    const hitl = report.hitl
      ? `<p class="meta-title">人工复核</p>
         <dl class="detail-list">
           <dt>复核人</dt><dd>${esc(report.hitl.reviewer)}</dd>
           <dt>结论</dt><dd>${statusPill(report.status)} <span class="meta">${esc(
             ACTIONS[report.hitl.action]?.title ||
               (report.hitl.action === "timeout" ? "标记超时" : report.hitl.action),
           )}</span></dd>
           <dt>复核意见</dt><dd>${esc(report.hitl.comment || "未填写")}</dd>
         </dl>`
      : `<p class="meta-title">人工复核</p>
         <div class="empty-line">本次没有触发人工确认（未出现红色风险）。</div>`;

    const limitations = (report.limitations || [])
      .map((item) => `<li><span>${esc(item)}</span></li>`)
      .join("");

    const ledger = findings.length
      ? findings.map((finding) => findingRow(finding, { showExplanation: true })).join("")
      : `<div class="panel-body"><div class="empty-line">本次没有命中任何规则。这不等于合同没有风险，请结合已知限制人工复核。</div></div>`;

    dom.view.innerHTML = `
      ${reviewHeader(
        review,
        "审查报告",
        `<span class="status-line">${statusPill(report.status)} <span class="meta">报告生成于 ${esc(
          fmtTime(report.generated_at),
        )} · 规则引擎 ${esc(report.rule_engine_version)}</span></span>`,
        `<a class="btn" href="${REVIEWS}/${esc(report.review_id)}/report?format=markdown" download>下载 Markdown</a>
         <a class="btn" href="${REVIEWS}/${esc(report.review_id)}/report?format=json" download>下载 JSON</a>
         <a class="btn ghost" href="#/workbench">新建审查</a>`,
      )}

      <div class="summary">
        <p class="summary-label">结论</p>
        <p class="summary-text">${esc(report.summary)}</p>
      </div>

      <div class="kpi-row">
        <div class="kpi">
          <p class="kpi-label">红色风险</p>
          <p class="kpi-value ${red ? "is-red" : ""}"><span class="num">${red}</span><span class="unit">条</span></p>
          <p class="kpi-note">已按人工结论出报告</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">黄色风险</p>
          <p class="kpi-value ${yellow ? "is-amber" : ""}"><span class="num">${yellow}</span><span class="unit">条</span></p>
          <p class="kpi-note">建议在签署前修订</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">待人工核对</p>
          <p class="kpi-value"><span class="num">${(report.to_verify || []).length}</span><span class="unit">项</span></p>
          <p class="kpi-note">抽取与校验提示</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">解释状态</p>
          <p class="kpi-value small">${esc(EXPLANATION[report.explanation_status] || report.explanation_status)}</p>
          <p class="kpi-note">${esc(report.explanation_model || "未调用模型")}</p>
        </div>
      </div>

      <section class="panel">
        <header class="panel-head">
          <h2>风险清单</h2>
          <span class="meta">红色 ${red} · 黄色 ${yellow} · 每条附规则与原文证据</span>
        </header>
        <div class="ledger">${ledger}</div>
      </section>

      <section class="panel">
        <header class="panel-head">
          <h2>抽取要素</h2>
          <span class="meta">${filled.length ? `${filled.length} 项已抽取 · 共 ${allFields.length} 项` : "本次未抽取到字段"}</span>
        </header>
        <div class="panel-body">
          ${
            filled.length
              ? `<div class="fields">${fieldsGrid}</div>`
              : `<div class="empty-line">要素抽取未执行或全部字段缺失。依赖抽取的字段规则已跳过，请在签署前人工核对金额、贸易术语与争议解决。</div>`
          }
          ${
            report.to_verify.length
              ? `<div class="verify-list">${report.to_verify
                  .map(
                    (item) => `<div class="verify-item"><span>${esc(item.field)}</span>
                      <span class="verify-reason">${esc(item.reason)}${
                        item.clause_id ? ` · ${esc(item.clause_id)}` : ""
                      }</span></div>`,
                  )
                  .join("")}</div>`
              : ""
          }
        </div>
      </section>

      <section class="panel">
        <header class="panel-head">
          <h2>复核记录与版本</h2>
          <span class="meta">审计留痕 · 附已知限制</span>
        </header>
        <div class="panel-body meta-body">
          ${hitl}
          <div class="meta-sub">
            <p class="meta-title">版本</p>
            <dl class="detail-list">
              <dt>规则引擎</dt><dd>${esc(report.rule_engine_version)}</dd>
              <dt>抽取提示词</dt><dd>${esc(report.prompt_version)}</dd>
              <dt>抽取模型</dt><dd>${esc(report.model_id || "未调用")}</dd>
              <dt>解释提示词</dt><dd>${esc(report.explanation_prompt_version)}</dd>
              <dt>解释模型</dt><dd>${esc(report.explanation_model || "未调用")}</dd>
            </dl>
          </div>
          <div class="meta-sub">
            <p class="meta-title">已知限制</p>
            <ul class="bullet-list">${limitations || "<li><span>报告未附带额外限制说明。</span></li>"}</ul>
          </div>
        </div>
      </section>`;
  }

  function fieldRow(key, value, label = null) {
    const missing = value === null || value === undefined || value === "";
    return `<div class="field-row">
      <span class="field-label-cell">${esc(label || FIELDS[key] || key)}<span class="mono">${esc(key)}</span></span>
      <span class="field-value ${missing ? "missing" : ""}">${missing ? "—" : esc(value)}</span>
    </div>`;
  }

  // ------------------------------------------------------------------ 规则集
  function renderRules() {
    const rules = state.rules;
    const loading = !rules && !state.rulesError;

    const rows = rules
      ? rules.rules
          .map(
            (rule) => `<tr>
              <td class="mono nowrap">${esc(rule.rule_id)}</td>
              <td class="nowrap"><span class="level-pill ${LEVEL_TONE[rule.risk_level]}">${LEVELS[rule.risk_level]}</span></td>
              <td class="nowrap">${esc(CATEGORIES[rule.category] || rule.category)}</td>
              <td>
                <p class="cell-title">${esc(rule.title)}</p>
                <p class="cell-note">${esc(rule.reason)}</p>
              </td>
              <td class="cell-note">${esc(rule.suggestion)}</td>
            </tr>`,
          )
          .join("")
      : "";

    const skeleton = `<tr>${[0, 1, 2, 3, 4]
      .map(() => `<td><span class="skl w-80"></span></td>`)
      .join("")}</tr>`;

    dom.view.innerHTML = `
      <header class="title-row">
        <div class="title-main">
          <h1>规则集</h1>
          <p class="subline">${
            rules
              ? `version ${rules.ruleset_version} · ${rules.count} 条规则 · 引擎 ${esc(
                  rules.rule_engine_version,
                )}。等级只由规则产出，模型不参与判级。`
              : "正在读取服务端规则集…"
          }</p>
        </div>
        <div class="title-actions">
          <button class="btn" type="button" id="reload-rules">刷新</button>
        </div>
      </header>

      ${
        state.rulesError
          ? `<div class="notice is-error">${ICON_INFO}<span>规则集加载失败：${esc(
              state.rulesError,
            )}</span></div>`
          : ""
      }

      <div class="kpi-row">
        <div class="kpi">
          <p class="kpi-label">规则总数</p>
          <p class="kpi-value"><span class="num">${rules ? rules.count : "—"}</span><span class="unit">条</span></p>
        </div>
        <div class="kpi">
          <p class="kpi-label">红色规则</p>
          <p class="kpi-value is-red"><span class="num">${rules ? rules.red_count : "—"}</span><span class="unit">条</span></p>
          <p class="kpi-note">触发后暂停，等待人工确认</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">黄色规则</p>
          <p class="kpi-value is-amber"><span class="num">${rules ? rules.yellow_count : "—"}</span><span class="unit">条</span></p>
          <p class="kpi-note">写入报告，不触发暂停</p>
        </div>
        <div class="kpi">
          <p class="kpi-label">规则集版本</p>
          <p class="kpi-value small">${rules ? `v${rules.ruleset_version}` : "—"}</p>
          <p class="kpi-note">definitions.yaml</p>
        </div>
      </div>

      <section class="panel">
        <header class="panel-head">
          <h2>规则目录</h2>
          <span class="meta">来自 /api/rules · 只读</span>
        </header>
        <div class="table-wrap">
          <table class="data rules-table">
            <colgroup>
              <col class="col-id" />
              <col class="col-level" />
              <col class="col-category" />
              <col />
              <col class="col-suggestion" />
            </colgroup>
            <thead>
              <tr><th>规则编号</th><th>等级</th><th>主题</th><th>检查项与理由</th><th>处理建议</th></tr>
            </thead>
            <tbody>${loading ? skeleton + skeleton + skeleton : rows}</tbody>
          </table>
        </div>
      </section>

      <div class="grid-2">
        <section class="panel">
          <header class="panel-head"><h2>评测口径</h2><span class="meta">ADR-011</span></header>
          <div class="panel-body">
            <dl class="kv eval-list">
              <dt>留出集 holdout4</dt><dd>12 份 · P 1.00 / R 0.889 / F1 0.941</dd>
              <dt>唯一漏报</dt><dd>H39（已知，故意不修）</dd>
              <dt>主集（50 份）</dt><dd>规则级 P/R 1.00（同分布，非泛化）</dd>
              <dt>现象覆盖</dt><dd>21 个 gold 现象覆盖 52.4%</dd>
            </dl>
            <p class="fineprint">silver gold 尚未人工复核；留出集一旦用于定位缺陷即视为已消耗，只能作回归守卫，因此对外只引用 holdout4。</p>
          </div>
        </section>
        <section class="panel">
          <header class="panel-head"><h2>已知边界</h2></header>
          <div class="panel-body">
            <ul class="bullet-list">
              <li><span>13 条规则覆盖 13 类条款主题；未命中 ≠ 无风险。</span></li>
              <li><span>两条字段规则依赖模型抽取，抽取失败时跳过而非误报。</span></li>
              <li><span>仅做签约前预审，不构成法律意见。</span></li>
              <li><span>等级只由 Python 规则决定；模型只做抽取与解释。</span></li>
            </ul>
          </div>
        </section>
      </div>`;

    on("reload-rules", "click", loadRules);
  }

  // ------------------------------------------------------------------ 非合同
  function renderNotContract(review) {
    const check = review.document_check || {};
    const reasons = check.reasons || [];
    const hints = check.hints || [];
    const confidence =
      typeof check.confidence === "number"
        ? `判定置信度 ${Math.round(check.confidence * 100)}%`
        : "未给出判别置信度";
    const list = (items, fallback) =>
      items.length
        ? `<ul class="bullet-list">${items.map((item) => `<li><span>${esc(item)}</span></li>`).join("")}</ul>`
        : `<div class="empty-line">${esc(fallback)}</div>`;

    dom.view.innerHTML = `
      ${reviewHeader(
        review,
        "上传的文件不是合同",
        `<span class="status-line">${statusPill(
          "not_contract",
        )} <span class="meta">${esc(confidence)} · 未执行任何规则判级</span></span>`,
        `<button class="btn primary" type="button" id="restart">重新选择文件</button>
         <a class="btn ghost" href="#/rules">看看规则覆盖范围</a>`,
      )}

      <div class="notice is-error">${ICON_INFO}<div class="notice-body">
        <p class="notice-title">已停止审查</p>
        <p>这里只审查国际货物销售合同。这份文件没有通过文档类型校验，因此没有切分条款、没有抽取要素、也没有执行风险判级。</p>
      </div></div>

      <div class="grid-2">
        <section class="panel">
          <header class="panel-head"><h2>判定依据</h2><span class="meta">确定性规则 · 可复现</span></header>
          <div class="panel-body">${list(reasons, "服务端未返回具体依据。")}</div>
        </section>
        <section class="panel">
          <header class="panel-head"><h2>下一步</h2><span class="meta">换一份文件即可</span></header>
          <div class="panel-body">${list(hints, "请上传国际货物销售合同后重试。")}</div>
        </section>
      </div>

      <p class="fineprint">本次没有生成风险报告：文件只用于判断类型，未被当作合同审查。如果确认这是合同，请上传包含正文条款的完整版本。</p>`;

    on("restart", "click", () => {
      remember(null);
      stopPolling();
      state.review = null;
      state.reviewId = null;
      state.file = null;
      state.draft = null;
      navigate("workbench");
    });
  }

  // ------------------------------------------------------------------ 空态 / 失败
  function renderNoSession(name) {
    const isReport = name === "report";
    dom.view.innerHTML = `
      <header class="title-row">
        <div class="title-main">
          <h1>${isReport ? "还没有可查看的报告" : "还没有进行中的审查"}</h1>
          <p class="subline">上传一份合同后，审查进度与报告会出现在这里；刷新页面也会从本机记录恢复。</p>
        </div>
        <div class="title-actions">
          <a class="btn primary" href="#/workbench">去上传合同</a>
        </div>
      </header>
      <section class="panel">
        <div class="panel-body">
          <div class="empty">
            <span>${isReport ? "报告在人工确认后生成，或由规则直接通过时生成。" : "支持 TXT / MD / PDF / DOCX，单文件不超过 15 MB。"}</span>
            <a class="text-link" href="#/rules">先看看规则集覆盖了哪些条款</a>
          </div>
        </div>
      </section>`;
  }

  function renderFailure(review) {
    const details = [...(review.errors || []), ...(review.warnings || [])];
    dom.view.innerHTML = `
      ${reviewHeader(
        review,
        "审查未完成",
        `<span class="status-line">${statusPill("failed")} <span class="meta">没有生成报告。</span></span>`,
        `<button class="btn" type="button" id="refresh">刷新状态</button>
         <a class="btn ghost" href="#/workbench">新建审查</a>`,
      )}
      <div class="notice is-error">${ICON_INFO}<span>${esc(
        details.length ? details.join("；") : "服务端未返回具体原因，请检查文件格式或服务日志。",
      )}</span></div>
      <section class="panel">
        <header class="panel-head"><h2>排查建议</h2></header>
        <div class="panel-body">
          <ul class="bullet-list">
            <li><span>确认文件是文本型 PDF 或 DOCX（扫描件需先 OCR）。</span></li>
            <li><span>确认文件未超过 15 MB，且扩展名在支持范围内。</span></li>
            <li><span>若抽取失败，检查模型配置；规则仍会在抽取降级时继续执行。</span></li>
          </ul>
        </div>
      </section>`;

    on("refresh", "click", () => refreshReview());
  }

  // ------------------------------------------------------------------ 启动
  function bindChrome() {
    dom.toastClose.addEventListener("click", () => {
      dom.toast.dataset.visible = "false";
    });
    dom.menuButton.addEventListener("click", () => {
      const open = dom.sidebar.dataset.open === "true";
      dom.sidebar.dataset.open = String(!open);
      dom.menuButton.setAttribute("aria-expanded", String(!open));
      dom.scrim.hidden = open;
    });
    dom.scrim.addEventListener("click", () => {
      dom.sidebar.dataset.open = "false";
      dom.menuButton.setAttribute("aria-expanded", "false");
      dom.scrim.hidden = true;
    });
    dom.navItems.forEach((item) =>
      item.addEventListener("click", () => {
        dom.sidebar.dataset.open = "false";
        dom.menuButton.setAttribute("aria-expanded", "false");
        dom.scrim.hidden = true;
      }),
    );
    window.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      dom.sidebar.dataset.open = "false";
      dom.menuButton.setAttribute("aria-expanded", "false");
      dom.scrim.hidden = true;
      dom.toast.dataset.visible = "false";
    });
    window.addEventListener("hashchange", render);

    // 打印时展开所有折叠条目（规则/证据在纸上要能读全）
    window.addEventListener("beforeprint", () => {
      dom.view.querySelectorAll("details.finding").forEach((node) => {
        if (!node.open) {
          node.dataset.printedOpen = "true";
          node.open = true;
        }
      });
    });
    window.addEventListener("afterprint", () => {
      dom.view.querySelectorAll("details.finding[data-printed-open]").forEach((node) => {
        node.open = false;
        delete node.dataset.printedOpen;
      });
    });
  }

  async function fetchReview(reviewId) {
    try {
      const review = await api(`${REVIEWS}/${encodeURIComponent(reviewId)}`);
      state.review = review;
      state.reviewId = review.review_id;
      return review;
    } catch (error) {
      if (error.status === 404) {
        remember(null);
        state.review = null;
        state.reviewId = null;
        return null;
      }
      toast(error.message || "读取审查状态失败", "error");
      return null;
    }
  }

  async function boot() {
    dom.view = document.getElementById("view");
    dom.crumbs = document.getElementById("crumbs-current");
    dom.sidebar = document.getElementById("sidebar");
    dom.menuButton = document.getElementById("menu-button");
    dom.scrim = document.getElementById("scrim");
    dom.toast = document.getElementById("toast");
    dom.toastText = document.getElementById("toast-text");
    dom.toastClose = document.getElementById("toast-close");
    dom.apiStatus = document.getElementById("api-status");
    dom.apiStatusText = document.getElementById("api-status-text");
    dom.navItems = Array.from(document.querySelectorAll(".nav-item[data-nav]"));
    dom.reviewBadge = document.getElementById("nav-review-badge");
    dom.rulesBadge = document.getElementById("nav-rules-badge");

    bindChrome();
    checkHealth();
    setInterval(checkHealth, 30000);
    loadRules();

    const current = route();
    const stored = readStored();
    const reviewId = current.id || stored;
    if (reviewId) {
      await fetchReview(reviewId);
      if (state.review && current.name === "workbench" && !current.id) {
        window.location.hash = `#/review/${state.review.review_id}`;
        return;
      }
    }
    if (!current.id && !state.review && current.name !== "rules") {
      // 没有记录也不在规则页时，停在空态工作台
      if (window.location.hash) window.location.hash = "#/workbench";
    }
    render();
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
