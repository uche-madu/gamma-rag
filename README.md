# Financial Advice Chatbot

This project is a **Financial Advice Chatbot** powered by **FastAPI, LangChain, LangGraph, and Supabase**. It leverages **pgvector** in Postgres to enable efficient vector search, uses **Nomic embeddings**, and integrates **Groq** for LLM-based responses. The chatbot provides financial insights based on web-scraped data from key sources.

## Features

- **Web Scraping Pipeline**: Uses Scrapy to extract financial data from the web.
- **GitHub Actions**: Automatically runs the web scraping job **every 6 hours**.
- **Postgres with pgvector**: Stores scraped data and enables vector-based retrieval.
- **Embeddings via Nomic API**: Converts scraped articles into vector format.
- **Automated Embedding Updates**:
  - Runs **10 seconds after FastAPI starts/restarts** via a background task in FastAPI.
  - Updates **every 6 hours** to match scraping frequency.
- **FastAPI Backend**:
  - User Authentication (Register/Login)
  - Embedding Articles
  - RAG Chat for Financial Advice
- **Swagger UI for API Testing**
- **Alembic for Database Migrations**

## Required Environment Variables

To run this project, set the following environment variables:

```env
SUPABASE_URL=
SUPABASE_KEY=
DATABASE_URL=postgresql+asyncpg://[USER]:[DBPASSWORD]@aws-0-xxxxxxxxxxx.pooler.supabase.com:5432/[DBTABLE]
SCRAPEOPS_API_KEY=
JWT_SECRET=
ALGORITHM="HS256"
GROQ_API_KEY=
NOMIC_API_KEY=
```
## Installation & Setup

### 1. Clone the Repository
```sh
 git clone https://github.com/uche-madu/gamma-rag.git
 cd gamma-rag
```

### 2. Install Dependencies
```sh
pip install uv
uv pip install -r requirements.txt
```

### 3. Run the FastAPI Server
```sh
uvicorn app.main:app --reload
```

### 4. Running the Scraper
To manually run the Scrapy spider, use:
```sh
cd stock_scraper
scrapy crawl news
```

## Database Migrations with Alembic

To set up database migrations with Alembic, follow these steps:

1. **Initialize Alembic** (run from the root folder):
   For async support, use:
   ```sh
   alembic init -t async alembic
   ```
2. **Configure `alembic.ini` and `env.py`** to point to the correct database URL.
3. **Generate a new migration script**:
   ```sh
   alembic revision --autogenerate -m "Initial migration"
   ```
4. **Review the generated migration script** before applying changes.
   - Not all database tables are created via FastAPI.
   - Tables such as `articles`, `documents` and the HNSW `index` are manually created using `supabase.sql` in the Supabase SQL Editor.
   - Ensure that the migration does not delete or overwrite existing tables.
5. **Apply the migration only after verification**:
   ```sh
   alembic upgrade head
   ```

## API Usage

### 1. Authentication

To interact with the API, users must **register and log in**:

- **Register**: `POST /auth/register` with `email`, `username`, and `password`.
- **Login**: `POST /auth/login` to obtain an authentication token.

Once logged in, users can access protected routes (lock icons in Swagger UI).

### 2. Chat for Financial Advice

- After logging in, visit `/chat` to ask financial questions.
- Currently, scraped data **only includes information for Nvidia, Google, and Tesla**.
- For better performance, restrict queries to these companies.
- Responses are generated based on a **prompt template** to maintain coherence.

## Tech Stack

- **FastAPI** (API & background tasks)
- **Scrapy** (Web Scraping)
- **Postgres + pgvector** (Database & vector search)
- **LangChain & LangGraph** (RAG & workflow management)
- **Groq** (LLM for financial advice generation)
- **Nomic** (Free API for embeddings)
- **Supabase** (Postgres database & auth management)
- **Alembic** (Database migrations)
- **GitHub Actions** (Scheduled scraping automation)

## Deployment & Automation

- Web scraping runs **every 6 hours via GitHub Actions**.
- The FastAPI background task ensures scraped data is embedded **every 6 hours**.
- The embedding process also triggers **10 seconds after the server starts/restarts**.
- Chat responses dynamically retrieve relevant embedded content via **RAG (Retrieval-Augmented Generation)**.

## Future Enhancements

- Expand scraping coverage to more companies & sources.
- Improve LLM response personalization with **user sentiment analysis**.
- Introduce voice & video-based responses.
- Optimize vector retrieval and search efficiency.

---

### 🚀 **Ready to test it out?**

1. **Run the FastAPI server**.
2. Visit Swagger UI (/docs) > **Register/Login** via any of the lock symbols.
3. Head to `/chat` and start asking questions about Nvidia, Google, or Tesla!

---

This project showcases a production-ready **LLM-powered RAG chatbot** with real-time updates and automated data ingestion.
