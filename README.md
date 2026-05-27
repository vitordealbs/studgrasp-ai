# studgrasp-ai

Serviço de inteligência artificial do **StudGrasp** — plataforma de aprendizado de CS com flashcards, trilhas de conhecimento e revisão espaçada.

Construído com FastAPI (Python), integra-se ao backend Java Spring Boot via HTTP e ao banco PostgreSQL compartilhado.

---

## Versões

| Tecnologia        | Versão      |
|-------------------|-------------|
| Python            | 3.11+       |
| FastAPI           | 0.115.5     |
| Uvicorn           | 0.32.1      |
| Anthropic SDK     | >= 0.50.0   |
| Claude Model      | claude-opus-4-7 |
| Playwright        | 1.49.0      |
| Celery            | 5.4.0       |
| SQLAlchemy        | 2.0.36      |
| pydantic-settings | 2.6.1       |
| httpx             | 0.28.1      |
| Redis             | 5.2.1       |
| pytest            | 8.3.4       |

---

## Pré-requisitos

- Python 3.11+
- PostgreSQL (compartilhado com o Java API — não cria tabelas novas)
- Redis (usado pelo Celery)
- Java Spring Boot API rodando em `http://localhost:8080`
- Chave de API da Anthropic

---

## Configuração

### 1. Clone e entre no projeto

```bash
git clone <repo-url>
cd studgrasp-ai
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Instale o browser do Playwright

```bash
playwright install chromium
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com seus valores:

```env
ANTHROPIC_API_KEY=sk-ant-...
JAVA_API_URL=http://localhost:8080
DB_URL=postgresql://usuario:senha@localhost:5432/studgrasp
REDIS_URL=redis://localhost:6379
```

---

## Build e execução

### Iniciar a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em `http://localhost:8000`.

Documentação interativa: `http://localhost:8000/docs`

### Iniciar o worker Celery

```bash
celery -A tasks.scraper_task.celery_app worker --loglevel=info
```

### Iniciar o Celery Beat (agendador semanal)

```bash
celery -A tasks.scraper_task.celery_app beat --loglevel=info
```

---

## Endpoints implementados

### Health

| Método | Rota      | Descrição                        |
|--------|-----------|----------------------------------|
| GET    | `/health` | Verifica se o serviço está ativo |

**Resposta:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-27T00:00:00.000000+00:00"
}
```

---

### Flashcards — Geração com IA

| Método | Rota                       | Descrição                                              |
|--------|----------------------------|--------------------------------------------------------|
| POST   | `/ai/flashcards/generate`  | Gera flashcards com Claude e salva via Java API        |
| GET    | `/ai/review/{userId}`      | Retorna flashcards com revisão pendente (SM-2)         |

**POST `/ai/flashcards/generate` — body:**
```json
{
  "nodeId": "node-uuid",
  "nodeTitle": "REST APIs",
  "nodeDescription": "Princípios de design de APIs RESTful",
  "quantity": 5
}
```

**Resposta:**
```json
{
  "nodeId": "node-uuid",
  "flashcards": [
    {
      "question": "O que é REST?",
      "answer": "Representational State Transfer",
      "difficulty": "EASY"
    }
  ]
}
```

**GET `/ai/review/{userId}` — resposta:**
```json
{
  "userId": "user-uuid",
  "cards": [
    {
      "id": "fc-uuid",
      "nodeId": "node-uuid",
      "question": "...",
      "answer": "...",
      "difficulty": "MEDIUM",
      "nextReviewAt": "2026-05-27T00:00:00",
      "easeFactor": 2.5,
      "intervalDays": 6,
      "repetitions": 2
    }
  ]
}
```

---

### Análise de desempenho

| Método | Rota                    | Descrição                                              |
|--------|-------------------------|--------------------------------------------------------|
| GET    | `/ai/analysis/{userId}` | Retorna os tópicos com maior taxa de erro do usuário   |

**Resposta:**
```json
{
  "userId": "user-uuid",
  "weakTopics": [
    {
      "nodeId": "node-uuid",
      "nodeTitle": "Algoritmos de Ordenação",
      "errorRate": 0.75
    }
  ]
}
```

---

## Tarefas agendadas (Celery)

| Tarefa                     | Frequência          | Descrição                                           |
|----------------------------|---------------------|-----------------------------------------------------|
| `scrape_roadmaps_task`     | Semanal (dom 00:00) | Scrapa as trilhas do roadmap.sh e salva via Java API |

**Trilhas suportadas:** `backend`, `frontend`, `devops`, `full-stack`, `android`, `ai-data-scientist`

Para executar manualmente:

```bash
celery -A tasks.scraper_task.celery_app call tasks.scraper_task.scrape_roadmaps_task
```

---

## Banco de dados

O serviço acessa o banco PostgreSQL **compartilhado com o Java API** — nenhuma tabela é criada.

Tabelas utilizadas (somente leitura via SQL puro):

| Tabela                | Uso                                                        |
|-----------------------|------------------------------------------------------------|
| `flashcard_attempts`  | Leitura para SM-2 (revisão pendente e taxa de erros)       |
| `flashcards`          | Join para obter pergunta, resposta e dificuldade           |
| `roadmap_nodes`       | Join para obter título do nó na análise de desempenho      |

---

## Testes

```bash
pytest tests/
```

Com verbose e cobertura:

```bash
pytest tests/ -v --tb=short
```

### Módulos de teste

| Arquivo                          | O que testa                                              |
|----------------------------------|----------------------------------------------------------|
| `tests/test_health.py`           | Endpoint `/health`                                       |
| `tests/test_flashcards.py`       | Geração de flashcards e listagem de revisão              |
| `tests/test_analysis.py`         | Endpoint de análise de desempenho                        |
| `tests/test_anthropic_service.py`| Integração com Claude (mockado) e parsing do JSON        |
| `tests/test_scraper_service.py`  | Parser de `__NEXT_DATA__`, fallback DOM, save via httpx  |
| `tests/test_spaced_repetition.py`| Algoritmo SM-2 e queries SQL (mockadas)                  |

---

## Arquitetura

```
studgrasp-ai/
├── app/
│   ├── main.py              # FastAPI app + error handler global
│   ├── config.py            # pydantic-settings + lru_cache
│   ├── database.py          # SQLAlchemy engine + get_db()
│   ├── routers/             # Camada HTTP (recebe/responde apenas)
│   │   ├── health.py
│   │   ├── flashcards.py
│   │   └── analysis.py
│   ├── services/            # Lógica de negócio
│   │   ├── anthropic_service.py   # Chamadas ao Claude
│   │   ├── spaced_repetition.py   # SM-2 + queries PostgreSQL
│   │   └── scraper_service.py     # Playwright scraper
│   └── schemas/             # Modelos Pydantic
│       ├── flashcard.py
│       └── analysis.py
├── tasks/
│   └── scraper_task.py      # Celery + Beat schedule
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── .env.example
└── requirements.txt
```

---

## Padrão de erros

Todos os erros retornam JSON no formato:

```json
{
  "status": "error",
  "message": "Descrição do erro em inglês",
  "timestamp": "2026-05-27T00:00:00.000000+00:00"
}
```