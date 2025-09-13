# test_amazon_model.py
import json
import os
import types
import pytest
from botocore.exceptions import ClientError

# 👇 change this import to your actual module path
import Models.AmazonModel as mod


class FakeBody:
    """Mimics botocore.response.StreamingBody.read() -> bytes."""
    def __init__(self, payload_dict):
        self._bytes = json.dumps(payload_dict).encode("utf-8")
    def read(self):
        return self._bytes


class FakeBedrockOK:
    """Successful bedrock.invoke_model returning a dict with 'body' that supports .read()."""
    def __init__(self, output_text="Hello world", usage=None):
        if usage is None:
            usage = {"inputTokens": 7, "outputTokens": 3, "totalTokens": 10}
        self.payload = {
            "results": [{"outputText": output_text}],
            "usage": usage
        }
    def invoke_model(self, modelId=None, body=None):
        # Minimal validation of inputs
        assert isinstance(modelId, str) and modelId
        assert isinstance(body, str) and body
        return {"body": FakeBody(self.payload)}


class FakeBedrockMalformedBody:
    """Returns a non-JSON body to exercise JSONDecodeError handling."""
    def invoke_model(self, modelId=None, body=None):
        class BadBody:
            def read(self):
                return b'{"usage": {"inputTokens": 1}, "results": '  # truncated JSON
        return {"body": BadBody()}


class FakeBedrockRaisesClientError:
    def invoke_model(self, modelId=None, body=None):
        raise ClientError(
            error_response={"Error": {"Code": "BadRequest", "Message": "boom"}},
            operation_name="InvokeModel",
        )


class FakeBedrockRaisesException:
    def invoke_model(self, modelId=None, body=None):
        raise RuntimeError("unexpected failure")


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    # Ensure MODEL_ID is set for all tests
    monkeypatch.setenv("MODEL_ID", "anthropic.claude-3-haiku")
    # If module read MODEL_ID at import, refresh its constant
    mod.MODEL_ID = os.getenv("MODEL_ID")


def test_success_flow(monkeypatch):
    # Replace the global bedrock client in module with a fake OK client
    monkeypatch.setattr(mod, "bedrock", FakeBedrockOK(output_text="Generated content", usage={
        "inputTokens": 11, "outputTokens": 29, "totalTokens": 40
    }))

    m = mod.AmazonModel(prompt="Make stuff", temp=0.2, top_p=0.9, max_gen_len=128)

    # Response parsed
    assert m.valid_response() is True
    assert m.get_generation() == "Generated content"

    # Token accounting
    assert m.input_token() == 11
    assert m.output_token() == 29
    assert m.total_token() == 40


def test_malformed_body_parsing(monkeypatch, caplog):
    monkeypatch.setattr(mod, "bedrock", FakeBedrockMalformedBody())

    m = mod.AmazonModel(prompt="test", temp=0.1, top_p=0.5, max_gen_len=16)
    # _invoke_model returns a dict with body, but _parse_response should fail -> parsed_response None
    assert m.parsed_response is None
    assert m.valid_response() is False
    # calling get_generation now would KeyError; we only assert invalid
    # input/output/total token calls will also fail if used without a valid response — by design.


def test_client_error(monkeypatch, caplog):
    monkeypatch.setattr(mod, "bedrock", FakeBedrockRaisesClientError())

    m = mod.AmazonModel(prompt="boom", temp=0.5, top_p=0.9, max_gen_len=64)
    # Invocation failed -> response is None, parsed_response None
    assert m.response is None
    assert m.parsed_response is None
    assert m.valid_response() is False

    # Ensure the class doesn't crash when methods are not appropriate to call without response
    with pytest.raises(AttributeError):
        _ = m.input_token()
    with pytest.raises(AttributeError):
        _ = m.output_token()
    with pytest.raises(AttributeError):
        _ = m.total_token()
    with pytest.raises(TypeError):
        _ = m.get_generation()  # parsed_response is None -> TypeError/KeyError depending on access path


def test_generic_exception(monkeypatch):
    monkeypatch.setattr(mod, "bedrock", FakeBedrockRaisesException())

    m = mod.AmazonModel(prompt="x", temp=0.1, top_p=0.9, max_gen_len=8)
    assert m.response is None
    assert m.parsed_response is None
    assert m.valid_response() is False


def test_usage_methods_independent_calls(monkeypatch):
    """Validate that each token method re-parses body independently and returns correct fields."""
    payload = {
        "results": [{"outputText": "OK"}],
        "usage": {"inputTokens": 2, "outputTokens": 5, "totalTokens": 7},
    }
    class FakeBedrockCustom:
        def invoke_model(self, modelId=None, body=None):
            return {"body": FakeBody(payload)}

    monkeypatch.setattr(mod, "bedrock", FakeBedrockCustom())
    m = mod.AmazonModel(prompt="p", temp=0.0, top_p=1.0, max_gen_len=4)

    assert m.valid_response() is True
    assert m.input_token() == 2
    assert m.output_token() == 5
    assert m.total_token() == 7
    assert m.get_generation() == "OK"