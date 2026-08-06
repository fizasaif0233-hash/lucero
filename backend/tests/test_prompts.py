from app.ai.prompts import build_system_prompt, JARVIS_SYSTEM_PROMPT


def test_system_prompt_without_context():
    prompt = build_system_prompt(None)
    assert "Jarvis" in prompt
    assert "Never invent" in prompt
    assert prompt == JARVIS_SYSTEM_PROMPT


def test_system_prompt_with_context():
    prompt = build_system_prompt("Revenue was $1M last year.")
    assert "Knowledge base context" in prompt
    assert "Revenue was $1M last year." in prompt
