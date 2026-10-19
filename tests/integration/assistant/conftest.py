import pytest

from backend.common.storage import object_storage


@pytest.fixture
def local_media(monkeypatch, settings):
    settings.DEBUG = True
    settings.MOCK_INTERVIEW_BACKEND = "mock"
    settings.TTS_PROVIDER = settings.STT_PROVIDER = "mock"
    objects: dict[str, tuple[bytes, str]] = {}
    monkeypatch.setattr(
        object_storage,
        "upload_object",
        lambda key, content, mime: objects.__setitem__(key, (content, mime)),
    )
    monkeypatch.setattr(
        object_storage,
        "read_bounded",
        lambda key, limit: (
            objects[key][0]
            if len(objects[key][0]) <= limit
            else (_ for _ in ()).throw(ValueError("limit"))
        ),
    )
    monkeypatch.setattr(
        object_storage, "object_metadata", lambda key: (len(objects[key][0]), objects[key][1])
    )
    monkeypatch.setattr(object_storage, "stream_object", lambda key: iter([objects[key][0]]))
    monkeypatch.setattr(object_storage, "delete_object", lambda key: objects.pop(key, None))
    return objects
