from app.ai.prompts import build_system_prompt, JARVIS_SYSTEM_PROMPT, LUCERO_SYSTEM_PROMPT


def test_system_prompt_without_context():
    prompt = build_system_prompt(None)
    assert "L.U.C.E.R.O" in prompt
    assert "never Jarvis" in prompt
    assert "ACTION mode" in prompt
    assert "Do not refuse" in prompt or "Never refuse" in prompt
    assert "Sticky business memory" in prompt
    assert "Permanent knowledge library" in prompt
    assert LUCERO_SYSTEM_PROMPT in prompt
    assert JARVIS_SYSTEM_PROMPT == LUCERO_SYSTEM_PROMPT


def test_system_prompt_with_context():
    prompt = build_system_prompt("Revenue was $1M last year.")
    assert "Knowledge / research context" in prompt
    assert "Revenue was $1M last year." in prompt
    assert "Do NOT refuse" in prompt


def test_system_prompt_forbids_document_only_refusal():
    prompt = build_system_prompt(None)
    assert "isn't uploaded" in prompt


def test_action_mode_deliverable_formats():
    prompt = build_system_prompt(None)
    assert "0–2 clarifying questions" in prompt or "0-2 clarifying questions" in prompt
    assert "Flyer created" in prompt
    assert "DALL·E" in prompt or "DALL" in prompt
    assert "Midjourney" in prompt
    assert "ElevenLabs" in prompt
    assert "SWOT" in prompt
    assert "Feel free" in prompt  # banned phrase listed so model avoids it
    assert "Drink it. Trade it. Own it." in prompt
