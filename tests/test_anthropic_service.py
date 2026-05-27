import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.flashcard import Difficulty
from app.services import anthropic_service
from app.config import Settings

MOCK_SETTINGS = Settings(
    anthropic_api_key="test-key",
    java_api_url="http://localhost:8080",
    db_url="postgresql://test:test@localhost:5432/test",
    redis_url="redis://localhost:6379",
)

MOCK_RESPONSE_JSON = json.dumps([
    {"question": "What is REST?", "answer": "Representational State Transfer", "difficulty": "EASY"},
    {"question": "What is HTTP?", "answer": "HyperText Transfer Protocol", "difficulty": "MEDIUM"},
])


@pytest.mark.asyncio
@patch("app.services.anthropic_service.anthropic.AsyncAnthropic")
async def test_generate_flashcards_success(mock_anthropic_cls):
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = MOCK_RESPONSE_JSON

    mock_message = MagicMock()
    mock_message.content = [mock_text_block]

    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.get_final_message = AsyncMock(return_value=mock_message)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream
    mock_anthropic_cls.return_value = mock_client

    result = await anthropic_service.generate_flashcards(
        node_title="REST APIs",
        node_description="RESTful API design principles",
        quantity=2,
        settings=MOCK_SETTINGS,
    )

    assert len(result) == 2
    assert result[0].question == "What is REST?"
    assert result[0].difficulty == Difficulty.EASY
    assert result[1].difficulty == Difficulty.MEDIUM


@pytest.mark.asyncio
@patch("app.services.anthropic_service.anthropic.AsyncAnthropic")
async def test_generate_flashcards_invalid_json(mock_anthropic_cls):
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "This is not JSON"

    mock_message = MagicMock()
    mock_message.content = [mock_text_block]

    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.get_final_message = AsyncMock(return_value=mock_message)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream
    mock_anthropic_cls.return_value = mock_client

    with pytest.raises(json.JSONDecodeError):
        await anthropic_service.generate_flashcards(
            node_title="REST APIs",
            node_description="desc",
            quantity=1,
            settings=MOCK_SETTINGS,
        )