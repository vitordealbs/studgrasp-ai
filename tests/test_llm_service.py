import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.flashcard import Difficulty
from app.services import llm_service
from app.config import Settings

MOCK_SETTINGS = Settings(
    llm_api_key="test-key",
    llm_base_url="https://api.deepseek.com",
    llm_model="deepseek-chat",
    java_api_url="http://localhost:8080",
    db_url="postgresql://test:test@localhost:5432/test",
    redis_url="redis://localhost:6379",
)

MOCK_RESPONSE_JSON = json.dumps([
    {"question": "What is REST?", "answer": "Representational State Transfer", "difficulty": "EASY"},
    {"question": "What is HTTP?", "answer": "HyperText Transfer Protocol", "difficulty": "MEDIUM"},
])


def _make_mock_openai_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
@patch("app.services.llm_service.AsyncOpenAI")
async def test_generate_flashcards_success(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_openai_response(MOCK_RESPONSE_JSON)
    )
    mock_openai_cls.return_value = mock_client

    result = await llm_service.generate_flashcards(
        node_title="REST APIs",
        node_description="RESTful API design principles",
        quantity=2,
        settings=MOCK_SETTINGS,
    )

    assert len(result) == 2
    assert result[0].question == "What is REST?"
    assert result[0].difficulty == Difficulty.EASY
    assert result[1].difficulty == Difficulty.MEDIUM

    mock_openai_cls.assert_called_once_with(
        api_key="test-key",
        base_url="https://api.deepseek.com",
    )


@pytest.mark.asyncio
@patch("app.services.llm_service.AsyncOpenAI")
async def test_generate_flashcards_invalid_json(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_openai_response("This is not JSON")
    )
    mock_openai_cls.return_value = mock_client

    with pytest.raises(json.JSONDecodeError):
        await llm_service.generate_flashcards(
            node_title="REST APIs",
            node_description="desc",
            quantity=1,
            settings=MOCK_SETTINGS,
        )


@pytest.mark.asyncio
@patch("app.services.llm_service.AsyncOpenAI")
async def test_generate_flashcards_uses_configured_model(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_openai_response(MOCK_RESPONSE_JSON)
    )
    mock_openai_cls.return_value = mock_client

    await llm_service.generate_flashcards(
        node_title="topic",
        node_description="desc",
        quantity=2,
        settings=MOCK_SETTINGS,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-chat"