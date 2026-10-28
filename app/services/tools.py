"""只读工具层：本地工具 + MCP（stdio）客户端（ADR-015）。

角色：给“专家 / 解释”节点提供**可审计的工具调用**——检索知识、定位条款、回读字段。
依赖：标准库（`json` / `subprocess` / `threading`）+ `app/services/rag.py`、`app/schemas.py`。
约束：
- **只读**：工具只能读合同与知识库，不能改合同、不能写库、不能改等级；
- **可审计**：每次调用都产出 `ToolCallRecord`（含参数、耗时、成败），失败也留痕；
- **可离线**：本地工具零网络；MCP 只允许在 `.env` 里配置的 stdio 命令（`shell=False`），
  不访问网络、不执行用户上传包里的脚本；
- **有界**：单次调用参数截断、结果摘要截断、MCP 读取单行上限、超时即杀进程；
- 任何工具异常都不能让图崩溃：`ToolRegistry.call` 统一转成 `ok=False` 的轨迹。

MCP 说明：这里实现的是 MCP 的 **stdio / JSON-RPC 2.0** 子集
（`initialize` → `tools/list` → `tools/call`），不引入 `mcp` SDK，保持零新依赖。
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, settings
from app.schemas import Clause, ContractReviewState, Evidence, ToolCallRecord, format_citation
from app.services.rag import KnowledgeBase, KnowledgeConfigError, load_knowledge_base

MAX_TOOL_ARG_CHARS = 200
MAX_TOOL_SUMMARY_CHARS = 400
MAX_MCP_LINE_CHARS = 1_000_000
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_TOOL_PREFIX = "mcp:"
MCP_READY_TIMEOUT_SECONDS = 15.0

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")


class ToolError(RuntimeError):
    """工具配置/协议错误；调用方应降级成轨迹里的 `ok=False`，不让图崩溃。"""


@dataclass(frozen=True)
class ToolSpec:
    """工具契约：给 LLM 看的说明 + 参数名（用于校验与轨迹）。"""

    name: str
    title: str
    description: str
    arguments: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolOutput:
    """工具执行结果（只用于说明与引用，不参与判级）。"""

    summary: str
    citations: tuple[str, ...] = ()


Handler = Callable[[dict[str, Any]], ToolOutput]


@dataclass
class _Entry:
    spec: ToolSpec
    handler: Handler


class ToolRegistry:
    """本地工具 + MCP 工具的集合；`call` 永不抛异常。"""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._mcp: list[McpStdioClient] = []

    # ---------- 注册 ----------

    def register(self, spec: ToolSpec, handler: Handler) -> None:
        if spec.name in self._entries:
            raise ToolError(f"工具名重复：{spec.name}")
        self._entries[spec.name] = _Entry(spec, handler)

    def _register_mcp(self, client: McpStdioClient) -> None:
        for tool in client.list_tools():
            name = str(tool.get("name") or "").strip()
            if not name:
                continue
            spec = ToolSpec(
                name=f"{MCP_TOOL_PREFIX}{client.name}/{name}",
                title=f"MCP · {client.name} · {tool.get('title') or name}",
                description=str(tool.get("description") or "MCP 工具")[:300],
                arguments=tuple((tool.get("inputSchema") or {}).get("properties", {}).keys()),
            )
            self.register(
                spec,
                lambda arguments, client=client, name=name: _mcp_output(
                    client, name, arguments
                ),
            )
        self._mcp.append(client)

    # ---------- 查询 ----------

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def specs(self) -> list[ToolSpec]:
        return [entry.spec for entry in self._entries.values()]

    def describe(self) -> str:
        """给提示词用的工具清单（一行一个）。"""
        if not self._entries:
            return "（本次没有可用工具）"
        lines = []
        for entry in self._entries.values():
            args = ", ".join(entry.spec.arguments) or "无参数"
            lines.append(f"- {entry.spec.name}({args})：{entry.spec.description}")
        return "\n".join(lines)

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> ToolCallRecord:
        started = time.perf_counter()
        safe_args = _clean_arguments(arguments)
        entry = self._entries.get(name)
        if entry is None:
            return ToolCallRecord(
                name=name,
                ok=False,
                arguments=safe_args,
                error=f"未注册的工具：{name}",
                elapsed_ms=_elapsed_ms(started),
            )
        try:
            output = entry.handler(safe_args)
        except Exception as exc:  # noqa: BLE001 - 工具失败只影响本次调用
            return ToolCallRecord(
                name=name,
                title=entry.spec.title,
                ok=False,
                arguments=safe_args,
                error=f"{type(exc).__name__}: {exc}"[:MAX_TOOL_SUMMARY_CHARS],
                elapsed_ms=_elapsed_ms(started),
            )
        return ToolCallRecord(
            name=name,
            title=entry.spec.title,
            ok=True,
            arguments=safe_args,
            summary=_truncate(output.summary, MAX_TOOL_SUMMARY_CHARS),
            citations=list(output.citations),
            elapsed_ms=_elapsed_ms(started),
        )

    def close(self) -> None:
        for client in self._mcp:
            client.close()
        self._mcp.clear()


# ---------------------------------------------------------------- 本地工具


def build_tool_registry(
    state: ContractReviewState,
    *,
    mcp_servers: str | None = None,
    timeout_seconds: float | None = None,
) -> ToolRegistry:
    """按当前审查状态构建工具集合；MCP 只在配置了服务器时才连接。"""
    registry = ToolRegistry()
    _register_local(registry, state)

    raw = settings.mcp_servers if mcp_servers is None else mcp_servers
    for config in parse_mcp_servers(raw):
        client = McpStdioClient(
            config,
            timeout_seconds=settings.mcp_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds,
        )
        try:
            client.start()
            registry._register_mcp(client)  # noqa: SLF001 - 同模块内部装配
        except Exception as exc:  # noqa: BLE001 - 单个 MCP 服务器不可用不拖垮审查
            client.close()
            registry.register(
                ToolSpec(
                    name=f"{MCP_TOOL_PREFIX}{config.name}/unavailable",
                    title=f"MCP · {config.name}（不可用）",
                    description=f"MCP 服务器不可用：{type(exc).__name__}",
                ),
                _unavailable(f"MCP 服务器 {config.name} 不可用：{exc}"),
            )
    return registry


def _unavailable(message: str) -> Handler:
    """注册一个“调用即失败”的占位工具，让模型/用户看到具体原因。"""

    def handler(_arguments: dict[str, Any]) -> ToolOutput:
        raise ToolError(message)

    return handler


def _register_local(registry: ToolRegistry, state: ContractReviewState) -> None:
    registry.register(
        ToolSpec(
            name="contract_outline",
            title="合同条款目录",
            description="列出本合同切分出的条款编号与标题，用于确认“去哪一条找”。",
        ),
        lambda _arguments: _outline(state),
    )
    registry.register(
        ToolSpec(
            name="find_clause",
            title="按关键词找条款",
            description="按关键词在条款标题与正文中查找，返回命中的条款编号、标题与片段。",
            arguments=("keyword",),
        ),
        lambda arguments: _find_clause(state, str(arguments.get("keyword") or "")),
    )
    registry.register(
        ToolSpec(
            name="read_field",
            title="回读已抽取字段",
            description=(
                "读取某个已抽取契约要素（如 payment_terms / incoterms）的取值与原文位置；"
                "只能读，不能改。"
            ),
            arguments=("field",),
        ),
        lambda arguments: _read_field(state, str(arguments.get("field") or "")),
    )
    registry.register(
        ToolSpec(
            name="search_knowledge",
            title="检索知识库",
            description=(
                "在本地知识库（法规/惯例/内部政策）中检索，返回可引用的 source_id#section。"
            ),
            arguments=("query",),
        ),
        lambda arguments: _search_knowledge(str(arguments.get("query") or "")),
    )


def _outline(state: ContractReviewState) -> ToolOutput:
    if not state.clauses:
        raise ToolError("本合同没有切分出条款")
    lines = [
        f"[{clause.clause_id}] {clause.title or '（无标题）'}（p{clause.page}）"
        for clause in state.clauses[:40]
    ]
    return ToolOutput(summary="\n".join(lines))


def _find_clause(state: ContractReviewState, keyword: str) -> ToolOutput:
    term = keyword.strip()
    if not term:
        raise ToolError("keyword 不能为空")
    matched = [
        clause
        for clause in state.clauses
        if term.casefold() in f"{clause.title}\n{clause.text}".casefold()
    ]
    if not matched:
        return ToolOutput(summary=f"没有条款命中关键词：{term}")
    blocks = []
    citations = []
    for clause in matched[:3]:
        snippet = _snippet(clause, term)
        blocks.append(f"[{clause.clause_id}] {clause.title or '（无标题）'}\n{snippet}")
        citations.append(_clause_citation(state, clause))
    return ToolOutput(summary="\n\n".join(blocks), citations=tuple(citations))


def _read_field(state: ContractReviewState, field_name: str) -> ToolOutput:
    name = field_name.strip()
    if not name:
        raise ToolError("field 不能为空")
    if name not in state.facts:
        available = "、".join(sorted(state.facts)) or "（本次没有已确认字段）"
        raise ToolError(f"没有字段 {name}；可用字段：{available}")
    value = state.facts[name]
    evidence = state.fact_evidence.get(name)
    citation = format_citation(state.source_filename, evidence) if evidence else "无原文证据"
    return ToolOutput(summary=f"{name} = {value}\n原文位置：{citation}", citations=(citation,))


def _search_knowledge(query: str) -> ToolOutput:
    term = query.strip()
    if not term:
        raise ToolError("query 不能为空")
    if not settings.rag_enabled:
        raise ToolError("知识库未启用（RAG_ENABLED=false），本工具不返回任何内容")
    try:
        knowledge: KnowledgeBase = load_knowledge_base(settings.rag_knowledge_dir, enabled=True)
    except KnowledgeConfigError as exc:
        raise ToolError(f"知识库不可用：{exc}") from exc
    hits = knowledge.search(
        term, top_k=settings.rag_top_k, min_score=settings.rag_min_score
    )
    if not hits:
        return ToolOutput(summary=f"知识库没有命中：{term}")
    blocks = [
        f"[{hit.citation}] {hit.title} / {hit.heading}\n{hit.text[:300]}" for hit in hits
    ]
    return ToolOutput(
        summary="\n\n".join(blocks), citations=tuple(hit.citation for hit in hits)
    )


def _snippet(clause: Clause, term: str) -> str:
    """关键词附近的片段（找不到精确位置就取条款开头）。"""
    index = clause.text.casefold().find(term.casefold())
    start = max(0, index - 60) if index >= 0 else 0
    return clause.text[start : start + 240]


def _clause_citation(state: ContractReviewState, clause: Clause) -> str:
    return format_citation(
        state.source_filename,
        Evidence(
            quote=clause.text[:80],
            start=clause.start,
            end=clause.end,
            page=clause.page,
            clause_id=clause.clause_id,
            grounded=True,
        ),
    )


# ---------------------------------------------------------------- MCP stdio


@dataclass(frozen=True)
class McpServerConfig:
    """一个 MCP stdio 服务器（只来自 `.env` 运维配置，不接受用户输入）。"""

    name: str
    command: str
    args: tuple[str, ...] = ()


def parse_mcp_servers(raw: str) -> tuple[McpServerConfig, ...]:
    """解析 `MCP_SERVERS` JSON；格式错误直接抛出（启动期配置问题要暴露）。"""
    text = (raw or "").strip()
    if not text:
        return ()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"MCP_SERVERS 不是合法 JSON：{exc}") from exc
    if not isinstance(payload, list):
        raise ToolError("MCP_SERVERS 必须是 JSON 数组")

    configs: list[McpServerConfig] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ToolError("MCP_SERVERS 的每一项必须是对象")
        name = str(item.get("name") or "").strip()
        command = str(item.get("command") or "").strip()
        args = item.get("args") or []
        if not _NAME_RE.match(name):
            raise ToolError(f"MCP 服务器名不合法（字母开头、≤32 位）：{name!r}")
        if name in seen:
            raise ToolError(f"MCP 服务器名重复：{name}")
        if not command:
            raise ToolError(f"MCP 服务器 {name} 缺少 command")
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ToolError(f"MCP 服务器 {name} 的 args 必须是字符串数组")
        seen.add(name)
        configs.append(
            McpServerConfig(
                name=name,
                command=_resolve_command(command),
                args=tuple(args),
            )
        )
    return tuple(configs)


def _resolve_command(command: str) -> str:
    """相对路径按项目根解析；`python`/`node` 等可执行名交给 PATH。"""
    candidate = Path(command)
    if candidate.is_absolute():
        return str(candidate)
    if "/" in command or "\\" in command:
        return str(PROJECT_ROOT / candidate)
    return command


class McpStdioClient:
    """MCP stdio 客户端（JSON-RPC 2.0 子集）：只做 initialize / tools/list / tools/call。

    读取放在后台线程，主线程用队列带超时等待；超时或协议错误一律杀进程并抛
    `ToolError`，由 `ToolRegistry.call` 转成 `ok=False` 的轨迹。
    """

    def __init__(self, config: McpServerConfig, *, timeout_seconds: float = 10.0) -> None:
        self._config = config
        self._timeout = max(0.5, float(timeout_seconds))
        self._process: subprocess.Popen[str] | None = None
        self._reader: threading.Thread | None = None
        self._responses: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._lock = threading.Lock()
        self._next_id = 0
        self._tools: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def tools(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._tools)

    def start(self) -> None:
        if self._process is not None:
            return
        try:
            self._process = subprocess.Popen(
                [self._config.command, *self._config.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                shell=False,
            )
        except OSError as exc:
            raise ToolError(f"MCP 服务器 {self.name} 启动失败：{exc}") from exc
        self._reader = threading.Thread(
            target=self._read_loop, name=f"mcp-{self.name}", daemon=True
        )
        self._reader.start()
        self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agent-alex", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict[str, Any]]:
        self.start()
        result = self._request("tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise ToolError(f"MCP 服务器 {self.name} 的 tools/list 返回格式不正确")
        self._tools = [tool for tool in tools if isinstance(tool, dict)]
        return self._tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        self.start()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        parts: list[str] = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(str(item["text"]))
        text = "\n".join(parts).strip()
        if result.get("isError"):
            raise ToolError(f"MCP 工具 {name} 返回错误：{_truncate(text, 200)}")
        return text or f"MCP 工具 {name} 执行成功（无文本结果）"

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:  # noqa: BLE001 - 关闭是尽力而为
            try:
                process.kill()
            except Exception:  # noqa: BLE001
                pass

    # ---------- JSON-RPC ----------

    def _send(self, payload: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise ToolError(f"MCP 服务器 {self.name} 未启动")
        line = json.dumps(payload, ensure_ascii=False)
        if len(line) > MAX_MCP_LINE_CHARS:
            raise ToolError(f"发往 MCP 服务器 {self.name} 的请求过大")
        with self._lock:
            try:
                process.stdin.write(line + "\n")
                process.stdin.flush()
            except (BrokenPipeError, ValueError) as exc:
                raise ToolError(f"MCP 服务器 {self.name} 已断开：{exc}") from exc

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._send(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.close()
                raise ToolError(f"MCP 服务器 {self.name} 响应超时（{method}）")
            try:
                message = self._responses.get(timeout=remaining)
            except queue.Empty:
                self.close()
                raise ToolError(f"MCP 服务器 {self.name} 响应超时（{method}）") from None
            if message is None:
                self.close()
                raise ToolError(f"MCP 服务器 {self.name} 提前退出（{method}）")
            if message.get("id") != request_id:
                continue  # 通知或过期响应，丢弃
            error = message.get("error")
            if isinstance(error, dict):
                raise ToolError(
                    f"MCP 服务器 {self.name} 返回错误：{error.get('message') or error}"
                )
            result = message.get("result")
            return result if isinstance(result, dict) else {}

    def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            self._responses.put(None)
            return
        try:
            for line in process.stdout:
                if len(line) > MAX_MCP_LINE_CHARS:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    self._responses.put(payload)
        finally:
            self._responses.put(None)


def _mcp_output(client: McpStdioClient, name: str, arguments: dict[str, Any]) -> ToolOutput:
    text = client.call_tool(name, arguments)
    return ToolOutput(summary=text)


# ---------------------------------------------------------------- 小工具


def _clean_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """只保留 JSON 标量/短字符串，避免把整段合同塞进轨迹与提示词。"""
    if not isinstance(arguments, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in arguments.items():
        name = str(key)[:40]
        if isinstance(value, (int, float, bool)) or value is None:
            cleaned[name] = value
        else:
            cleaned[name] = _truncate(str(value), MAX_TOOL_ARG_CHARS)
    return cleaned


def _truncate(text: str, limit: int) -> str:
    value = str(text)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
