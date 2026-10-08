# Module 5: Monitoring

Offline evaluation can't tell you how your RAG system performs once real
people use it. This module covers online monitoring: collecting metrics
from real traffic and visualizing them on a dashboard.

We build a Streamlit chat app, capture metrics, store conversations
in PostgreSQL, and create Grafana dashboards for real-time monitoring.

## Lessons

Work through them in order:

1. [Intro](lessons/01-intro.md) - Why monitoring matters, what we'll build
2. [Assistant Setup](lessons/02-assistant-setup.md) - Setting up the RAG assistant
3. [Chat App](lessons/03-chat-app.md) - Basic Streamlit app with RAG
4. [Capturing Metrics](lessons/04-metrics.md) - LLMCallRecord, cost tracking
5. [Database](lessons/05-database.md) - PostgreSQL with Docker, saving conversations
6. [Querying Data](lessons/06-querying.md) - Fetching stored conversations
7. [Streamlit Dashboard](lessons/07-streamlit-dashboard.md) - Visualizing metrics in Streamlit
8. [User Feedback](lessons/08-user-feedback.md) - Thumbs up/down buttons
9. [Built-in Judge](lessons/09-built-in-judge.md) - LLM-as-a-judge for automatic relevance evaluation
10. [Feedback Dashboard](lessons/10-feedback-dashboard.md) - Adding feedback panels to the Streamlit dashboard
11. [Synthetic Data](lessons/11-synthetic-data.md) - Generating test data for dashboards
12. [Grafana Dashboards](lessons/12-grafana.md) - SQL queries and dashboard panels
13. [Docker Compose](lessons/13-docker-compose.md) - Running everything together
14. [Next Steps](lessons/14-next-steps.md) - OpenTelemetry, alerting, frameworks to learn more

## Run this project

This repository contains a local student-support RAG app, PostgreSQL request
logging, a Streamlit monitoring dashboard, and a provisioned Grafana dashboard.
After each generated answer, the app asks the configured LLM to score its
correctness, groundedness, and relevance against the retrieved FAQ context.
The evaluation and judge token usage are saved with the conversation and shown
in the chat and monitoring dashboard. This judge call uses the configured model
provider and consumes additional API tokens; the interface shows an evaluation
warning if judging fails while preserving the generated answer.

### Run the full stack with Docker Compose

1. Copy `.env.example` to `.env` and add an API key for the provider selected
   with `LLM_PROVIDER` (`GROQ_API_KEY` or `OPENAI_API_KEY`). Set your own local
   database and Grafana passwords before exposing these services beyond your
   machine.
2. From the project directory, start the services:

   ```powershell
   docker compose up --build -d
   ```

   The app initializes its PostgreSQL tables when it starts.
3. Open the Streamlit app at http://localhost:8501 and Grafana at
   http://localhost:3000. Grafana's initial username is `admin`; use the
   password configured in `GRAFANA_ADMIN_PASSWORD` (the development default is
   `admin`).

The PostgreSQL and Grafana data are kept in Docker volumes. Stop the stack with
`docker compose down`; use `docker compose down -v` only when you intend to
delete the stored monitoring data.

### Run Streamlit outside Docker

Start PostgreSQL with `docker compose up -d postgres`, set `DATABASE_URL` in
`.env` to use `localhost` as the database host, then initialize and run the app:

```powershell
uv sync
uv run python db_init.py
uv run streamlit run app.py
```

Run the standalone monitoring dashboard with `uv run streamlit run dashboard.py`.

To insert synthetic conversation and feedback records for dashboard testing, run:

```powershell
uv run python generate_data.py --count 25 --seed 42
```

### Deploy the chat app to Streamlit Community Cloud

1. Push the project files to a GitHub repository. Do not upload `.env` or `.venv`;
   `.gitignore` excludes them.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create
   app**, select your repository and branch, and set **Main file path** to
   `app.py`.
3. In the app's **Settings > Secrets**, add the key for your chosen provider.
   For Groq:

   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "your-groq-api-key"
   GROQ_MODEL = "llama-3.3-70b-versatile"
   ```

   Or for OpenAI:

   ```toml
   LLM_PROVIDER = "openai"
   OPENAI_API_KEY = "your-openai-api-key"
   OPENAI_MODEL = "gpt-4o-mini"
   ```

   Save the secrets and reboot the app if it has already been deployed. The app
   uses the local FAQ dataset without a database, but conversations and
   monitoring metrics will not be persisted. To enable the dashboard and
   persistence, also add a `DATABASE_URL` secret for a hosted PostgreSQL
   database; a database running on your own computer's `localhost` is not
   reachable from Streamlit Cloud.
