from pathlib import Path

import pytest

from ugi.models import Settings


def test_qwen_production_settings_validate_without_network():
    settings = Settings(
        backend="memory", provider="bedrock", allow_paid_calls=True,
        model_id="qwen.qwen3-32b-v1:0", aws_region="ap-southeast-2",
        input_price=0.1545, output_price=0.6180, daily_cost_limit=0.25,
        max_model_calls=8, max_output_tokens=2250, max_input_tokens=12000,
        extraction_windows=1,
    )
    assert settings.model_id == "qwen.qwen3-32b-v1:0"
    assert settings.max_model_calls == 8
    assert settings.backend == "memory"


def test_paid_inference_remains_explicit_opt_in():
    with pytest.raises(ValueError):
        Settings(provider="bedrock", model_id="qwen.qwen3-32b-v1:0",
                 input_price=0.1545, output_price=0.6180)
    base = (Path(__file__).parents[1] / "compose.yaml").read_text()
    overlay = (Path(__file__).parents[1] / "compose.qwen.yaml").read_text()
    assert 'UGI_ALLOW_PAID_CALLS: "false"' in base
    for s in (
        'UGI_ALLOW_PAID_CALLS: "true"', 'qwen.qwen3-32b-v1:0',
        'UGI_AWS_REGION: ap-southeast-2', 'UGI_INPUT_PRICE: "0.1545"',
        'UGI_OUTPUT_PRICE: "0.6180"', 'UGI_MAX_MODEL_CALLS: "8"',
        'UGI_EXTRACTION_WINDOWS: "1"',
    ):
        assert s in overlay
    assert "UGI_API_KEYS:" not in overlay
    assert "UGI_IDENTITY_" not in overlay
    assert "UGI_MEMORY_" not in overlay
