/* 外贸合同智审助手 · 极简前端
 *
 * 只有三件事：选合同 → 上传审查 → 看风险点。
 * 约束（ADR-003 / ADR-009）：不在浏览器判级、不拼 Command、后端文本一律先转义。
 */
(() => {
  "use strict";

  const MAX_BYTES = 15 * 1024 * 1024;
  const ALLOWED = [".pdf", ".docx", ".txt", ".md", ".markdown"];

  const dom = {
    view: document.getElementById("view"),
    main: document.getElementById("main"),
  };

  const state = {
    file: null,
    reviewId: null,
    busy: false,
    reviewer: "",
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

  /* ---------- 路由 ---------- */

  function navigate(hash) {
    if (location.hash === hash) {
      route();
      return;
    }
    location.hash = hash;
  }

  function route() {
    const hash = location.hash || "#/";
    const match = hash.match(/^#\/(?:review|report)\/([A-Za-z0-9_-]{1,64})$/);
    if (match) {
      loadReview(match[1]);
      return;
    }
    renderUpload();
  }

  async function api(path, options) {
    const response = await fetch(path, options);
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      body = null;
    }
    if (!response.ok) {
      const detail = body && body.detail ? body.detail : "服务返回 " + response.status;
      throw new Error(typeof detail === "string" ? detail : "请求未被接受");
    }
    return body;
  }

  /* ---------- 上传页 ---------- */

  function renderUpload() {
    state.file = null;
    state.busy = false;
    window.scrollTo({ top: 0 });
    dom.view.innerHTML =
      '<section class="upload">' +
      '<h1 class="headline">上传合同，查看风险点</h1>' +
      '<p class="lead">先判断这份文件是不是国际货物销售合同；是合同才会列出需要关注的条款，' +
      "并给出修改建议。</p>" +
      '<div class="drop" id="drop">' +
      '<input id="file-input" type="file" accept=".pdf,.docx,.txt,.md" hidden />' +
      '<div class="drop-body" id="drop-body">' +
      '<svg class="drop-ico" viewBox="0 0 32 32" width="34" height="34" aria-hidden="true">' +
      '<path d="M16 21V8m0 0-5 5m5-5 5 5" fill="none" stroke="currentColor" stroke-width="1.8" ' +
      'stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M6.5 21v3.5A1.5 1.5 0 0 0 8 26h16a1.5 1.5 0 0 0 1.5-1.5V21" fill="none" ' +
      'stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>' +
      '<p class="drop-main">把合同拖到这里</p>' +
      '<button class="btn btn-ghost" type="button" id="pick-file">选择文件</button>' +
      '<p class="drop-hint">支持 PDF、Word、TXT，最大 15 MB</p>' +
      "</div>" +
      "</div>" +
      '<p class="alert" id="form-error" role="alert" hidden></p>' +
      '<button class="btn btn-primary btn-block" type="button" id="start" disabled>开始审查</button>' +
      '<p class="fine">系统只做预审辅助，风险等级由规则给出，不构成法律意见。</p>' +
      "</section>";

    const input = dom.view.querySelector("#file-input");
    const drop = dom.view.querySelector("#drop");

    on("pick-file", "click", () => dom.view.querySelector("#file-input")?.click());

    if (input) {
      input.addEventListener("change", () => {
        if (input.files && input.files[0]) accept(input.files[0]);
      });
    }

    if (drop && input) {
      drop.addEventListener("click", (event) => {
        if (event.target.closest("button") || event.target.closest("input")) return;
        dom.view.querySelector("#file-input")?.click();
      });
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

    on("start", "click", startReview);
  }

  function accept(file) {
    const error = document.getElementById("form-error");
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
    if (error) error.hidden = true;
    state.file = file;

    const body = dom.view.querySelector("#drop-body");
    if (body) {
      body.innerHTML =
        '<p class="picked-name">' +
        esc(file.name) +
        "</p>" +
        '<p class="drop-hint">' +
        esc(humanSize(file.size)) +
        ' · <button class="link" type="button" id="pick-file">换一个</button></p>';
      on("pick-file", "click", () => dom.view.querySelector("#file-input")?.click());
    }
    const start = document.getElementById("start");
    if (start) {
      start.disabled = false;
      start.textContent = "开始审查";
    }
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
    const drop = dom.view.querySelector("#drop-body");
    state.busy = true;
    if (start) {
      start.disabled = true;
      start.innerHTML = spinner() + "正在上传…";
    }
    if (drop) drop.classList.add("is-dim");

    const form = new FormData();
    form.append("file", state.file, state.file.name);

    try {
      const summary = await api("/api/reviews", { method: "POST", body: form });
      state.reviewId = summary.review_id;
      // 只换 hash 不新增历史记录：刷新 / 分享链接时还能回到这次结果
      history.replaceState(null, "", "#/review/" + summary.review_id);
      renderResult(summary);
    } catch (error) {
      state.busy = false;
      if (start) {
        start.disabled = false;
        start.textContent = "重新试一次";
      }
      if (drop) drop.classList.remove("is-dim");
      showFormError(
        error instanceof TypeError
          ? "服务没有响应，请确认服务已启动后重试。"
          : error.message || "上传失败，请重试。",
      );
    }
  }

  /* ---------- 结果页 ---------- */

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
    window.scrollTo({ top: 0 });

    if (review.status === "failed") {
      failMessage(
        (review.errors && review.errors.join("；")) ||
          "合同没能被读取，请确认文件是文本型 PDF / Word / TXT。",
      );
      return;
    }
    if (review.status === "not_contract") {
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
            reviewer: state.reviewer || "本机用户",
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
      (hints.length
        ? '<p class="fine">' + hints.map(esc).join(" ") + "</p>"
        : "") +
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

  window.addEventListener("hashchange", route);
  route();
})();
