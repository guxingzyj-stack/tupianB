"""intent (Claude 给的修图指令字符串) -> 参数化操作序列。

映射表严格对应 PRD §6.2。intent 可能含多个关键词, 命中的操作会合并;
同类型操作去重时取强度较大的那个。一个都没命中 -> 通用轻度增强。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Operation:
    type: str
    value: float = 0.0
    name: Optional[str] = None  # 预留: LUT 名等
    params: dict = field(default_factory=dict)


# 关键词 -> 操作。按 PRD §6.2:
#   提亮/更亮      -> 曲线提亮暗部、保护高光
#   鲜艳/色彩增强  -> 饱和度 + vibrance
#   通透/对比      -> 局部对比 + 清晰度
#   暖色          -> 色温暖化
#   天空更蓝       -> 蓝色局部加饱和 + 提亮
#   主体更清楚     -> 主体(暗部)局部增强 + 清晰度
#   暖色草原/纪录片感 -> 暖调 + 中等饱和 + 对比
#   柔和          -> 降对比 + 轻磨皮
_KEYWORD_OPS: list[tuple[str, list[Operation]]] = [
    ("暖色草原", [Operation("warmth", 0.20), Operation("saturation", 0.12), Operation("contrast", 0.08)]),
    ("纪录片感", [Operation("warmth", 0.12), Operation("contrast", 0.14), Operation("saturation", 0.06)]),
    ("天空更蓝", [Operation("sky_blue", 0.30)]),
    ("主体更清楚", [Operation("subject_boost", 0.20), Operation("clarity", 0.12)]),
    ("主体更亮", [Operation("subject_boost", 0.20)]),
    ("色彩增强", [Operation("saturation", 0.22), Operation("vibrance", 0.15)]),
    ("更鲜艳", [Operation("saturation", 0.22), Operation("vibrance", 0.15)]),
    ("鲜艳", [Operation("saturation", 0.20), Operation("vibrance", 0.12)]),
    ("饱和", [Operation("saturation", 0.18)]),
    ("更明亮", [Operation("brightness", 0.16), Operation("contrast", 0.04)]),
    ("更亮", [Operation("brightness", 0.20)]),
    ("提亮", [Operation("brightness", 0.15)]),
    ("脸更亮", [Operation("subject_boost", 0.22)]),
    ("通透", [Operation("contrast", 0.12), Operation("clarity", 0.18)]),
    ("清晰", [Operation("clarity", 0.18)]),
    ("对比", [Operation("contrast", 0.16)]),
    ("暖色", [Operation("warmth", 0.18)]),
    ("暖调", [Operation("warmth", 0.16)]),
    ("更柔和", [Operation("soft", 0.25)]),
    ("柔光", [Operation("soft", 0.22)]),
    ("柔和", [Operation("soft", 0.25)]),
    ("降低对比", [Operation("soft", 0.20)]),
    ("降对比", [Operation("soft", 0.20)]),
]

# 一个关键词都没命中时的通用轻度增强
_DEFAULT_OPS = [
    Operation("brightness", 0.08),
    Operation("saturation", 0.10),
    Operation("contrast", 0.06),
]


def parse_intent(intent: str) -> list[Operation]:
    """把 intent 字符串解析成操作序列。"""
    intent = intent or ""
    collected: list[Operation] = []
    for keyword, ops in _KEYWORD_OPS:
        if keyword in intent:
            collected.extend(ops)

    if not collected:
        return [Operation(o.type, o.value, o.name, dict(o.params)) for o in _DEFAULT_OPS]

    # 同类型去重: 取强度 (|value|) 较大的
    best: dict[str, Operation] = {}
    for op in collected:
        cur = best.get(op.type)
        if cur is None or abs(op.value) > abs(cur.value):
            best[op.type] = op
    return list(best.values())
