from app.agents.os_task_router import (
    OsTaskRouter,
    extract_image_prompt_from_reply,
    extract_narration_from_reply,
)


def test_flyer_routes_to_image_job():
    plan = OsTaskRouter().plan("Create a flyer for my tequila business")
    assert plan.media_job == "flyer_image"


def test_commercial_routes_to_video():
    plan = OsTaskRouter().plan("Write a 30 second commercial for Blue Prince21")
    assert plan.media_job == "commercial_video"


def test_web_fact():
    plan = OsTaskRouter().plan("Is Viral Coaching real?")
    assert plan.wants_web is True
    assert plan.intent == "web_fact"


def test_extract_flux_prompt():
    text = "✅ Flyer created\n\n**Flux:** cinematic bottle on agave field, gold light\n\n**CTA:** Shop now"
    assert "cinematic bottle" in extract_image_prompt_from_reply(text)


def test_extract_narration():
    text = "**ElevenLabs narration:** Drink it. Trade it. Own it. Premium tequila.\n\n**Music:** ..."
    assert "Drink it" in extract_narration_from_reply(text)
