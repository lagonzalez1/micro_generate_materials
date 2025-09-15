# test_amazon_model.py
import json
import os
import types
import pytest
from botocore.exceptions import ClientError
import Models.AmazonModel as main


# ---------- Fakes / helpers ----------

class _FakeBody:
    """Mimic botocore StreamingBody with .read()->bytes."""
    def __init__(self, payload: dict):
        self._buf = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._buf


class _BedrockOK:
    """Happy-path fake for bedrock.invoke_model."""
    def __init__(self, output_text="Hello", usage=None):
        if usage is None:
            usage = {"inputTokens": 5, "outputTokens": 7, "totalTokens": 12}
        self.payload = {
            "results": [{"outputText": output_text}],
            "usage": usage
        }
    def invoke_model(self, modelId=None, body=None):
        # basic sanity checks
        assert isinstance(modelId, str) and modelId
        assert isinstance(body, str) and body
        return {"body": _FakeBody(self.payload)}


class _BedrockMalformedJSON:
    """Returns invalid JSON body to trigger JSONDecodeError in _parse_response."""
    def invoke_model(self, modelId=None, body=None):
        class _BadBody:
            def read(self):  # truncated/invalid json
                return b'{"usage":{"inputTokens":1},"results":[{"outputText":"x"}]'
        return {"body": _BadBody()}


class _BedrockRaisesClientError:
    def invoke_model(self, modelId=None, body=None):
        raise ClientError(
            error_response={"Error": {"Code": "BadRequest", "Message": "boom"}} ,
            operation_name="InvokeModel",
        )


class _BedrockRaisesGeneric:
    def invoke_model(self, modelId=None, body=None):
        raise RuntimeError("unexpected failure")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    # Ensure MODEL_ID exists for all tests (your module reads it at import)
    monkeypatch.setenv("MODEL_ID", "anthropic.claude-3-haiku")
    main.MODEL_ID = os.getenv("MODEL_ID")


# ---------- Tests ----------

def test_success_flow(monkeypatch):
    monkeypatch.setattr(main, "bedrock", _BedrockOK(output_text="Generated content", usage={
        "inputTokens": 11, "outputTokens": 29, "totalTokens": 40
    }))

    m = main.AmazonModel(prompt="Make stuff", temp=0.2, top_p=0.9, max_gen_len=128)

    # Parsed response present
    assert m.valid_response() is True
    assert m.get_generation() == "Generated content"

    # Token accounting
    assert m.input_token() == 11
    assert m.output_token() == 29
    assert m.total_token() == 40


def test_malformed_body(monkeypatch, caplog):
    monkeypatch.setattr(main, "bedrock", _BedrockMalformedJSON())
    m = main.AmazonModel(prompt="bad json", temp=0.1, top_p=0.5, max_gen_len=16)

    # _parse_response should fail gracefully -> parsed_response None
    assert m.parsed_response is None
    assert m.valid_response() is False

    # Using token/generation methods without a valid response should raise
    assert m._parse_response() is None
    assert  m.input_token() is None
    assert  m.output_token() is None
    assert  m.total_token() is None
    assert  m.get_generation() is None



def test_client_error(monkeypatch):
    monkeypatch.setattr(main, "bedrock", _BedrockRaisesClientError())

    m = main.AmazonModel(prompt="boom", temp=0.5, top_p=0.9, max_gen_len=64)

    assert m.response is None
    assert m.parsed_response is None
    assert m.valid_response() is False

    assert m._parse_response() is None
    assert  m.input_token() is None
    assert  m.output_token() is None
    assert  m.total_token() is None
    assert  m.get_generation() is None


def test_generic_exception(monkeypatch):
    monkeypatch.setattr(main, "bedrock", _BedrockRaisesGeneric())

    m = main.AmazonModel(prompt="x", temp=0.1, top_p=0.9, max_gen_len=8)
    assert m.response is None
    assert m.parsed_response is None
    assert m.valid_response() is False


def test_usage_fields_present(monkeypatch):
    """Validate that token helpers return correct values when usage dict is well-formed."""
    payload_usage = {"inputTokens": 2, "outputTokens": 5, "totalTokens": 7}
    monkeypatch.setattr(main, "bedrock", _BedrockOK(output_text="OK", usage=payload_usage))

    m = main.AmazonModel(prompt="p", temp=0.0, top_p=1.0, max_gen_len=4)

    assert m.valid_response() is True
    assert m.get_generation() == "OK"
    assert m.input_token() == 2
    assert m.output_token() == 5
    assert m.total_token() == 7