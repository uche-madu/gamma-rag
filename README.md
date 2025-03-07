# Gamma Financial Advice Chatbot

This project is a **Financial Advice Chatbot** powered by **FastAPI, LangChain, LangGraph, and Supabase**. It leverages **pgvector** in PostgreSQL for efficient vector search, uses **Nomic embeddings**, and integrates **Groq** for LLM-based responses. The chatbot provides financial insights based on web-scraped data from key sources.

## Live API Backend
The API is deployed and accessible at: [Live Backend](https://gamma-rag-financial-advisor.onrender.com/)
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Workflow

![Workflow Diagram](assets/gamma_financial_advisor.png)

## Features

- **Web Scraping Pipeline**: Uses Scrapy to extract financial data from the web.
- **GitHub Actions**: Automatically runs the web scraping job **every 6 hours**.
- **Postgres with pgvector**: Stores scraped data and enables vector-based retrieval.
- **Embeddings via Nomic API**: Converts scraped articles into vector format.
- **Automated Embedding Updates**:
  - Runs **10 seconds after FastAPI starts/restarts** via a background task.
  - Updates **every 6 hours** to match scraping frequency.
- **FastAPI Backend**:
  - User Authentication (Register/Login)
  - Embedding Articles
  - RAG Chat for Financial Advice
- **Sentiment Analysis**: Enhances response quality using TextBlob + VaderSentiment.
- **Swagger UI for API Testing**
- **Alembic for Database Migrations**

## Tech Stack

- **Backend:** FastAPI
- **Database & Vector Store:** Supabase (PostgreSQL with `pgvector` extension)
- **Web Scraping:** Scrapy
- **Embeddings:** Nomic (nomic-embed-text-v1.5)
- **LLM:** DeepSeek via Groq API (deepseek-r1-distill-llama-70b)
- **Orchestration:** LangGraph
- **Authentication:** FastAPI Users
- **Infrastructure:** GitHub Actions (for scheduled scraping jobs)

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

1. **Initialize Alembic**:
   ```sh
   alembic init -t async alembic
   ```
2. **Configure `alembic.ini` and `env.py`** with the correct database URL.
3. **Generate a new migration script**:
   ```sh
   alembic revision --autogenerate -m "Initial migration"
   ```
4. **Review the migration script** before applying changes.
5. **Apply the migration**:
   ```sh
   alembic upgrade head
   ```

## Workflow Breakdown

### 1. **News Scraping & Storage**
- Scrapy extracts financial news articles and stores them in the **articles table** in Supabase.
- The scraper runs **every 6 hours** via GitHub Actions.
- Supabase's `pg_cron` extension deletes articles older than **24 hours**:
  ```sql
  select cron.schedule(
      'delete_old_articles',
      '0 */6 * * *',
      $$ delete from articles where scraped_at < now() - interval '24 hours' $$
  );
  ```

### 2. **Embedding Generation & Vector Storage**
- A FastAPI background task retrieves **articles where `is_embedded=false`**.
- It chunks the content and calls **Nomic embeddings API**.
- The embeddings are stored in the **documents table** in Supabase with an HNSW index for fast retrieval.
- **Embedding model:**
  ```python
  embedding_model = NomicEmbeddings(
      model='nomic-embed-text-v1.5',
      inference_mode='remote',
      nomic_api_key=os.getenv('NOMIC_API_KEY')
  )
  ```

### 3. **Retrieval, Sentiment Analysis & Response Generation**
- The **retrieval service** fetches relevant articles using **match_documents function**.
- It filters results with **similarity >= 0.8**.
- The query undergoes **sentiment analysis using TextBlob + VaderSentiment**.
- The sentiment score is included in the LLM prompt.
- **LLM Model (DeepSeek via Groq API)**:
  ```python
  groq_llm = init_chat_model(
      model='deepseek-r1-distill-llama-70b',
      model_provider='groq',
      temperature=0.5
  )
  ```
- The response is streamed back to the user.

### 4. **Authentication & User Interaction**
- Users must **register and log in**:
  - **Register**: `POST /auth/register` with `email`, `username`, and `password`.
  - **Login**: `POST /auth/login` to obtain an authentication token.
- Authenticated users can access **/chat** for financial insights.
- Currently, scraped data is limited to **Nvidia, Google, and Tesla**.

## Deployment & Automation

- Web scraping runs **every 6 hours via GitHub Actions**.
- The FastAPI background task ensures embeddings update **every 6 hours**.
- The embedding process also triggers **10 seconds after server restart**.
- Chat responses dynamically retrieve relevant content via **RAG (Retrieval-Augmented Generation)**.

## Future Enhancements

- Expand scraping coverage to more companies & sources.
- Improve LLM response personalization with **user sentiment analysis**.
- Introduce voice & video-based responses.
- Optimize vector retrieval and search efficiency.

---

### 🚀 **Ready to test it out?**

1. **Run the FastAPI server**.
2. Visit Swagger UI (`/docs`) and **Register/Login**.
3. Go to `/chat` and start asking questions about Nvidia, Google, or Tesla!

**Chat & WebSocket Interaction**
- The chat endpoint is available via the API, documented in Swagger UI.
- An alternative WebSocket endpoint provides a more suitable interaction method:
  - **WebSocket URL:** `wss://gamma-rag-financial-advisor.onrender.com/chat/ws?token=USER_TOKEN`
## WebSocket Chat Testing  
You can test the WebSocket chat endpoint using the test script in the repository:  

[app/tests/test_websocket_chat.py](app/tests/test_websocket_chat.py)


---

This project showcases a production-ready **LLM-powered RAG chatbot** with real-time updates and automated data ingestion.












































# Financial Advice System - Workflow Documentation

## Overview
This document provides a detailed breakdown of the financial advice system, including its workflow, components, and technical implementation.

## Tech Stack
- **Backend:** FastAPI
- **Database & Vector Store:** Supabase (PostgreSQL with `pgvector` extension)
- **Scraping:** Scrapy
- **Embeddings:** Nomic (nomic-embed-text-v1.5)
- **LLM:** DeepSeek via Groq API (deepseek-r1-distill-llama-70b)
- **Orchestration:** LangGraph
- **Authentication:** FastAPI Users
- **Infrastructure:** GitHub Actions (for scheduled scraping jobs)

## Live API Backend
The API is deployed and accessible at: [Live Backend](https://gamma-rag-financial-advisor.onrender.com/)
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Workflow Breakdown

### 1. **News Scraping & Storage**
- Scrapy extracts financial news articles.
- Data is stored in the **articles table** in Supabase.
- The GitHub Actions workflow runs the scraper every **6 hours**.
- Schema of `articles` table:
  ```sql
  CREATE TABLE articles (
      id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
      url TEXT UNIQUE NOT NULL,
      stock_symbol TEXT NOT NULL,
      title TEXT,
      author TEXT,
      published_date TEXT,
      content TEXT,
      scraped_at TIMESTAMPTZ NOT NULL,
      is_embedded BOOLEAN DEFAULT FALSE
  );
  ```
- Supabase's `pg_cron` extension deletes articles older than **24 hours**:
  ```sql
  select cron.schedule(
      'delete_old_articles',
      '0 */6 * * *',
      $$ delete from articles where scraped_at < now() - interval '24 hours' $$
  );
  ```

### 2. **Embedding Generation & Vector Storage**
- A FastAPI background task retrieves **articles where `is_embedded=false`**.
- It chunks the article content and calls **Nomic embeddings API**.
- The generated embeddings are stored in the **documents table** in Supabase, which acts as a vector store.
- **Documents table schema:**
  ```sql
  CREATE TABLE documents (
      id UUID PRIMARY KEY,
      content TEXT,
      metadata JSONB,
      embedding VECTOR(768)
  );
  ```
- An **HNSW index** is created for fast approximate search:
  ```sql
  CREATE INDEX ON documents USING HNSW (embedding VECTOR_L2_OPS);
  ```
- The **embedding model** used:
  ```python
  embedding_model = NomicEmbeddings(
      model='nomic-embed-text-v1.5',
      inference_mode='remote',
      nomic_api_key=os.getenv('NOMIC_API_KEY')
  )
  ```
- After embedding, the system updates `is_embedded=true` in the articles table.

### 3. **Retrieval & Response Generation**
- When a user queries the system via `/chat` or WebSocket endpoint:
  - The **retrieval service** fetches relevant articles using **match_documents function**.
  - It **filters results with similarity >= 0.8**.
  - The retrieved data is injected into a **LangGraph prompt template**.
  ```sql
  CREATE FUNCTION match_documents (
      query_embedding VECTOR(768),
      filter JSONB DEFAULT '{}'
  ) RETURNS TABLE (
      id UUID,
      content TEXT,
      metadata JSONB,
      similarity FLOAT
  ) LANGUAGE plpgsql AS $$
  BEGIN
      RETURN QUERY
      SELECT id, content, metadata, 1 - (documents.embedding <=> query_embedding) AS similarity
      FROM documents
      WHERE metadata @> filter
      ORDER BY documents.embedding <=> query_embedding;
  END;
  $$;
  ```
- The **LLM (DeepSeek via Groq API)** generates a response.
  ```python
  groq_llm = init_chat_model(
      model='deepseek-r1-distill-llama-70b',
      model_provider='groq',
      temperature=0.5
  )
  ```
- The response is streamed back to the user.

### 4. **Chat & WebSocket Interaction**
- The chat endpoint is available via the API, documented in Swagger UI.
- An alternative WebSocket endpoint provides a more suitable interaction method:
  - **WebSocket URL:** `wss://gamma-rag-financial-advisor.onrender.com/chat/ws?token=THE_TOKEN`
- WebSocket chat can be tested using the script located at:
  ```
  app/tests/test_websocket_chat.py
  ```

### 5. **Authentication & User Interaction**
- The system uses **FastAPI Users** for authentication.
- Users sign up via `/auth/register` and log in.
- Authenticated users can query data via `/chat` API or WebSocket.

## Diagram (To be created in Excalidraw)
The diagram will illustrate the entire workflow, showing:
- **Scrapy fetching news articles**
- **Supabase storing raw articles**
- **Background tasks handling embedding generation**
- **Supabase's vector store handling retrieval**
- **LangGraph integrating embeddings with prompt templates**
- **Groq's LLM generating responses**
- **User interactions via FastAPI APIs and WebSockets**

## Next Steps
- **Design the Excalidraw diagram** with components, logos, and arrows for data flow.
- **Refine this document** based on additional details or future improvements.

