from pathlib import Path


WORKFLOW = Path(".github/workflows/autoposter.yml")
FIGHTER_WORKFLOW = Path(".github/workflows/fighter-of-day.yml")
VIDEO_WORKFLOW = Path(".github/workflows/video-post.yml")


def test_workflow_is_manual_and_safe():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "cancel-in-progress: false" in text
    assert 'AUTOPOSTER_DRY_RUN: "false"' in text
    assert "TELEGRAM_BOT_TOKEN" in text
    assert "TELEGRAM_CHAT_ID" in text
    assert "git add storage/published.json" in text
    assert "git add ." not in text


def test_fighter_workflow_is_manual_and_uses_shared_history():
    text = FIGHTER_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "group: autoposter-template" in text
    assert 'AUTOPOSTER_DRY_RUN: "false"' in text
    assert "python fighter_of_day.py" in text
    assert "TELEGRAM_BOT_TOKEN" in text
    assert "TELEGRAM_CHAT_ID" in text
    assert "git add storage/published.json" in text
    assert "git add ." not in text


def test_video_workflow_supports_safe_manual_api_validation():
    text = VIDEO_WORKFLOW.read_text(encoding="utf-8")

    assert "schedule:" not in text
    assert "PEXELS_API_KEY" in text
    assert "PIXABAY_API_KEY" in text
    assert "inputs.publish" in text
    assert 'python video_posts.py --slot "${{ inputs.slot || \'auto\' }}"' in text
    assert "git add storage/video_published.json" in text
