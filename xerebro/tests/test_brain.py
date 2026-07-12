"""
Xerebro AI — Tests
"""

import pytest
from src.brain import XerebroBrain, XerebroConfig, XerebroRequest


@pytest.mark.asyncio
async def test_brain_initialization():
    """Test that the brain initializes with defaults."""
    brain = XerebroBrain()
    assert brain.config.model == "llama3.2"
    assert brain.config.ollama_host == "http://localhost:11434"
    assert not brain.is_available
    await brain.close()


@pytest.mark.asyncio
async def test_brain_custom_config():
    """Test custom configuration."""
    config = XerebroConfig(
        ollama_host="http://ollama:11434",
        model="mistral",
    )
    brain = XerebroBrain(config)
    assert brain.config.model == "mistral"
    assert brain.config.ollama_host == "http://ollama:11434"
    await brain.close()


def test_prompt_building():
    """Test that prompts are built correctly."""
    brain = XerebroBrain()
    request = XerebroRequest(
        prompt="Extract the product price from this HTML",
        context={"html_snippet": "<span class='price'>$29.99</span>"},
    )
    prompt = brain._build_prompt(request)
    assert "Extract the product price" in prompt
    assert "$29.99" in prompt
    assert brain.config.system_prompt in prompt


def test_sync_check_when_ollama_down():
    """Test sync check returns False when no Ollama running."""
    config = XerebroConfig(
        ollama_host="http://localhost:19999",  # Port that won't be open
        timeout_seconds=2,
    )
    brain = XerebroBrain(config)
    result = brain.check_sync()
    assert result is False
    assert brain.is_available is False


def test_reason_sync_when_ollama_down():
    """Test sync reason gracefully fails when Ollama is unreachable."""
    config = XerebroConfig(
        ollama_host="http://localhost:19999",
        timeout_seconds=2,
        max_retries=1,
    )
    brain = XerebroBrain(config)
    result = brain.reason_sync("test prompt")
    assert result.success is False
    assert result.error is not None


def test_prompt_building_without_context():
    """Test prompt building works without context."""
    brain = XerebroBrain()
    request = XerebroRequest(prompt="Hello")
    prompt = brain._build_prompt(request)
    assert prompt.startswith(brain.config.system_prompt)
    assert "Context:" not in prompt
    assert "Hello" in prompt


def test_prompt_building_json_format():
    """Test JSON format instruction is appended."""
    brain = XerebroBrain()
    request = XerebroRequest(prompt="Test", format="json")
    prompt = brain._build_prompt(request)
    assert "Respond with valid JSON" in prompt


def test_prompt_building_text_format():
    """Test text format doesn't append the extra JSON instruction line."""
    brain = XerebroBrain()
    request = XerebroRequest(prompt="Test", format="text")
    prompt = brain._build_prompt(request)
    # The system prompt does mention JSON, but the extra instruction
    # "Respond with valid JSON only, no markdown" should NOT be appended
    assert "Respond with valid JSON only" not in prompt