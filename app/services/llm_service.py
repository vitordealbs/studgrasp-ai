import json
from typing import List

from openai import AsyncOpenAI

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
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    user_message = (
        f"Generate exactly {quantity} flashcard(s) about the topic: '{node_title}'.\n"
        f"Topic description: {node_description}\n\n"
        "Return only the JSON array."
    )

    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=2048,
    )

    raw_text = response.choices[0].message.content or ""
    data = json.loads(raw_text)

    return [
        FlashcardItem(
            question=item["question"],
            answer=item["answer"],
            difficulty=Difficulty(item["difficulty"]),
        )
        for item in data
    ]
