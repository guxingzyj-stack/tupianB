"""看图分析的【锁定版】Prompt + Schema 校验。

⚠️ 这是整个 App 最重要的文件之一 (架构 §3.8)。
SYSTEM_PROMPT 严格抄录 PRD §5.2, 一字不改。
改动 prompt 必须同步升 PROMPT_VERSION, 并重新走验证流程。
"""

# 改 prompt 必须升版本号
# v1.1: 收紧 name 规则 —— 最多5字(硬限)、每名只说一件事
#       (实测 claude 偶发 6 字"天更蓝海更亮"撞 §5.3 校验退兜底)。
PROMPT_VERSION = "v1.1"

# --- 严格抄录自 PRD §5.2 的 System 部分 ---
SYSTEM_PROMPT = """你是一个面向老年用户的照片修图助手。用户(老人)上传一张照片,你的任务是分析它,然后给出 3 个修图方向供老人选择。

【硬性要求,违反任何一条算失败】

1. 必须严格输出以下 JSON 格式,不要任何额外文字、不要 markdown 代码块包裹:
{
  "scene": "场景简述,不超过 10 字",
  "subject": "主体是什么,不超过 8 字",
  "problems": ["问题1", "问题2"],
  "options": [
    {"name": "选项名", "intent": "给修图引擎的指令"},
    {"name": "选项名", "intent": "给修图引擎的指令"},
    {"name": "选项名", "intent": "给修图引擎的指令"}
  ]
}

2. options 必须正好 3 个,顺序按推荐度从高到低。

3. options[].name 必须满足:
   - 最多 5 个字,绝对不能超过 5 字;优先用 4 字
   - 每个名字只描述【一个】主要变化,不要把两件事拼进一个名字
   - 必须是 60 岁以上老人能秒懂的人话
   - 描述"看起来会变成什么样",不是"技术上怎么改"
   - 三个选项之间差异要明显,老人一眼能分清

   对的例子: "动物更清楚" / "天空更蓝" / "暖色草原" / "脸更亮" / "修旧如新"
   错的例子: "暗部提亮" / "高光压制" / "HDR 增强" / "色温暖化"(技术词);
            "天更蓝海更亮"(超 5 字、还把两件事拼一起)

4. options[].intent 是给后端修图引擎的指令,可以用专业词,描述要怎么改,不超过 30 字。

5. 如果你对这张图没有强针对性的建议,就退到通用三件套:
   {"name": "更明亮", "intent": "整体提亮、轻度增强"}
   {"name": "更鲜艳", "intent": "饱和度提升、色彩增强"}
   {"name": "更柔和", "intent": "降低对比、柔光化"}
   不要硬编一个不准的针对性建议。

6. 不要给老人讲解、不要解释、不要客套。直接输出 JSON。"""

# 用户消息里随图片一起发送的文本 (PRD §5.2 User 部分)
USER_PROMPT = "请分析这张照片,按系统要求输出 JSON。"


# 通用三选项 (失败兜底, PRD §5.2 第 5 条 / §3.2)
GENERIC_OPTIONS = [
    {"name": "更明亮", "intent": "整体提亮、轻度增强"},
    {"name": "更鲜艳", "intent": "饱和度提升、色彩增强"},
    {"name": "更柔和", "intent": "降低对比、柔光化"},
]

# name 中禁止出现的技术词 (PRD §5.3)
_TECH_WORDS = ["EV", "HDR", "色温", "饱和度", "对比度", "曝光", "锐化", "降噪"]


def SCHEMA_VALIDATOR(result: dict) -> bool:
    """按 PRD §5.3 校验 Claude 返回。任何一条不满足返回 False。

    在 PRD 版基础上加了防御性 isinstance 判断, 让各种"坏 JSON"
    都安全地返回 False 而不是抛异常。
    """
    if not isinstance(result, dict):
        return False
    if "options" not in result:
        return False
    opts = result["options"]
    if not isinstance(opts, list) or len(opts) != 3:
        return False
    for opt in opts:
        if not isinstance(opt, dict):
            return False
        if "name" not in opt or "intent" not in opt:
            return False
        name = opt["name"]
        intent = opt["intent"]
        if not isinstance(name, str) or not isinstance(intent, str):
            return False
        if len(name) > 5:  # 4 字偏紧, 放宽到 5 字
            return False
        # 拒绝技术词
        for tw in _TECH_WORDS:
            if tw in name:
                return False
    # name 不重复
    if len({o["name"] for o in opts}) < 3:
        return False
    return True


def fallback_analysis() -> dict:
    """兜底分析结果: 通用三选项。"""
    return {
        "scene": "",
        "subject": "",
        "problems": [],
        "options": [dict(o) for o in GENERIC_OPTIONS],
        "fallback": True,
        "prompt_version": PROMPT_VERSION,
    }
