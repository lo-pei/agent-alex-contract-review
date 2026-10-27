"""Streamlit 界面：上传合同 → 审查 → 人工确认 → 下载报告。

角色：本地演示与人工复核入口（ADR-009）。
依赖：`app/review_service.py`、`app/services/checkpointer.py`、`app/services/pending_store.py`、
`app/report_markdown.py`。
约束：
- **不在 UI 里拼 `Command(resume=...)`**，一切人工决定走 `ReviewService.resume()`；
- 界面只展示规则结果与已通过质量门的解释，不自行推断等级；
- 超时必须显式点击“标记为超时”，且结果绝不会是“通过”。

启动：`.venv/Scripts/python.exe -m streamlit run app/ui.py`
"""

from __future__ import annotations

import atexit
import json
import uuid
from pathlib import Path

import streamlit as st

from app.config import PROJECT_ROOT, settings
from app.graph import build_graph
from app.report_markdown import render_report_markdown
from app.review_service import ReviewRun, ReviewService, ReviewStateError
from app.schemas import HitlDecision, ReviewReport
from app.services.checkpointer import sqlite_checkpointer
from app.services.pending_store import FilePendingStore

LEVEL_LABELS = {"red": "红色", "yellow": "黄色", "pass": "通过", "unknown": "未知"}
STATUS_LABELS = {
    "approved": "已批准",
    "rejected": "已拒绝",
    "changes_requested": "要求修改",
    "unreviewed_red_risk": "未获人工确认（超时/无效决策）",
    "completed": "审查完成",
    "failed": "审查失败",
    "running": "等待人工确认",
}
ACTION_LABELS = {"approve": "批准", "request_changes": "要求修改", "reject": "拒绝"}
UPLOAD_SUFFIXES = {".txt", ".md", ".markdown", ".pdf", ".docx"}


@st.cache_resource
def get_service() -> ReviewService:
    """进程级单例：SQLite checkpointer + 落盘的 pending 时间戳（跨会话可恢复）。"""
    context = sqlite_checkpointer()
    saver = context.__enter__()
    atexit.register(context.__exit__, None, None, None)
    return ReviewService(
        build_graph(checkpointer=saver),
        pending_store=FilePendingStore(),
    )


def _save_upload(uploaded) -> Path:
    """把上传文件写到 `.data/uploads/<uuid>/<basename>`，并做大小/类型校验。"""
    name = Path(uploaded.name.replace("\\", "/")).name
    suffix = Path(name).suffix.casefold()
    if suffix not in UPLOAD_SUFFIXES:
        raise ValueError(f"不支持的文件类型 {suffix or '(无扩展名)'}；支持 txt/md/pdf/docx")
    content = uploaded.getbuffer()
    limit = settings.max_upload_mb * 1024 * 1024
    if len(content) == 0:
        raise ValueError("文件为空")
    if len(content) > limit:
        raise ValueError(f"文件超过 {settings.max_upload_mb} MB 上限")

    target_dir = Path(settings.upload_dir) / uuid.uuid4().hex
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    target.write_bytes(bytes(content))
    return target


def _run_of(review_id: str) -> ReviewRun | None:
    try:
        return get_service().get(review_id)
    except ReviewStateError as exc:
        st.error(str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - 界面层兜底，避免整页崩溃
        st.error(f"读取审查状态失败：{exc}")
        return None


def _show_header(review_id: str, run: ReviewRun) -> None:
    state = run.state
    if state is None:  # pragma: no cover - 防御性
        return
    columns = st.columns(4)
    columns[0].metric("总体等级", LEVEL_LABELS.get(state.overall_level, state.overall_level))
    columns[1].metric("审查状态", STATUS_LABELS.get(run.status, run.status))
    columns[2].metric("条款数量", len(state.clauses))
    columns[3].metric("抽取状态", state.extraction_status)
    st.caption(
        f"审查编号 `{review_id}` · 文件 `{state.source_filename}` · "
        f"解释状态 `{state.explanation_status}`"
    )
    if state.warnings:
        with st.expander(f"提示（{len(state.warnings)} 条）"):
            for warning in state.warnings:
                st.write(f"- {warning}")
    if state.errors:
        with st.expander(f"错误（{len(state.errors)} 条）"):
            for error in state.errors:
                st.write(f"- {error}")


def _show_approval(run: ReviewRun) -> None:
    payload = run.approval
    if payload is None:  # pragma: no cover - 暂停时必有载荷
        st.warning("未取到审批载荷，请刷新重试。")
        return

    st.error(
        f"检测到 {payload.findings_total} 条红色风险，"
        f"流程已暂停，等待人工确认（尚未生成最终报告）。"
    )
    st.info(payload.instructions)

    for finding in payload.findings:
        tag = "系统" if finding.is_system_finding else "合同"
        with st.expander(f"[{tag}] {finding.rule_id} · {finding.title}", expanded=True):
            st.write(f"**理由**：{finding.reason}")
            if finding.suggestion:
                st.write(f"**建议**：{finding.suggestion}")
            if finding.clause_ids:
                st.write("**相关条款**：" + "、".join(finding.clause_ids))
            if finding.citations:
                st.write("**原文依据**：" + "；".join(finding.citations))
            for quote in finding.quotes:
                st.code(quote, language=None)
    if payload.truncated:
        st.caption(
            f"另有 {payload.truncated} 条红色风险未展示（上限 {len(payload.findings)} 条）。"
        )
    if payload.to_verify:
        with st.expander("待人工核对"):
            for item in payload.to_verify:
                st.write(f"- {item}")

    with st.form("decision"):
        action_label = st.radio(
            "复核结论",
            ("批准", "要求修改", "拒绝"),
            horizontal=True,
            help="批准只代表已人工确认红色风险，不改变规则等级。",
        )
        reviewer = st.text_input("复核人", value="")
        comment = st.text_area("复核意见（可选）", value="")
        submitted = st.form_submit_button("提交复核结论", type="primary")

    if submitted:
        action = {"批准": "approve", "要求修改": "request_changes", "拒绝": "reject"}[action_label]
        if not reviewer.strip():
            st.error("请填写复核人。")
            return
        decision = HitlDecision(
            action=action,
            reviewer=reviewer.strip(),
            comment=comment.strip() or None,
        )
        try:
            run = get_service().resume(run.review_id, decision)
        except ReviewStateError as exc:
            st.error(str(exc))
            return
        st.session_state["run"] = run
        st.rerun()

    st.divider()
    st.caption("若确认无人复核，可将本次审查标记为超时（结果绝不会是“通过”）。")
    if st.button("标记为超时（未确认）"):
        decision = HitlDecision(
            action="timeout",
            reviewer="ui-timeout",
            comment="界面操作：无人复核，按超时未确认处理。",
        )
        st.session_state["run"] = get_service().resume(run.review_id, decision)
        st.rerun()


def _show_report(report: ReviewReport) -> None:
    st.subheader("审查报告")
    st.write(report.summary)

    if report.findings:
        for finding in report.findings:
            tag = "系统" if finding.is_system_finding else "合同"
            title = (
                f"[{LEVEL_LABELS.get(finding.risk_level, finding.risk_level)}][{tag}] "
                f"{finding.rule_id}"
            )
            with st.expander(title, expanded=finding.risk_level == "red"):
                st.write(f"**规则理由**：{finding.reason}")
                if finding.citations:
                    st.write("**原文依据**：" + "；".join(finding.citations))
                if finding.explanation_summary:
                    source = "模型" if finding.explanation_source == "llm" else "规则"
                    st.write(f"**解释（{source}）**：{finding.explanation_summary}")
                    if finding.explanation_citation:
                        st.caption(f"解释依据：{finding.explanation_citation}")
                else:
                    st.caption("本风险未提供模型解释。")
                if finding.knowledge_citations:
                    st.write("**知识引用**：" + "；".join(finding.knowledge_citations))
                if finding.suggestion:
                    st.write(f"**建议**：{finding.suggestion}")
    else:
        st.success("规则执行完成，未命中任何风险规则（不代表没有风险，见限制）。")

    if report.extracted_fields:
        st.subheader("抽取要素")
        st.dataframe(
            [
                {"字段": field, "值": "" if value is None else str(value)}
                for field, value in report.extracted_fields.items()
            ],
            use_container_width=True,
            hide_index=True,
        )

    if report.to_verify:
        with st.expander(f"待人工核对（{len(report.to_verify)} 项）"):
            for item in report.to_verify:
                where = f"[{item.clause_id}] " if item.clause_id else ""
                st.write(f"- {where}{item.field}：{item.reason}")

    if report.hitl:
        st.caption(
            f"人工复核：{ACTION_LABELS.get(report.hitl.action, report.hitl.action)}"
            f"（复核人 {report.hitl.reviewer}）"
        )

    st.subheader("限制与免责")
    for limitation in report.limitations:
        st.write(f"- {limitation}")

    st.caption(
        f"规则引擎 {report.rule_engine_version} · 抽取 prompt {report.prompt_version} · "
        f"解释 prompt {report.explanation_prompt_version}"
    )

    as_json = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
    columns = st.columns(2)
    columns[0].download_button(
        "下载 JSON 报告",
        data=as_json,
        file_name=f"{report.review_id}-report.json",
        mime="application/json",
    )
    columns[1].download_button(
        "下载 Markdown 报告",
        data=render_report_markdown(report),
        file_name=f"{report.review_id}-report.md",
        mime="text/markdown",
    )


def main() -> None:
    st.set_page_config(page_title="Agent Alex · 外贸合同智审助手", layout="wide")
    st.title("Agent Alex · 外贸合同智审助手")
    st.caption(
        "上传国际货物销售合同 → Python 规则判级 → 红色风险人工确认 → 模型解释 → 可追溯报告"
    )

    with st.sidebar:
        st.header("运行配置")
        model_status = "已配置" if settings.llm_api_key.strip() else "未配置（解释回退规则理由）"
        st.write(f"- 模型：{model_status}")
        st.write(f"- RAG：{'开启' if settings.rag_enabled else '关闭'}")
        st.write(f"- 超时：{settings.hitl_timeout_minutes} 分钟（超时不视为通过）")
        st.write(f"- 上传上限：{settings.max_upload_mb} MB")
        st.caption(f"数据目录：{PROJECT_ROOT / '.data'}")
        if st.button("清空当前审查"):
            st.session_state.pop("run", None)
            st.session_state.pop("review_id", None)
            st.rerun()

    service = get_service()
    run: ReviewRun | None = st.session_state.get("run")
    review_id: str | None = st.session_state.get("review_id")

    uploaded = st.file_uploader(
        "上传合同（txt / md / 文本型 pdf / docx）",
        type=["txt", "md", "markdown", "pdf", "docx"],
    )
    if uploaded is not None and run is None:
        if st.button("开始审查", type="primary"):
            try:
                path = _save_upload(uploaded)
                new_run = service.start(path)
            except (ValueError, ReviewStateError) as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - 界面层兜底
                st.error(f"审查启动失败：{exc}")
            else:
                st.session_state["run"] = new_run
                st.session_state["review_id"] = new_run.review_id
                st.rerun()

    if run is None:
        st.info("请上传合同后点击“开始审查”。红色风险会暂停并等待人工确认。")
        return

    review_id = run.review_id
    st.session_state["review_id"] = review_id

    if st.button("刷新状态"):
        refreshed = _run_of(review_id)
        if refreshed is not None:
            st.session_state["run"] = refreshed
            st.rerun()

    if run.awaiting_human:
        _show_header(review_id, run)
        _show_approval(run)
        return

    _show_header(review_id, run)
    if run.report is None:
        st.warning("审查已结束但没有报告，请查看错误信息。")
        return
    _show_report(run.report)


if __name__ == "__main__":  # pragma: no cover - Streamlit 入口
    main()
