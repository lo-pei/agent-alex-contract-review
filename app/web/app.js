/**
 * Agent Alex · 外贸合同智审助手 —— 原生前端（无框架、无 CDN、无构建步骤）。
 *
 * 职责（ADR-009 第 2 轮补充）：
 * - 只调用 FastAPI 暴露的 REST 接口，不在浏览器里判级、改级或拼 Command；
 * - 审批决定一律 POST /api/reviews/{id}/decisions，由 ReviewService 统一恢复；
 * - 所有文本先转义再插入 DOM，避免合同内容里的 HTML 被当成标记执行。
 */
(() => {
  "use strict";

  const REVIEWS = "/api/reviews";
  const STORAGE_KEY = "agent-alex.review-id";
  const MAX_UPLOAD_MB = 15;
  const ALLOWED = new Set([".txt", ".md", ".markdown", ".pdf", ".docx"]);
  const POLL_INTERVAL_MS = 1500;
  const POLL_MAX_TRIES = 80;

  const LEVEL_LABELS = { red: "红色", yellow: "黄色", pass: "通过", unknown: "未知" };
  const STATUS_LABELS = {
    running: "审查中",
    completed: "审查完成",
    failed: "审查失败",
    approved: "已批准",
    rejected: "已拒绝",
    changes_requested: "要求修改",
    unreviewed_red_risk: "未获人工确认",
  };
  const ACTION_LABELS = {
    approve: "批准",
    request_changes: "要求修改",
    reject: "拒绝",
    timeout: "超时未确认",
  };
  const EXTRACTION_LABELS = { ok: "抽取成功", degraded: "抽取降级", skipped: "未抽取" };
  const EXPLANATION_LABELS = { ok: "模型解释", fallback: "规则兜底", skipped: "未解释" };
  const FIELD_LABELS = {
    seller: "卖方",
    buyer: "买方",
    goods_description: "货物描述",
    quantity: "数量",
    unit_price: "单价",
    total_amount: "总金额",
    currency: "币种",
    incoterms: "贸易术语",
    incoterms_version: "术语版本",
    delivery_date: "交付期限",
    payment_method: "付款方式",
    payment_terms: "付款条件",
    inspection_standard: "检验标准",
    warranty_period: "质保期",
    liability_cap: "责任上限",
    governing_law: "适用法律",
    dispute_resolution: "争议解决",
  };

  const dom = {
    dropzone: document.getElementById("dropzone"),
    fileInput: document.getElementById("file-input"),
    fileChip: document.getElementById("file-chip"),
    fileName: document.getElementById("file-name"),
    fileSize: document.getElementById("file-size"),
    fileIcon: document.querySelector(".file-chip-icon"),
    clearFile: document.getElementById("clear-file"),
    startButton: document.getElementById("start-button"),
    resetButton: document.getElementById("reset-button"),
    apiStatus: document.getElementById("api-status"),
    apiStatusText: document.getElementById("api-status-text"),
    workingDetail: document.getElementById("working-detail"),
    states: {
      empty: document.getElementById("state-empty"),
      working: document.getElementById("state-working"),
      approval: document.getElementById("state-approval"),
      report: document.getElementById("state-report"),
    },
    steps: Array.from(document.querySelectorAll(".step")),
    toast: document.getElementById("toast"),
  };

  /** @type {{file: File|null, review: any|null, busy: boolean, pollTimer: number|null}} */
  const state = { file: null, review: null, busy: false, pollTimer: null };

  // ---------- 通用工具 ----------

  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch],
    );

  const formatBytes = (bytes) => {
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / 1024 ** index;
    return `${value >= 10 || index === 0 ? Math.round(value) : value.toFixed(1)} ${units[index]}`;
  };

  const formatTime = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString("zh-CN", { hour12: false });
  };

  let toastTimer = null;
  const toast = (message, tone = "info") => {
    dom.toast.textContent = message;
    dom.toast.dataset.tone = tone;
    dom.toast.hidden = false;
    dom.toast.dataset.visible = "true";
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      dom.toast.dataset.visible = "false";
      window.setTimeout(() => {
        dom.toast.hidden = true;
      }, 200);
    }, 3600);
  };

  async function api(path, options = {}) {
    const response = await fetch(path, options);
    if (!response.ok) {
      let detail = `请求失败（HTTP ${response.status}）`;
      try {
        const body = await response.json();
        if (body && body.detail) {
          detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        }
      } catch {
        /* 非 JSON 响应：保留兜底文案 */
      }
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  const rememberReview = (reviewId) => {
    try {
      if (reviewId) window.localStorage.setItem(STORAGE_KEY, reviewId);
      else window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* 隐私模式下忽略 */
    }
  };

  const recalledReview = () => {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  };

  // ---------- 步骤与视图 ----------

  function setStep(active) {
    dom.steps.forEach((step) => {
      const index = Number(step.dataset.step);
      step.dataset.state = index < active ? "done" : index === active ? "active" : "idle";
    });
  }

  function showStage(name, activeStep) {
    Object.entries(dom.states).forEach(([key, node]) => {
      node.hidden = key !== name;
    });
    setStep(activeStep);
  }

  function render() {
    const review = state.review;
    if (!review) {
      showStage("empty", 1);
      return;
    }
    if (review.awaiting_human) {
      renderApproval(review);
      showStage("approval", 3);
      return;
    }
    if (review.report) {
      renderReport(review);
      showStage("report", 4);
      return;
    }
    if (review.status === "running") {
      showStage("working", 2);
      schedulePoll();
      return;
    }
    renderFailure(review);
    showStage("report", 2);
  }

  function setWorking(detail) {
    dom.workingDetail.textContent = detail;
    showStage("working", 2);
  }

  // ---------- 健康检查 ----------

  async function checkHealth() {
    try {
      const health = await api("/health");
      dom.apiStatus.dataset.state = "online";
      dom.apiStatusText.textContent = `API 在线 · v${health.version}`;
    } catch {
      dom.apiStatus.dataset.state = "offline";
      dom.apiStatusText.textContent = "API 离线";
    }
  }

  // ---------- 上传 ----------

  function setFile(file) {
    if (!file) return;
    const suffix = `.${(file.name.split(".").pop() || "").toLowerCase()}`;
    if (!ALLOWED.has(suffix)) {
      toast("不支持该文件类型，请使用 TXT / MD / PDF / DOCX", "error");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      toast(`文件超过 ${MAX_UPLOAD_MB} MB 上限`, "error");
      return;
    }
    if (file.size === 0) {
      toast("文件为空，请重新选择", "error");
      return;
    }
    state.file = file;
    dom.fileName.textContent = file.name;
    dom.fileSize.textContent = `${formatBytes(file.size)} · ${suffix.slice(1).toUpperCase()}`;
    dom.fileIcon.textContent = suffix === ".pdf" ? "PDF" : suffix === ".docx" ? "DOC" : "TXT";
    dom.fileChip.hidden = false;
    dom.startButton.disabled = false;
  }

  function clearFile() {
    state.file = null;
    dom.fileInput.value = "";
    dom.fileChip.hidden = true;
    dom.startButton.disabled = true;
  }

  async function startReview() {
    if (!state.file || state.busy) return;
    state.busy = true;
    dom.startButton.disabled = true;
    dom.startButton.textContent = "正在提交…";

    const form = new FormData();
    form.append("file", state.file, state.file.name);

    try {
      const review = await api(REVIEWS, { method: "POST", body: form });
      state.review = review;
      rememberReview(review.review_id);
      dom.resetButton.hidden = false;
      setWorking("解析文档 → 切分条款 → 抽取要素 → 规则判级");
      render();
    } catch (error) {
      toast(error.message || "审查启动失败", "error");
    } finally {
      state.busy = false;
      dom.startButton.disabled = !state.file;
      dom.startButton.textContent = "开始审查";
    }
  }

  // ---------- 轮询 ----------

  function schedulePoll() {
    clearPoll();
    let tries = 0;
    const tick = async () => {
      tries += 1;
      if (tries > POLL_MAX_TRIES) {
        toast("审查耗时较长，请稍后点击“刷新状态”", "error");
        return;
      }
      try {
        const review = await api(`${REVIEWS}/${state.review.review_id}`);
        state.review = review;
        render();
      } catch (error) {
        if (error.status === 404) {
          toast("审查记录已失效，请重新上传", "error");
          resetView();
          return;
        }
        state.pollTimer = window.setTimeout(tick, POLL_INTERVAL_MS * 2);
      }
    };
    state.pollTimer = window.setTimeout(tick, POLL_INTERVAL_MS);
  }

  function clearPoll() {
    if (state.pollTimer) {
      window.clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }
  }

  // ---------- 公共片段 ----------

  function findingsBlock(findings, { openRed = true, showExplanation = false } = {}) {
    if (!findings || findings.length === 0) {
      return `<div class="success-state"><span aria-hidden="true">✓</span>规则执行完成，未命中任何风险规则（不代表没有风险）。</div>`;
    }
    return `<div class="findings">${findings.map((finding) => renderFinding(finding, openRed, showExplanation)).join("")}</div>`;
  }

  function renderFinding(finding, open, showExplanation) {
    const level = finding.risk_level === "red" ? "red" : "yellow";
    const openAttr = open && level === "red" ? " open" : "";
    // 审批载荷与报告载荷字段不同：报告里的风险条目没有 title / quotes
    const title = finding.title ? ` · ${esc(finding.title)}` : "";
    const chips = (finding.clause_ids || [])
      .map((id) => `<span class="chip">${esc(id)}</span>`)
      .join("");
    const quotes = (finding.quotes || [])
      .map((quote) => `<blockquote class="quote">${esc(quote)}</blockquote>`)
      .join("");
    const citations = (finding.citations || []).length
      ? `<p class="meta-line"><span class="label">原文依据</span>${esc((finding.citations || []).join("；"))}</p>`
      : "";

    let explanation = "";
    if (showExplanation && finding.explanation_summary) {
      const source = { llm: "模型", rule: "规则兜底", none: "无" }[finding.explanation_source] || "规则兜底";
      const quote = finding.explanation_quote
        ? `<blockquote class="quote">${esc(finding.explanation_quote)}</blockquote>`
        : "";
      const cite = finding.explanation_citation
        ? `<p class="meta-line">解释依据：${esc(finding.explanation_citation)}</p>`
        : "";
      explanation = `<p><span class="label">解释（${source}）</span>${esc(finding.explanation_summary)}</p>${quote}${cite}`;
    }

    const knowledge = (finding.knowledge_citations || []).length
      ? `<div class="chips">${(finding.knowledge_citations || [])
          .map((item) => `<span class="chip">${esc(item)}</span>`)
          .join("")}</div>`
      : "";

    return `<details class="finding ${level}"${openAttr}>
      <summary>
        <span class="level-badge ${level}">${level === "red" ? "红" : "黄"}</span>
        <span class="finding-title"><code>${esc(finding.rule_id)}</code>${title}</span>
        ${finding.is_system_finding ? '<span class="tag">系统</span>' : '<span class="tag">合同</span>'}
        <span class="caret" aria-hidden="true">›</span>
      </summary>
      <div class="finding-body">
        <p><span class="label">规则理由</span>${esc(finding.reason)}</p>
        ${finding.suggestion ? `<p><span class="label">建议</span>${esc(finding.suggestion)}</p>` : ""}
        ${chips ? `<div class="chips">${chips}</div>` : ""}
        ${quotes}
        ${citations}
        ${explanation}
        ${knowledge ? `<p class="meta-line"><span class="label">知识引用</span></p>${knowledge}` : ""}
      </div>
    </details>`;
  }

  function warningsBlock(review) {
    const warnings = review.warnings || [];
    const errors = review.errors || [];
    if (warnings.length === 0 && errors.length === 0) return "";
    return `<details class="panel">
      <summary>提示与错误（${warnings.length + errors.length}）</summary>
      <div class="panel-body">
        ${errors.length ? `<ul class="verify-list">${errors.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}
        ${warnings.length ? `<ul class="verify-list">${warnings.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>` : ""}
      </div>
    </details>`;
  }

  // ---------- 审批视图 ----------

  function renderApproval(review) {
    const approval = review.approval;
    if (!approval) {
      dom.states.approval.innerHTML = `<div class="card"><div class="banner warn">
        <span class="banner-icon" aria-hidden="true">!</span>
        <div><h2>未取到审批载荷</h2><p>请点击“刷新状态”重试。</p></div>
      </div></div>`;
      return;
    }

    const findings = approval.findings || [];
    const truncated = approval.truncated
      ? `<p class="meta-line">另有 ${approval.truncated} 条红色风险未展示（单页上限 ${findings.length} 条）。</p>`
      : "";

    dom.states.approval.innerHTML = `<div class="card">
      <div class="banner danger">
        <span class="banner-icon" aria-hidden="true">!</span>
        <div>
          <h2>检测到 ${approval.findings_total} 条红色风险，流程已暂停</h2>
          <p>${esc(approval.instructions)}</p>
        </div>
      </div>

      <div class="metrics">
        <div class="metric"><span>总体等级</span><strong class="level ${esc(review.overall_level)}">${esc(LEVEL_LABELS[review.overall_level] || review.overall_level)}</strong></div>
        <div class="metric"><span>红色风险</span><strong>${approval.findings_total}</strong></div>
        <div class="metric"><span>抽取状态</span><strong>${esc(EXTRACTION_LABELS[review.extraction_status] || review.extraction_status)}</strong></div>
        <div class="metric"><span>当前状态</span><strong>等待人工确认</strong></div>
      </div>

      ${warningsBlock(review)}

      <div class="section-head">
        <h3>红色风险清单</h3>
        <span class="muted">${esc(approval.source_filename || review.source_filename)}</span>
      </div>
      ${findingsBlock(findings, { openRed: true })}
      ${truncated}

      ${approval.to_verify && approval.to_verify.length
        ? `<details class="panel">
            <summary>待人工核对（${approval.to_verify.length}）</summary>
            <div class="panel-body"><ul class="verify-list">${approval.to_verify
              .map((item) => `<li>${esc(item)}</li>`)
              .join("")}</ul></div>
          </details>`
        : ""}

      <form class="decision" id="decision-form" novalidate>
        <fieldset>
          <legend>复核结论</legend>
          <div class="segmented">
            <label class="segment">
              <input type="radio" name="action" value="approve" checked />
              <span><strong>批准</strong><small>已人工确认红色风险，继续生成报告</small></span>
            </label>
            <label class="segment">
              <input type="radio" name="action" value="request_changes" />
              <span><strong>要求修改</strong><small>退回业务方修改合同条款</small></span>
            </label>
            <label class="segment">
              <input type="radio" name="action" value="reject" />
              <span><strong>拒绝</strong><small>不接受该合同，记录拒绝原因</small></span>
            </label>
          </div>
        </fieldset>

        <div class="field-row">
          <label class="field">
            <span>复核人 *</span>
            <input id="reviewer" name="reviewer" maxlength="64" autocomplete="name" required />
          </label>
          <label class="field">
            <span>复核意见（可选）</span>
            <textarea id="comment" name="comment" rows="3" maxlength="2000"></textarea>
          </label>
        </div>

        <p class="form-error" id="decision-error" role="alert"></p>

        <div class="form-actions">
          <button class="button primary" type="submit" id="decision-submit">提交复核结论</button>
          <button class="button ghost" type="button" id="timeout-button">标记为超时（未确认）</button>
        </div>
        <p class="fineprint">批准只代表已人工确认红色风险，不改变规则等级；超时结果绝不会是“通过”。</p>
      </form>
    </div>`;

    document.getElementById("decision-form").addEventListener("submit", submitDecision);
    document.getElementById("timeout-button").addEventListener("click", submitTimeout);
  }

  function decisionFromForm() {
    const form = document.getElementById("decision-form");
    const reviewer = form.querySelector("#reviewer").value.trim();
    const comment = form.querySelector("#comment").value.trim();
    const action = form.querySelector('input[name="action"]:checked').value;
    return { action, reviewer, comment: comment || null };
  }

  async function submitDecision(event) {
    event.preventDefault();
    if (state.busy) return;
    const payload = decisionFromForm();
    const errorNode = document.getElementById("decision-error");
    if (!payload.reviewer) {
      errorNode.textContent = "请填写复核人。";
      document.getElementById("reviewer").focus();
      return;
    }
    await sendDecision(payload);
  }

  async function submitTimeout() {
    if (state.busy) return;
    const confirmed = window.confirm(
      "确认无人复核？本次审查将被标记为“未获人工确认”，结果绝不会是通过。",
    );
    if (!confirmed) return;
    await sendDecision({
      action: "timeout",
      reviewer: "web-ui-timeout",
      comment: "前端操作：无人复核，按超时未确认处理。",
    });
  }

  async function sendDecision(payload) {
    state.busy = true;
    const errorNode = document.getElementById("decision-error");
    const buttons = [document.getElementById("decision-submit"), document.getElementById("timeout-button")];
    buttons.forEach((button) => {
      if (button) button.disabled = true;
    });
    if (errorNode) errorNode.textContent = "";
    setWorking("正在恢复流程 → 生成解释 → 输出报告…");

    try {
      const review = await api(`${REVIEWS}/${state.review.review_id}/decisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.review = review;
      render();
      toast("复核结论已提交", "success");
    } catch (error) {
      toast(error.message || "提交失败", "error");
      if (error.status === 404) {
        rememberReview(null);
        resetView();
        return;
      }
      if (error.status === 409) {
        // 状态已变化（例如别处已提交决定）：拉取最新状态再渲染
        try {
          state.review = await api(`${REVIEWS}/${state.review.review_id}`);
        } catch {
          /* 拉取失败时保留当前快照 */
        }
        render();
        return;
      }
      // 网络/服务端错误：回到审批视图，并保留已填写的复核人、意见与结论
      render();
      const reviewer = document.getElementById("reviewer");
      const comment = document.getElementById("comment");
      if (reviewer) reviewer.value = payload.reviewer;
      if (comment) comment.value = payload.comment || "";
      const radio = document.querySelector(
        `input[name="action"][value="${payload.action}"]`,
      );
      if (radio) radio.checked = true;
      const node = document.getElementById("decision-error");
      if (node) node.textContent = error.message || "提交失败";
    } finally {
      state.busy = false;
    }
  }

  // ---------- 报告视图 ----------

  function renderReport(review) {
    const report = review.report;
    const findings = report.findings || [];
    const red = findings.filter((item) => item.risk_level === "red");
    const yellow = findings.filter((item) => item.risk_level === "yellow");
    const level = report.overall_level || "unknown";
    const downloadBase = `${REVIEWS}/${encodeURIComponent(report.review_id)}/report`;
    const fields = Object.entries(report.extracted_fields || {});
    const hitl = report.hitl;

    dom.states.report.innerHTML = `<div class="card">
      <div class="report-head">
        <div>
          <span class="eyebrow">审查报告 · ${esc(report.review_id)}</span>
          <h2>${esc(report.source_filename)}</h2>
          <p class="muted">生成时间 ${esc(formatTime(report.generated_at))} · 状态 ${esc(STATUS_LABELS[report.status] || report.status)}</p>
        </div>
        <div class="report-actions">
          <span class="level-badge big ${esc(level)}">总体：${esc(LEVEL_LABELS[level] || level)}</span>
          <a class="button secondary" href="${downloadBase}?format=json" download>下载 JSON</a>
          <a class="button secondary" href="${downloadBase}?format=markdown" download>下载 Markdown</a>
          <button class="button ghost" type="button" id="new-review">新建审查</button>
        </div>
      </div>

      <p class="summary">${esc(report.summary)}</p>

      <div class="metrics">
        <div class="metric"><span>红色风险</span><strong class="level red">${red.length}</strong></div>
        <div class="metric"><span>黄色风险</span><strong class="level yellow">${yellow.length}</strong></div>
        <div class="metric"><span>待人工核对</span><strong>${(report.to_verify || []).length}</strong></div>
        <div class="metric"><span>解释状态</span><strong>${esc(EXPLANATION_LABELS[report.explanation_status] || report.explanation_status)}</strong></div>
      </div>

      ${warningsBlock(review)}

      <div class="section-head"><h3>风险清单</h3><span class="muted">红 ${red.length} · 黄 ${yellow.length}</span></div>
      ${findingsBlock(findings, { openRed: true, showExplanation: true })}

      ${
        fields.length
          ? `<details class="panel" open>
              <summary>抽取要素（${fields.length} 项）</summary>
              <div class="panel-body">
                <table class="field-table">
                  <tbody>
                    ${fields
                      .map(
                        ([key, value]) => `<tr>
                          <th scope="row">${esc(FIELD_LABELS[key] || key)}<br /><span class="muted">${esc(key)}</span></th>
                          <td>${value === null || value === "" ? '<span class="empty-value">未抽取</span>' : esc(value)}</td>
                        </tr>`,
                      )
                      .join("")}
                  </tbody>
                </table>
              </div>
            </details>`
          : ""
      }

      ${
        (report.to_verify || []).length
          ? `<details class="panel">
              <summary>待人工核对（${report.to_verify.length}）</summary>
              <div class="panel-body"><ul class="verify-list">${report.to_verify
                .map(
                  (item) =>
                    `<li>${item.clause_id ? `<span class="chip">${esc(item.clause_id)}</span> ` : ""}${esc(item.field)}：${esc(item.reason)}</li>`,
                )
                .join("")}</ul></div>
            </details>`
          : ""
      }

      ${
        hitl
          ? `<p class="meta-line" style="margin-top:16px"><span class="label">人工复核</span>${esc(ACTION_LABELS[hitl.action] || hitl.action)}（复核人 ${esc(hitl.reviewer)}${hitl.comment ? `；意见：${esc(hitl.comment)}` : ""}）</p>`
          : ""
      }

      <section class="limitations">
        <h3>限制与免责</h3>
        <ul>${(report.limitations || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </section>

      <div class="report-meta">
        <span>规则引擎 ${esc(report.rule_engine_version)}</span>
        <span>抽取 prompt ${esc(report.prompt_version)}</span>
        <span>解释 prompt ${esc(report.explanation_prompt_version)}</span>
        ${report.model_id ? `<span>抽取模型 ${esc(report.model_id)}</span>` : ""}
        ${report.explanation_model ? `<span>解释模型 ${esc(report.explanation_model)}</span>` : ""}
      </div>
    </div>`;

    const resetButton = document.getElementById("new-review");
    if (resetButton) resetButton.addEventListener("click", resetView);
  }

  function renderFailure(review) {
    const errors = review.errors || [];
    dom.states.report.innerHTML = `<div class="card">
      <div class="banner warn">
        <span class="banner-icon" aria-hidden="true">!</span>
        <div>
          <h2>审查已结束，但没有生成报告</h2>
          <p>${esc(STATUS_LABELS[review.status] || review.status)}：请查看下方错误信息后重试。</p>
        </div>
      </div>
      ${
        errors.length
          ? `<ul class="verify-list" style="margin-top:14px">${errors.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`
          : ""
      }
      <button class="button ghost" type="button" id="new-review">新建审查</button>
    </div>`;
    const resetButton = document.getElementById("new-review");
    if (resetButton) resetButton.addEventListener("click", resetView);
  }

  // ---------- 复位 / 恢复 ----------

  function resetView() {
    clearPoll();
    state.review = null;
    state.busy = false;
    rememberReview(null);
    dom.resetButton.hidden = true;
    clearFile();
    render();
    toast("已清空当前审查，可重新上传合同");
  }

  async function restore() {
    const reviewId = recalledReview();
    if (!reviewId) {
      render();
      return;
    }
    setWorking("正在恢复上次审查…");
    try {
      const review = await api(`${REVIEWS}/${reviewId}`);
      state.review = review;
      dom.resetButton.hidden = false;
      render();
    } catch (error) {
      rememberReview(null);
      if (error.status !== 404) {
        toast(`恢复上次审查失败：${error.message}`, "error");
      }
      render();
    }
  }

  // ---------- 事件绑定 ----------

  dom.dropzone.addEventListener("click", () => dom.fileInput.click());
  dom.dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      dom.fileInput.click();
    }
  });
  ["dragenter", "dragover"].forEach((type) => {
    dom.dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dom.dropzone.dataset.dragging = "true";
    });
  });
  ["dragleave", "drop"].forEach((type) => {
    dom.dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dom.dropzone.dataset.dragging = "false";
    });
  });
  dom.dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
    if (file) setFile(file);
  });
  dom.fileInput.addEventListener("change", () => setFile(dom.fileInput.files[0]));
  dom.clearFile.addEventListener("click", clearFile);
  dom.startButton.addEventListener("click", startReview);
  dom.resetButton.addEventListener("click", resetView);

  // ---------- 启动 ----------

  checkHealth();
  window.setInterval(checkHealth, 30000);
  restore();
})();
