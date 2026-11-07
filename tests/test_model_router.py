import pytest
from app.core.model_router import ModelRouter
from app.config import settings


def test_model_router_task_mapping():
    router = ModelRouter()
    assert router.get_model_for_task("scanning") == settings.MODEL_SCANNING
    assert router.get_model_for_task("elicitation") == settings.MODEL_ELICITATION
    assert router.get_model_for_task("planning") == settings.MODEL_PLANNING
    assert router.get_model_for_task("cypher") == settings.MODEL_CYPHER
    assert router.get_model_for_task("coding") == settings.MODEL_CODING


def test_model_router_resilience_and_fallback():
    router = ModelRouter()

    # Test generation with fallback mechanism
    result = router.generate(
        task_type="scanning",
        system_prompt="Analyze repository architecture.",
        user_prompt="Scan repository files.",
    )

    assert result is not None
    assert len(result) > 20
    assert router.call_stats["total_calls"] > 0
