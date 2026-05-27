import json
from typing import List

import anthropic

from app.config import Settings
from app.schemas.flashcard import Difficulty, FlashcardItem

_SYSTEM_PROMPT = (
    "You are a flashcard generation assistant. "
    "Respond ONLY with a valid JSON array — no markdown, no explanation. "
    "Each element must have exactly three fields: "
    '"question" (string), "answer" (string), "difficulty" (one of EASY, MEDIUM, HARD).'
)


async def generate_flashcards(
    node_title: str,
    node_description: str,
    quantity: int,
    settings: Settings,
) -> List[FlashcardItem]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    user_message = (
        f"Generate exactly {quantity} flashcard(s) about the topic: '{node_title}'.\n"
        f"Topic description: {node_description}\n\n"
        "Return only the JSON array."
    )

    stream = client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    async with stream as s:
        message = await s.get_final_message()

    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text = block.text
            break

    data = json.loads(raw_text)
    return [
        FlashcardItem(
            question=item["question"],
            answer=item["answer"],
            difficulty=Difficulty(item["difficulty"]),
        )
        for item in data
    ]
