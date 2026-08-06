from app.ai.prompts import build_system_prompt, JARVIS_SYSTEM_PROMPT, LUCERO_SYSTEM_PROMPT


def test_system_prompt_without_context():
    prompt = build_system_prompt(None)
    assert "L.U.C.E.R.O" in prompt
    assert "never Jarvis" in prompt
    assert "Never refuse" in prompt
    assert "general knowledge" in prompt.lower()
    assert LUCERO_SYSTEM_PROMPT in prompt
    assert JARVIS_SYSTEM_PROMPT == LUCERO_SYSTEM_PROMPT


def test_system_prompt_with_context():
    prompt = build_system_prompt("Revenue was $1M last year.")
    assert "Knowledge / research context" in prompt
    assert "Revenue was $1M last year." in prompt
    assert "do NOT refuse" in prompt


def test_system_prompt_forbids_document_only_refusal():
    prompt = build_system_prompt(None)
    assert "I cannot answer because it is not in the uploaded documents" in prompt
