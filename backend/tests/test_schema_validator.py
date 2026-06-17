"""Schema 校验测试 (任务 2.3: 各种坏 JSON 都能拒绝)。"""

from app.prompts.analyze_prompt import (
    SCHEMA_VALIDATOR,
    fallback_analysis,
)


def _good():
    return {
        "scene": "野生动物",
        "subject": "猎豹",
        "problems": ["主体偏暗"],
        "options": [
            {"name": "动物更清楚", "intent": "主体增强"},
            {"name": "天空更蓝", "intent": "蓝色加饱和"},
            {"name": "暖色草原", "intent": "暖调 LUT"},
        ],
    }


def test_good_passes():
    assert SCHEMA_VALIDATOR(_good()) is True


def test_fallback_passes_validator():
    assert SCHEMA_VALIDATOR(fallback_analysis()) is True


def test_missing_options():
    assert SCHEMA_VALIDATOR({"scene": "x"}) is False


def test_wrong_option_count():
    r = _good()
    r["options"] = r["options"][:2]
    assert SCHEMA_VALIDATOR(r) is False


def test_missing_intent_key():
    r = _good()
    del r["options"][0]["intent"]
    assert SCHEMA_VALIDATOR(r) is False


def test_name_too_long():
    r = _good()
    r["options"][0]["name"] = "这个名字明显超过五个字了"
    assert SCHEMA_VALIDATOR(r) is False


def test_tech_word_rejected():
    r = _good()
    r["options"][0]["name"] = "HDR增强"
    assert SCHEMA_VALIDATOR(r) is False
    r2 = _good()
    r2["options"][1]["name"] = "饱和度"
    assert SCHEMA_VALIDATOR(r2) is False


def test_duplicate_names():
    r = _good()
    r["options"][1]["name"] = r["options"][0]["name"]
    assert SCHEMA_VALIDATOR(r) is False


def test_not_a_dict():
    assert SCHEMA_VALIDATOR(None) is False
    assert SCHEMA_VALIDATOR("乱七八糟") is False
    assert SCHEMA_VALIDATOR([1, 2, 3]) is False


def test_option_not_dict():
    r = _good()
    r["options"][0] = "不是对象"
    assert SCHEMA_VALIDATOR(r) is False
