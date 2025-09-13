# test_gemini_model.py
import types
import pytest

# 👇 Change this to your actual module path (e.g., from app.gemini_model import GeminiModel; import app.gemini_model as mod)
import Models.GeminModel as mod


# ---- Fakes ----
class _FakeModels:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    def generate_content(self, model=None, contents=None):
        if self._exc:
            raise self._exc
        # Return an object with a .text attribute like the real SDK
        return types.SimpleNamespace(text=self._text)


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self.models = _FakeModels(text=text, exc=exc)


# ---- Tests ----
def test_success_flow(monkeypatch):
    # Patch the module-level `client` to a fake that returns text
    monkeypatch.setattr(mod, "client", _FakeClient(text="Hello Gemini!"))

    m = mod.GeminiModel(prompt="Generate materials for addition")
    assert m.valid_response() is True
    assert m.get_generation() == "Hello Gemini!"
    assert m.get_text_length() == len("Hello Gemini!")

    # total_token uses (len(compressed)+2)//4
    compressed_len = len("".join("Hello Gemini!".split()))
    assert m.total_token() == (compressed_len + 2) // 4


def test_empty_text(monkeypatch):
    monkeypatch.setattr(mod, "client", _FakeClient(text=""))

    m = mod.GeminiModel(prompt="empty please")
    assert m.valid_response() is True
    assert m.get_generation() == ""
    assert m.get_text_length() == 0
    # compressed length is 0 -> (0+2)//4 == 0
    assert m.total_token() == 0


def test_whitespace_text(monkeypatch):
    text = "a b\nc\t d"
    monkeypatch.setattr(mod, "client", _FakeClient(text=text))

    m = mod.GeminiModel(prompt="spaces")
    assert m.valid_response() is True
    compressed = "".join(text.split())  # "abcd"
    assert m.total_token() == (len(compressed) + 2) // 4  # (4+2)//4 == 1


def test_exception_path(monkeypatch):
    # Simulate the genai client raising an exception during generate_content
    monkeypatch.setattr(mod, "client", _FakeClient(exc=RuntimeError("boom")))

    m = mod.GeminiModel(prompt="should fail")
    # generate_gemini catches and prints, returns None
    assert m.valid_response() is False
    assert m.response is None

    # Accessors should fail since response is None
    with pytest.raises(AttributeError):
        _ = m.get_generation()
    with pytest.raises(AttributeError):
        _ = m.get_text_length()
    with pytest.raises(AttributeError):
        _ = m.total_token()