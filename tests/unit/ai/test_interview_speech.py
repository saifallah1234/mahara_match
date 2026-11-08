import json
import wave
from io import BytesIO
from types import SimpleNamespace

import pytest

from ai.speech.providers import MockTTS, stt_provider, tts_provider


def test_disabled_and_missing_providers(tmp_path):
    for name in ("mock", "piper", "elevenlabs"):
        with pytest.raises(ValueError):
            tts_provider(name)
    with pytest.raises(ValueError):
        stt_provider("faster-whisper", whisper_model=str(tmp_path))
    with pytest.raises(ValueError):
        tts_provider("mock", allow_mock=True).synthesize("Hello", "en", "voice")


def test_piper_explicit_french_model(tmp_path, monkeypatch):
    from ai.speech import piper

    model = tmp_path / "fr.onnx"
    model.touch()
    (tmp_path / "fr.onnx.json").write_text(json.dumps({"language": {"code": "fr_FR"}}))
    content = MockTTS().synthesize("test", "fr", "test").content

    def synthesize(text, target):
        with wave.open(BytesIO(content), "rb") as source:
            target.setparams(source.getparams())
            target.writeframes(source.readframes(source.getnframes()))

    monkeypatch.setattr(
        piper,
        "import_module",
        lambda name: SimpleNamespace(
            PiperVoice=SimpleNamespace(load=lambda path: SimpleNamespace(synthesize_wav=synthesize))
        ),
    )
    result = tts_provider("piper", piper_model=str(model)).synthesize("Bonjour", "fr", "local")
    assert result.duration_ms == 1000 and result.metadata["simulated"] is False


def test_whisper_local_only(tmp_path, monkeypatch):
    numpy = pytest.importorskip("numpy")
    from ai.speech import faster_whisper

    for name in ("model.bin", "config.json", "tokenizer.json"):
        (tmp_path / name).touch()
    calls = []
    heard = []

    def transcribe(audio, **kwargs):
        heard.append(audio)
        return iter([SimpleNamespace(text=" Bonjour ")]), SimpleNamespace(language="fr")

    def model(path, **options):
        calls.append(options)
        return SimpleNamespace(transcribe=transcribe)

    real_import = faster_whisper.import_module
    monkeypatch.setattr(
        faster_whisper,
        "import_module",
        lambda name: (
            SimpleNamespace(WhisperModel=model) if name == "faster_whisper" else real_import(name)
        ),
    )
    # The job hands over the 16 kHz mono WAV produced by FFmpeg (decode_audio).
    wav = MockTTS().synthesize("test", "fr", "test").content
    result = stt_provider("faster-whisper", whisper_model=str(tmp_path)).transcribe(wav, "fr")
    assert result.text == "Bonjour" and calls[0]["local_files_only"] is True
    # Samples, not a file: faster-whisper's own PyAV decoder fails with PyAV 19.
    samples = heard[0]
    assert isinstance(samples, numpy.ndarray) and samples.dtype == numpy.float32
    assert samples.shape == (16000,) and 0 < abs(samples).max() <= 1
    with pytest.raises(ValueError, match="16 kHz mono"):
        stt_provider("faster-whisper", whisper_model=str(tmp_path)).transcribe(b"audio", "fr")


@pytest.mark.parametrize("missing", ("model.bin", "config.json", "tokenizer.json"))
def test_whisper_rejects_incomplete_local_model(tmp_path, monkeypatch, missing):
    from ai.speech import faster_whisper

    for name in ("model.bin", "config.json", "tokenizer.json"):
        if name != missing:
            (tmp_path / name).touch()

    def unexpected_import(name):
        pytest.fail("Incomplete models must fail before loading the speech library.")

    monkeypatch.setattr(faster_whisper, "import_module", unexpected_import)
    with pytest.raises(ValueError, match="complete existing faster-whisper model"):
        stt_provider("faster-whisper", whisper_model=str(tmp_path))


def test_elevenlabs_contract_without_network(monkeypatch):
    from ai.speech import elevenlabs

    requests = []

    class Response(BytesIO):
        pass

    def send(request, timeout):
        requests.append(request)
        return Response(b"mp3")

    monkeypatch.setattr(elevenlabs, "urlopen", send)
    monkeypatch.setattr(elevenlabs, "decode_audio", lambda content, ffmpeg: (b"wav", 1200))
    adapter = tts_provider("elevenlabs", elevenlabs_key="secret", paid_enabled=True)
    result = adapter.synthesize("Bonjour", "fr", "JBFqnCBsd6RMkjVDRZzb")
    assert result.content == b"wav" and result.duration_ms == 1200
    assert json.loads(requests[0].data)["model_id"] == "eleven_multilingual_v2"
    assert "secret" not in repr(result)
