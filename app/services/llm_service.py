import json
from typing import List

from openai import AsyncOpenAI

from app.config import Settings
from app.schemas.flashcard import Difficulty, FlashcardItem
from app.schemas.insights import InsightRequest, ClassInsightRequest

_SYSTEM_PROMPT = (
    "You are a flashcard generation assistant. "
    "Respond ONLY with a valid JSON array — no markdown, no explanation. "
    "Each element must have exactly three fields: "
    '"question" (string), "answer" (string), "difficulty" (one of EASY, MEDIUM, HARD).'
)

_INSIGHTS_SYSTEM_PROMPT = (
    "You are a personalized study advisor. "
    "Analyze the student's performance data and return ONLY a valid JSON array of strings — "
    "no markdown, no explanation outside the array. "
    "Each string is one actionable, specific insight in the student's language (pt-BR). "
    "Generate between 2 and 4 insights. Be direct and concrete — avoid generic advice."
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


async def generate_insights(context: InsightRequest, settings: Settings) -> List[str]:
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    weak_topics_text = ", ".join(
        f"{t.nodeTitle} ({round(t.errorRate * 100)}% de erro)"
        for t in context.weakTopics
    ) or "nenhum tópico com dados suficientes"

    retention_text = (
        f"{round(context.retentionRate * 100)}% nos últimos 30 dias"
        if context.retentionRate is not None
        else "sem dados suficientes ainda"
    )

    user_message = (
        f"Dados de desempenho do estudante:\n"
        f"- Streak atual: {context.streak} dias consecutivos\n"
        f"- Revisões hoje: {context.reviewedToday} ({context.correctToday} corretas)\n"
        f"- Cards pendentes para revisão agora: {context.dueNow}\n"
        f"- Taxa de retenção: {retention_text}\n"
        f"- Tópicos mais fracos: {weak_topics_text}\n\n"
        "Gere insights personalizados em pt-BR. Retorne apenas o array JSON."
    )

    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _INSIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=512,
    )

    raw_text = response.choices[0].message.content or "[]"
    return json.loads(raw_text)


_CLASS_INSIGHTS_SYSTEM_PROMPT = (
    "You are an educational analytics assistant for teachers and advisors. "
    "Analyze the class performance data and return ONLY a valid JSON array of strings — "
    "no markdown, no explanation outside the array. "
    "Each string is one actionable, specific insight in pt-BR. "
    "Generate between 3 and 5 insights. Be analytical and direct — the audience is a teacher "
    "who wants to act on the data. Do not invent data beyond what is provided."
)


async def generate_class_insights(context: ClassInsightRequest, settings: Settings) -> List[str]:
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    weak_topics_text = "\n".join(
        f"  - {t.nodeTitle}: {round(t.errorRate * 100)}% de erro"
        for t in context.weakTopics
    ) or "  - sem dados suficientes"

    avg_retention_text = (
        f"{round(context.avgRetentionRate * 100)}%"
        if context.avgRetentionRate is not None
        else "sem histórico suficiente"
    )

    inactive = [s.userName for s in context.students if s.reviewedToday == 0]
    inactive_text = ", ".join(inactive) if inactive else "nenhum"

    students_text = "\n".join(
        f"  - {s.userName}: {s.reviewedToday} revisões hoje, "
        f"retenção: {round(s.retentionRate * 100)}%" if s.retentionRate is not None
        else f"  - {s.userName}: {s.reviewedToday} revisões hoje, retenção: sem atividade registrada"
        for s in context.students
    )

    user_message = (
        f"Dados da turma (ID: {context.classId}):\n"
        f"- Total de alunos: {context.totalStudents}\n"
        f"- Revisões realizadas hoje (turma): {context.totalReviewedToday}\n"
        f"- Taxa de retenção média: {avg_retention_text}\n"
        f"- Alunos sem atividade hoje: {inactive_text}\n"
        f"- Tópicos com maior taxa de erro:\n{weak_topics_text}\n"
        f"- Desempenho individual:\n{students_text}\n\n"
        "Gere insights para o professor em pt-BR. Retorne apenas o array JSON."
    )

    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _CLASS_INSIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=768,
    )

    raw_text = response.choices[0].message.content or "[]"
    return json.loads(raw_text)
