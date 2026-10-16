"""Guards the exact comfy-sdk surface the adapters rely on (skipped when comfy-sdk is not installed)."""

import pytest

pytest.importorskip("comfy_sdk")
import comfy_sdk  # noqa: E402
from comfy_sdk import Comfy  # noqa: E402

FAKE_CREDENTIAL = "placeholder-value"  # never sent anywhere


@pytest.fixture
def client():
    return Comfy(api_key=FAKE_CREDENTIAL)


def test_workflow_surface(client):
    for path in ("workflows.from_file", "assets.from_file", "submit", "jobs.get"):
        o = client
        for part in path.split("."):
            o = getattr(o, part)
        assert callable(o), path
    for name in ("set_input", "remove_node"):
        assert hasattr(comfy_sdk.Workflow, name), name
    for name in ("events", "result", "get_outputs", "id"):
        assert hasattr(comfy_sdk.Job, name), name


def test_router_surface(client):
    assert callable(client.models.submit) and callable(client.models.run)
    for name in ("iter_events", "get", "request_id", "cancel"):
        assert hasattr(comfy_sdk.RequestHandle, name), name
    assert hasattr(comfy_sdk.QueueUpdate, "is_completed") and "queue_position" in comfy_sdk.QueueUpdate.__dataclass_fields__
    # SDK 0.5.0 has no estimate helper: the router adapter POSTs /estimate itself.
    assert not hasattr(client.models, "estimate")


def test_event_class_names_match_adapter():
    for name in ("Progress", "StatusChange", "Preview", "Log"):
        assert hasattr(comfy_sdk, name), name


def test_error_translation_uses_real_classes():
    from app import errors as E
    from app.engines.errmap import translate

    assert isinstance(translate(comfy_sdk.InsufficientCredits("x")), E.InsufficientCredits)
    assert isinstance(translate(comfy_sdk.Unauthorized("x")), E.Unauthorized)
    assert isinstance(translate(comfy_sdk.QueueFull("x", retry_after=3)), E.QueueFull)
