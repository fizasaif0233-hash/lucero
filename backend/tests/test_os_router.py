from app.agents.os_task_router import (
    OsTaskRouter,
    extract_image_prompt_from_reply,
    extract_narration_from_reply,
)


def test_presentation_routes():
    plan = OsTaskRouter().plan("Create a PowerPoint pitch deck")
    assert plan.media_job == "presentation"
    assert plan.requires_replicate is False


def test_flyer_does_not_require_replicate():
    plan = OsTaskRouter().plan("Create a flyer for my tequila business")
    assert plan.media_job == "flyer_image"
    assert plan.requires_replicate is False


def test_commercial_routes_to_video():
    plan = OsTaskRouter().plan("Write a 30 second commercial for Blue Prince21")
    assert plan.media_job == "commercial_video"


def test_web_fact():
    plan = OsTaskRouter().plan("Is Viral Coaching real?")
    assert plan.wants_web is True
    assert plan.intent == "web_fact"


def test_hero_visual_routes_to_image():
    plan = OsTaskRouter().plan("Create a tequila hero visual for Blue Prince21")
    assert plan.media_job == "image"


def test_create_image_routes():
    plan = OsTaskRouter().plan("Generate an image of the Blue Prince bottle")
    assert plan.media_job == "image"


def test_flyer_still_routes_to_flyer():
    plan = OsTaskRouter().plan("Create a printable A4 flyer")
    assert plan.media_job == "flyer_image"


def test_extract_image_description():
    text = (
        "✅ Tequila Hero Visual created\n\n"
        "Image Description: Luxurious cinematic product photography of a premium "
        "tequila bottle on black marble with gold rim light.\n\n"
        "Color Palette: Deep sapphire-blue, Gold, Black"
    )
    assert "cinematic product photography" in extract_image_prompt_from_reply(text)


def test_extract_narration():
    text = "**ElevenLabs narration:** Drink it. Trade it. Own it. Premium tequila.\n\n**Music:** ..."
    assert "Drink it" in extract_narration_from_reply(text)
