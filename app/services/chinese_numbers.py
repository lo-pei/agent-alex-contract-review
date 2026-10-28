"""中文条号的数字 ↔ 汉字互转（检索加权与评测 gold 共用一份实现）。

为什么单独成模块：`app/services/rag.py` 需要把用户提问里的“第584条”对到语料的
“第五百八十四条”，`eval/rag_gold.py` 需要把标签 `CC-584` 转成同样的条号。
两处规则必须一致，否则“评测命中”与“线上命中”会对不上。

写法与法律文本对齐：`110 → 一百一十`、`101 → 一百零一`、`1050 → 一千零五十`、`12 → 十二`。
"""

from __future__ import annotations

_DIGITS = "零一二三四五六七八九"
_UNITS = ("", "十", "百", "千")
_DIGIT_VALUES = {char: index for index, char in enumerate(_DIGITS)}
_UNIT_VALUES = {"十": 10, "百": 100, "千": 1000}

#: 支持 1..9999；语料里的条号都在此范围
MAX_NUMBER = 9999


class NumberFormatError(ValueError):
    """既不是 1..9999 的整数，也不是可解析的中文条号。"""


def to_chinese_number(value: int) -> str:
    """整数 → 中文数字（不含“第…条”外壳）。"""
    if not 0 < value <= MAX_NUMBER:
        raise NumberFormatError(f"条号超出可转换范围（1..{MAX_NUMBER}）：{value}")
    digits = str(value)
    text = ""
    pending_zero = False
    for index, char in enumerate(digits):
        digit = int(char)
        position = len(digits) - index - 1
        if digit == 0:
            pending_zero = True
            continue
        if pending_zero and text:
            text += "零"
        pending_zero = False
        text += _DIGITS[digit] + _UNITS[position]
    if text.startswith("一十"):
        text = text[1:]
    return text


def from_chinese_number(text: str) -> int:
    """中文数字 → 整数；不认识的形式抛 `NumberFormatError`，不静默返回 0。"""
    cleaned = text.strip()
    if not cleaned:
        raise NumberFormatError("空字符串不是中文条号")
    if cleaned.isdigit():
        value = int(cleaned)
        if not 0 < value <= MAX_NUMBER:
            raise NumberFormatError(f"条号超出范围：{text!r}")
        return value

    total = 0
    current = 0
    for char in cleaned:
        if char in _DIGIT_VALUES:
            current = _DIGIT_VALUES[char]
            continue
        if char not in _UNIT_VALUES:
            raise NumberFormatError(f"含无法识别的中文数字字符：{text!r}")
        unit = _UNIT_VALUES[char]
        total += (current or 1) * unit
        current = 0
    total += current
    if not 0 < total <= MAX_NUMBER:
        raise NumberFormatError(f"条号超出范围：{text!r}")
    return total
