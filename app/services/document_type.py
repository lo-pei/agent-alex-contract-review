"""文档类型判定：上传的到底是不是“国际货物销售合同”。

角色：在 `ingest_document` 之后、`segment_clauses` 之前做一次**确定性**闸门，
      避免把论文、法律条文、说明书当成合同去跑规则审查。
依赖：`app/schemas.py`（`DocumentCheck`）；无 LLM、无网络（离线也能判定）。
约束：
- 只看解析后的纯文本，**不判风险、不改等级**；等级仍只由规则引擎产出；
- 判“不是合同”时返回可解释的理由与建议，交给前端直接展示；
- 宁可放过（判为合同继续审查）也不要误杀：只有同时缺少合同身份信号且出现
  学术/法规特征时才拒绝，理由会写进报告；
- 阈值集中放在本文件顶部，便于按真实语料调参（见 `tests/test_document_type.py`）。

判定思路（可解释的三段式）：
1. **身份信号**：合同标题（销售/买卖/采购/供货…合同、Sales Contract…）、合同编号、
   买卖双方（卖方/买方、甲方/乙方、Seller/Buyer…）。三者一个都没有 → 拒绝。
2. **反向信号**：学术论文（摘要、关键词、参考文献、This paper…）与法规条文
   （本法、民法典、Chapter I、General Provisions）。它们出现且没有合同编号/签署语
   → 拒绝。
3. **合同信号打分**：标题 3 分、合同编号 2 分、买卖双方 2 分、编号条款 ≥2 条 2 分、
   贸易要素 ≥3 个 1 分、签署语 1 分；总分 < 4 → 拒绝。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import DocumentCheck

#: 少于这个字符数（去空白）无法判断，直接拒绝
MIN_COMPACT_CHARS = 120

_ZH_TITLE = re.compile(
    r"(销售|买卖|采购|供货|购销|供应|订购|外贸|进出口|货物|设备|产品)"
    r"[^\n，。；]{0,8}?(合同|协议|订单|确认书)"
)
_EN_TITLE = re.compile(
    r"\b(?:sales|purchase|supply|procurement|goods|equipment|export|import)[\s_-]{0,3}"
    r"(?:contract|agreement|order|confirmation)\b",
    re.IGNORECASE,
)
_BARE_TITLE = re.compile(r"^\s*(?:contract|agreement|order)\b", re.IGNORECASE)

#: 抬头只在文件开头的短行里找：正文里的“货物符合合同”不是标题
_TITLE_MAX_LINE = 48
_TITLE_DENY = ("符合合同", "违反合同", "本合同", "该合同", "根据合同", "按照合同", "依据合同")


def _extract_title(text: str) -> str:
    """只从开头十几行里找合同抬头。

    合同抬头通常独立成行（`**SALES CONTRACT**`、`货物销售合同`）；正文里的
    “货物符合合同约定”会误命中，所以限制行长并排除常见句式。
    """
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().strip("*#_>").strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) >= 12:
            break
    for line in lines:
        if len(line) > _TITLE_MAX_LINE or re.search(r"[。；，,;]", line):
            continue
        if any(word in line for word in _TITLE_DENY):
            continue
        match = _ZH_TITLE.search(line) or _EN_TITLE.search(line) or _BARE_TITLE.search(line)
        if match:
            return match.group(0)
    return ""


_ZH_CONTRACT_NO = re.compile(
    r"(合同编号|合同号码|合同号|订单编号|订单号|协议编号)[*\s:：]{0,6}"
    r"([A-Za-z0-9][A-Za-z0-9\-_/.]{1,})"
)
_EN_CONTRACT_NO = re.compile(
    r"\b(?:contract|agreement|order|p\.?o\.?)[\s*_\-]{0,3}(?:no\.?|number|#)[*\s:：]{0,4}"
    r"([A-Za-z0-9][A-Za-z0-9\-_/.]{1,})",
    re.IGNORECASE,
)

_PARTY_PAIRS = (
    ("卖方", "买方"),
    ("供方", "需方"),
    ("供货方", "采购方"),
    ("出口方", "进口方"),
    ("甲方", "乙方"),
)
_EN_PARTY_PAIRS = (
    ("seller", "buyer"),
    ("vendor", "purchaser"),
    ("supplier", "buyer"),
    ("exporter", "importer"),
)

_ARTICLE_ZH = re.compile(r"(?m)^[ \t>#*]*第\s*[一二三四五六七八九十百零0-9]{1,4}\s*条")
_ARTICLE_EN = re.compile(r"(?im)^[ \t>*_]*article\s+\d{1,3}\b")
_NUMBERED = re.compile(r"(?m)^[ \t]{0,4}\d{1,2}(?:\.\d{1,2})?[.、]\s*\S")

_ZH_DEAL = (
    "付款",
    "交货",
    "装运",
    "检验",
    "索赔",
    "仲裁",
    "不可抗力",
    "信用证",
    "单价",
    "总价",
    "数量",
    "质量",
    "包装",
    "保险",
    "违约金",
)
_EN_DEAL = re.compile(
    r"\b(?:payment|delivery|shipment|inspection|claim|arbitration|force\s*majeure|"
    r"letter\s*of\s*credit|l/c|unit\s*price|total\s*(?:amount|price)|quantity|quality|"
    r"packing|insurance|penalt(?:y|ies)|incoterms|fob|cif|cfr)\b",
    re.IGNORECASE,
)

_SIGNATURE = (
    "签字",
    "签署",
    "盖章",
    "签章",
    "授权代表",
    "authorizedsignature",
    "signedby",
    "inwitnesswhereof",
    "insignwhereof",
)

_ZH_ACADEMIC = (
    ("摘要", 4),
    ("关键词", 4),
    ("参考文献", 3),
    ("本文认为", 4),
    ("本文提出", 4),
    ("本文研究", 4),
    ("本文试图", 3),
    ("笔者", 3),
    ("本研究", 4),
    ("研究方法", 2),
    ("实证分析", 2),
    ("文献综述", 3),
    ("doi", 3),
    ("arxiv", 3),
    ("et al", 2),
    ("et al.", 2),
)
_EN_ACADEMIC = (
    ("this paper", 4),
    ("this article", 3),
    ("this study", 4),
    ("abstract", 3),
    ("keywords", 3),
    ("references", 3),
    ("introduction", 2),
    ("methodology", 2),
)

_ZH_LAW = (
    ("本法", 4),
    ("民法典", 4),
    ("本编", 3),
    ("总则", 3),
    ("依照", 1),
    ("本章", 1),
    ("适用本章", 2),
    ("最高人民法院", 3),
)
_EN_LAW = (
    ("civil code", 4),
    ("general provisions", 3),
    ("chapter i", 2),
    ("promulgated", 2),
    ("shall apply", 1),
)


@dataclass(frozen=True)
class _Signals:
    title: str = ""
    contract_no: str = ""
    parties: str = ""
    article_count: int = 0
    numbered_count: int = 0
    deal_terms: int = 0
    signature: bool = False
    academic: int = 0
    academic_hits: tuple[str, ...] = ()
    law: int = 0
    law_hits: tuple[str, ...] = ()

    @property
    def contract_score(self) -> int:
        score = 0
        if self.title:
            score += 3
        if self.contract_no:
            score += 2
        if self.parties:
            score += 2
        if self.article_count >= 2 or self.numbered_count >= 3:
            score += 2
        if self.deal_terms >= 3:
            score += 1
        if self.signature:
            score += 1
        return score


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


def _collect(text: str) -> _Signals:
    lower = text.casefold()
    compact = _compact(text)

    title = _extract_title(text)

    contract_no = ""
    if match := _ZH_CONTRACT_NO.search(text):
        contract_no = match.group(2)
    elif match := _EN_CONTRACT_NO.search(text):
        contract_no = match.group(1)

    parties = ""
    for left, right in _PARTY_PAIRS:
        if left in compact and right in compact:
            parties = f"{left}/{right}"
            break
    if not parties:
        for left, right in _EN_PARTY_PAIRS:
            if re.search(rf"\b{left}\b", lower) and re.search(rf"\b{right}\b", lower):
                parties = f"{left}/{right}"
                break

    article_count = len(_ARTICLE_ZH.findall(text)) + len(_ARTICLE_EN.findall(text))
    numbered_count = len(_NUMBERED.findall(text))

    deal_terms = sum(1 for term in _ZH_DEAL if term in compact) + len(
        {match.group(0).casefold() for match in _EN_DEAL.finditer(text)}
    )

    signature = any(term in compact for term in _SIGNATURE)

    academic_hits: list[str] = []
    academic = 0
    for term, weight in _ZH_ACADEMIC:
        if term in compact:
            academic += weight
            academic_hits.append(term)
    for term, weight in _EN_ACADEMIC:
        if term in lower:
            academic += weight
            academic_hits.append(term)

    law_hits: list[str] = []
    law = 0
    for term, weight in _ZH_LAW:
        if term in compact:
            law += weight
            law_hits.append(term)
    for term, weight in _EN_LAW:
        if term in lower:
            law += weight
            law_hits.append(term)

    return _Signals(
        title=title,
        contract_no=contract_no,
        parties=parties,
        article_count=article_count,
        numbered_count=numbered_count,
        deal_terms=deal_terms,
        signature=signature,
        academic=academic,
        academic_hits=tuple(academic_hits[:5]),
        law=law,
        law_hits=tuple(law_hits[:5]),
    )


def _reject_reasons(signals: _Signals) -> list[str]:
    reasons: list[str] = []
    if signals.academic >= 4 and not (signals.contract_no or signals.signature):
        hits = "、".join(signals.academic_hits) or "学术写作特征"
        reasons.append(f"检测到学术论文特征（{hits}），且没有合同编号或签署语。")
    if signals.law >= 4 and not (signals.contract_no or signals.signature):
        hits = "、".join(signals.law_hits) or "法规条文特征"
        reasons.append(f"检测到法律法规条文特征（{hits}），且没有合同编号或签署语。")
    if not (signals.title or signals.contract_no or signals.parties):
        reasons.append("没有找到合同标题、合同编号或买卖双方信息。")
    if signals.title and not (signals.contract_no or signals.parties):
        reasons.append("虽然出现合同字样，但缺少合同编号与买卖双方。")
    if signals.contract_score < 4 and not reasons:
        reasons.append("合同要素过少：标题、编号、双方、条款结构与交易条件都不充分。")
    return reasons


def classify_document(text: str) -> DocumentCheck:
    """判断一段解析后的文本是不是（货物销售）合同。

    返回 `DocumentCheck`：`is_contract` + 置信度 + 可展示的理由/建议。
    判定纯规则、可复现；不调用模型，也不读取文件名（文件名不可信）。
    """
    compact = _compact(text)
    if len(compact) < MIN_COMPACT_CHARS:
        return DocumentCheck(
            is_contract=False,
            confidence=0.95,
            reasons=[
                f"解析到的正文过短（{len(compact)} 字），无法判断这是一份合同。",
            ],
            hints=[
                "请确认上传的是含正文的合同文件，而不是封面、目录或空白页。",
                "扫描件需要先做 OCR，本工具目前只支持文本型 PDF / DOCX / TXT。",
            ],
        )

    signals = _collect(text)
    identity = bool(signals.title or signals.contract_no or signals.parties)
    academic_block = signals.academic >= 4 and not (signals.contract_no or signals.signature)
    law_block = signals.law >= 4 and not (signals.contract_no or signals.signature)

    # 兜底：合同抬头/编号/双方常被排版吃掉（截掉第一页、纯条款片段、表格转文本）。
    # 只要正文有足够多的编号条款与交易要素，且没有论文/法规特征，就按合同放行——
    # 与文件头注释一致：宁可放过，也不要误杀真实合同。
    rescued = (
        not identity
        and signals.numbered_count >= 6
        and signals.deal_terms >= 4
        and not academic_block
        and not law_block
    )

    is_contract = (
        (identity or rescued)
        and not academic_block
        and not law_block
        and (signals.contract_score >= 4 or rescued)
    )

    if is_contract:
        reasons = [f"识别为合同文件（契约度评分 {signals.contract_score}/11）。"]
        if rescued:
            reasons.append(
                f"未找到合同标题 / 编号 / 买卖双方，但正文有 {signals.numbered_count} 个编号段落、"
                f"命中 {signals.deal_terms} 项交易要素，按合同继续审查（宁可放过，避免误杀）。"
            )
        if signals.title:
            reasons.append(f"合同标题：{signals.title}。")
        if signals.contract_no:
            reasons.append(f"合同编号：{signals.contract_no}。")
        if signals.parties:
            reasons.append(f"买卖双方：{signals.parties}。")
        if signals.article_count:
            reasons.append(f"编号条款：{signals.article_count} 条。")
        elif signals.numbered_count:
            reasons.append(f"编号段落：{signals.numbered_count} 段。")
        reasons.append(f"交易要素命中 {signals.deal_terms} 项。")
        confidence = min(0.99, 0.6 + 0.035 * signals.contract_score)
        return DocumentCheck(
            is_contract=True, confidence=round(confidence, 2), reasons=reasons
        )

    return DocumentCheck(
        is_contract=False,
        confidence=round(min(0.98, 0.6 + 0.03 * max(signals.academic, signals.law)), 2),
        reasons=_reject_reasons(signals) or ["合同要素不足，未通过文档类型校验。"],
        hints=[
            "这里只审查国际货物销售合同（采购/销售/供货合同、订单或确认书）。",
            "文件扩展名（.txt / .docx / .pdf）不代表内容是合同；系统只看解析后的正文。",
            "论文、法律法规、说明书、报价单、问答或审阅意见等材料请走其他流程。",
            "如果确认是合同，请上传包含正文条款的完整版本（文本型 PDF / DOCX / TXT）。",
        ],
    )
