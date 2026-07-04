from unittest.mock import AsyncMock

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

from llm_absa.backend import GeminiBackend, LLMBackend, RetryConfig


class _Dummy(BaseModel):
    value: int


def _response(model: BaseModel):
    return type("_Response", (), {"text": model.model_dump_json()})()


def _rate_limit_error() -> genai_errors.ClientError:
    return genai_errors.ClientError(429, {"message": "rate limited"})


def make_backend(retry: RetryConfig | None = None) -> GeminiBackend:
    backend = GeminiBackend(api_key="fake-key-for-test", model="gemini-test", retry=retry)
    backend._client.aio.models.generate_content = AsyncMock()  # type: ignore[method-assign]
    return backend


async def test_agenerate_returns_parsed_schema():
    backend = make_backend()
    backend._client.aio.models.generate_content.return_value = _response(_Dummy(value=1))

    result = await backend.agenerate("system", "user", _Dummy)

    assert result == _Dummy(value=1)


async def test_agenerate_retries_on_rate_limit_then_succeeds():
    backend = make_backend(RetryConfig(max_attempts=5, min_wait_seconds=0, max_wait_seconds=0))
    backend._client.aio.models.generate_content.side_effect = [
        _rate_limit_error(),
        _rate_limit_error(),
        _response(_Dummy(value=2)),
    ]

    result = await backend.agenerate("system", "user", _Dummy)

    assert result == _Dummy(value=2)
    assert backend._client.aio.models.generate_content.call_count == 3


async def test_agenerate_raises_after_max_attempts_exhausted():
    backend = make_backend(RetryConfig(max_attempts=3, min_wait_seconds=0, max_wait_seconds=0))
    backend._client.aio.models.generate_content.side_effect = _rate_limit_error()

    with pytest.raises(genai_errors.ClientError):
        await backend.agenerate("system", "user", _Dummy)

    assert backend._client.aio.models.generate_content.call_count == 3


async def test_agenerate_does_not_retry_on_parse_failure():
    backend = make_backend()
    backend._client.aio.models.generate_content.return_value = type(
        "_Response", (), {"text": "{}"}
    )()

    with pytest.raises(ValidationError):
        await backend.agenerate("system", "user", _Dummy)

    assert backend._client.aio.models.generate_content.call_count == 1


async def test_agenerate_does_not_retry_on_non_rate_limit_client_error():
    backend = make_backend()
    backend._client.aio.models.generate_content.side_effect = genai_errors.ClientError(
        400, {"message": "bad request"}
    )

    with pytest.raises(genai_errors.ClientError):
        await backend.agenerate("system", "user", _Dummy)

    assert backend._client.aio.models.generate_content.call_count == 1


def test_generate_sync_wrapper_delegates_to_agenerate():
    backend = make_backend()
    backend._client.aio.models.generate_content.return_value = _response(_Dummy(value=3))

    result = backend.generate("system", "user", _Dummy)

    assert result == _Dummy(value=3)


def test_geminibackend_conforms_to_protocol():
    backend = make_backend()
    assert isinstance(backend, LLMBackend)


def test_mockbackend_conforms_to_protocol(mock_backend_factory):
    backend = mock_backend_factory([_Dummy(value=1)])
    assert isinstance(backend, LLMBackend)


async def test_mockbackend_returns_responses_in_order(mock_backend_factory):
    backend = mock_backend_factory([_Dummy(value=1), _Dummy(value=2)])

    first = await backend.agenerate("system", "user", _Dummy)
    second = await backend.agenerate("system", "user", _Dummy)

    assert first == _Dummy(value=1)
    assert second == _Dummy(value=2)
    assert len(backend.calls) == 2
