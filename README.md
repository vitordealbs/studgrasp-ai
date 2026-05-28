# studgrasp-ai

Serviço de inteligência artificial do **StudGrasp** — plataforma de aprendizado de CS com flashcards, trilhas de conhecimento e revisão espaçada.

Construído com FastAPI (Python), integra-se ao backend Java Spring Boot via HTTP e ao banco PostgreSQL compartilhado.

---

## Versões

| Tecnologia        | Versão   |
|-------------------|----------|
| Python            | 3.11+    |
| FastAPI           | 0.115.5  |
| Uvicorn           | 0.32.1   |
| OpenAI SDK        | >= 1.50.0 |
| Playwright        | 1.49.0   |
| Celery            | 5.4.0    |
| SQLAlchemy        | 2.0.36   |
| pydantic-settings | 2.6.1    |
| httpx             | 0.28.1   |
| Redis             | 5.2.1    |
| pytest            | 8.3.4    |

---

## Pré-requisitos

- Python 3.11+
- PostgreSQL (compartilhado com o Java API — não cria tabelas novas)
- Redis (usado pelo Celery, opcional se não usar a task manual)
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

Edite o `.env` escolhendo o provedor LLM desejado:

```env
# DeepSeek (barato, recomendado para desenvolvimento)
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

JAVA_API_URL=http://localhost:8080
DB_URL=postgresql://usuario:senha@localhost:5432/studgrasp
REDIS_URL=redis://localhost:6379
```

#### Provedores suportados

O serviço usa a API compatível com OpenAI — qualquer provedor que siga esse padrão funciona sem alterar código.

| Provedor    | `LLM_BASE_URL`                        | `LLM_MODEL`               | Custo       |
|-------------|---------------------------------------|---------------------------|-------------|
| DeepSeek    | `https://api.deepseek.com`            | `deepseek-chat`           | ~$0.14/1M   |
| Groq        | `https://api.groq.com/openai/v1`      | `llama-3.3-70b-versatile` | Grátis*     |
| OpenAI      | `https://api.openai.com/v1`           | `gpt-4o-mini`             | ~$0.15/1M   |
| Anthropic   | `https://api.anthropic.com/v1`        | `claude-opus-4-7`         | ~$5.00/1M   |
| Ollama      | `http://localhost:11434/v1`           | `llama3.2`                | Grátis      |

\* Groq tem limites de requisições no plano gratuito.

---

## Build e execução

### Iniciar a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em `http://localhost:8000`.

Documentação interativa: `http://localhost:8000/docs`

### Iniciar o worker Celery (opcional)

Necessário apenas se quiser disparar o scraper via Celery em vez do endpoint HTTP.

```bash
celery -A tasks.scraper_task.celery_app worker --loglevel=info
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

### Scraper de trilhas

| Método | Rota         | Descrição                                                   |
|--------|--------------|-------------------------------------------------------------|
| POST   | `/ai/scrape` | Scrapa o roadmap.sh e popula as trilhas no banco via Java API |

O endpoint é executado de forma síncrona e pode levar alguns minutos. Recomendado rodar **uma única vez** para popular o banco.

**Fluxo interno:**
1. Acessa `https://roadmap.sh` e descobre dinamicamente **todas** as trilhas disponíveis via `window.__NEXT_DATA__` (fallback por links DOM)
2. Para cada trilha descoberta:
   - `GET /api/roadmaps/career/{careerType}` → verifica se já existe
   - Se não existir → `POST /api/roadmaps` para criá-la automaticamente
   - Scrapa os nós da página da trilha (`window.__NEXT_DATA__`, fallback DOM)
   - `POST /api/roadmap-nodes` para cada nó encontrado

**Trilhas:** descobertas automaticamente — todas as disponíveis no roadmap.sh na data da execução.

**Resposta:**
```json
{
  "status": "ok",
  "summary": {
    "backend": 42,
    "frontend": 38,
    "devops": 31,
    "full-stack": 12,
    "android": 27,
    "ai-data-scientist": 25
  },
  "timestamp": "2026-05-27T00:00:00.000000+00:00"
}
```

---

### Flashcards — Geração com IA

| Método | Rota                      | Descrição                                       |
|--------|---------------------------|-------------------------------------------------|
| POST   | `/ai/flashcards/generate` | Gera flashcards com Claude e salva via Java API |
| GET    | `/ai/review/{userId}`     | Retorna flashcards com revisão pendente (SM-2)  |

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

| Método | Rota                    | Descrição                                            |
|--------|-------------------------|------------------------------------------------------|
| GET    | `/ai/analysis/{userId}` | Retorna os tópicos com maior taxa de erro do usuário |

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

## Banco de dados

O serviço acessa o banco PostgreSQL **compartilhado com o Java API** — nenhuma tabela é criada.

Tabelas utilizadas (somente leitura via SQL puro):

| Tabela               | Uso                                                   |
|----------------------|-------------------------------------------------------|
| `flashcard_attempts` | Leitura para SM-2 (revisão pendente e taxa de erros)  |
| `flashcards`         | Join para obter pergunta, resposta e dificuldade      |
| `roadmap_nodes`      | Join para obter título do nó na análise de desempenho |

---

## Testes

### Pré-requisito para rodar os testes

Os testes não precisam de banco, Redis nem Java rodando — tudo é mockado.

Apenas instale as dependências:

```bash
pip install -r requirements.txt
```

### Rodar todos os testes

```bash
pytest tests/
```

### Com detalhes de cada teste

```bash
pytest tests/ -v
```

### Com rastreamento de erros completo

```bash
pytest tests/ -v --tb=long
```

### Um módulo específico

```bash
pytest tests/test_spaced_repetition.py -v
```

### Verificar se todos passam antes de um commit

```bash
pytest tests/ -v --tb=short -q
```

### Módulos de teste

| Arquivo                           | O que testa                                                        |
|-----------------------------------|--------------------------------------------------------------------|
| `tests/test_health.py`            | Endpoint `GET /health`                                             |
| `tests/test_flashcards.py`        | `POST /ai/flashcards/generate` e `GET /ai/review/{userId}`         |
| `tests/test_analysis.py`          | `GET /ai/analysis/{userId}`                                        |
| `tests/test_llm_service.py`       | Geração de flashcards com LLM (mockado), parsing JSON, modelo usado |
| `tests/test_scraper_service.py`   | Descoberta dinâmica de slugs, parsers `__NEXT_DATA__`/DOM, save    |
| `tests/test_spaced_repetition.py` | Algoritmo SM-2 (6 casos) e queries SQL diretas (mockadas)          |

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
│   │   ├── analysis.py
│   │   └── scraper.py       # POST /ai/scrape
│   ├── services/            # Lógica de negócio
│   │   ├── llm_service.py         # Geração com LLM (provedor configurável)
│   │   ├── spaced_repetition.py   # SM-2 + queries PostgreSQL
│   │   └── scraper_service.py     # Playwright + get-or-create roadmap
│   └── schemas/             # Modelos Pydantic
│       ├── flashcard.py
│       └── analysis.py
├── tasks/
│   └── scraper_task.py      # Celery task (disparo manual)
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