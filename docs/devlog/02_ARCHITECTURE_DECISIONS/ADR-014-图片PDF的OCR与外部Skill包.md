# ADR-014：图片 PDF 的本地 OCR 与外部 Skill 包 / zip 导入

- 状态：**已接受（已实现）**
- 日期：2026-10-28（界面轮 13）
- 决策人：用户 + Trae AI

## 背景

用户提出三件互相独立、但都触碰“输入边界”的事：

1. **上传上限要扩大**：扫描件/带图合同常常超过 15 MB；
2. **要能识别 PDF 图片**：此前扫描件直接 `IngestError("未检测到文本层")`，用户实际工作中大量合同是扫描件；
3. **Skill 仓库要默认带上外部 Skill 包，并支持 zip 导入**：桌面已有 4 个成熟的合同/信用证 Skill 包（`SKILL.md` + `references/`），希望开箱可用。

硬约束不变（`开发提示词.md` / ADR-003）：**风险等级只能由 Python 规则决定**；LLM/OCR 只提供文本或解释；禁止前端框架、npm 构建、CDN、训练模型、Docker、向量数据库。

## 选项

### A. OCR 方案

| 方案 | 优点 | 缺点 |
|---|---|---|
| A1. 系统 Tesseract（`pytesseract`） | 成熟、语种多 | 需要用户单独装 exe + 语言包；Windows 分发易错；中文包常缺 |
| A2. 云端 OCR API | 识别质量最高 | 违反“离线可跑/不把合同外传”的默认预期，且要 Key、要计费 |
| A3. **本地 ONNX OCR（`rapidocr-onnxruntime`）+ `pypdfium2` 渲染** | 纯 pip、模型随包、离线推理、中英文开箱 | 首次加载模型约数秒；识别会吞空格/串行 |
| A4. 继续拒绝扫描件 | 零成本 | 直接违背用户需求 |

### B. 外部 Skill 包与 zip

| 方案 | 优点 | 缺点 |
|---|---|---|
| B1. 只放桌面路径，运行时读外部目录 | 不复制文件 | 换机器就失效，不是“默认纳入” |
| B2. **复制进 `app/resources/skills/`，启动时读** | 离线、可测试、随仓库分发 | 包内正文受 6000 字附件上限，需标“节选” |
| B3. 允许 zip 里的 `SKILL.md` 自带可执行脚本/工具定义 | 能力更强 | 越过 ADR-003：脚本可改判级/外联，无法保证可追溯 |
| B4. **zip 只读文本 + 固定 5 个已实现工具** | 边界清晰、可测试 | 包内 `allowed-tools` 不能直接生效，只能提示 |

## 决策

- **选 A3**：`app/services/ocr.py` 用 `pypdfium2` 渲染 + `rapidocr-onnxruntime` 识别；**只在无文本层时触发**，最多 20 页，单页失败跳过，依赖缺失/整份无文本才失败；OCR 结果只作为 `raw_text`，**不参与判级**。
- **选 B2 + B4**：4 个包复制到 `app/resources/skills/`，映射为 4 个 `builtin:*`（名称/说明按包内 `SKILL.md` 提炼，原 `SKILL.md` 与 `references/*.md` 作只读附件）；`POST /api/skills/import` 解析 zip（根目录 `SKILL.md` 必填、只收文本、不解压落盘、不执行、`allowed-tools` 只提示）。
- **上传上限**：`MAX_UPLOAD_MB` 15 → 30（单一配置源，前端常量与文案同步）。
- **目录去重**：切分层合并“相邻同主题标题”，展示层再兜底合并旧记录；**只合并文本与意见，等级仍取原规则结果**。
- **完整原文**：接口返回 `contract_text`，左栏可切“原文全文”；默认仍“条款目录”，不改变逐条审查主流程。

明确不选：Tesseract（分发依赖）、云端 OCR（合同外传）、执行 zip 内脚本（越过判级边界）。

## 后果

正面：
- 扫描件/图片 PDF 可进入既有 9 节点流程，无需改判级与 HITL；
- 4 个外部 Skill 开箱可用，用户不必手工建；
- zip 导入方便迁移 Skill 包，且不会给系统引入不可审计的可执行面。

代价与风险：
- OCR 依赖使安装包变大（onnxruntime + 模型），首次识别有数秒加载；
- 英文识别可能吞空格（`SALESCONTRACT`），中文与表格可能串行——报告会写“请人工核对”，仍记 ISSUE-030；
- 外部包正文/长 references 只存前 6000 字（“节选”），且**第三方内容授权未确认**（ISSUE-031），对外分发前需确认；
- `allowed-tools` 不映射，用户需在 Skill 详情里手动勾选项目支持的 5 个工具。

## 证据

- 代码：`app/services/ocr.py`、`app/nodes/ingest.py`、`app/services/skill_catalog.py`、`app/api.py`、`app/resources/skills/`、`app/web/app.js`、`app/web/styles.css`
- 测试：`tests/test_ocr.py`（5）、`tests/test_accounts.py`（内置外部包 + zip 3 项）、`tests/test_segment.py`（重复标题）、`tests/test_clause_review.py`（合并与 `contract_text`）、`tests/test_web.py`（30 MB、zip 弹窗、原文全文）
- 状态：`docs/devlog/00_PROJECT_STATE.md`“界面轮 13”；日志：`03_DEV_LOGS/2026-10-28.md` §23；未决：ISSUE-030 / ISSUE-031
