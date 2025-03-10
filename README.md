# Gamma Financial Advice Chatbot

This project is a **Financial Advice Chatbot** powered by **FastAPI, LangChain, LangGraph, and Supabase**. It leverages **pgvector** in PostgreSQL for efficient vector search, uses **Nomic embeddings**, and integrates **Groq** for LLM-based responses. The chatbot provides financial insights based on web-scraped data from key sources.

## Live API Backend
The API is deployed and accessible at: [Live Backend](https://gamma-rag-financial-advisor.onrender.com/)
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Workflow

![Project Diagram](assets/gamma_financial_advisor.png)

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
- Conditionally, after 6 user messages in a single thread, the previous messages
  are summarized via an LLM call.
  ```python
  llama3_70b_llm = init_chat_model( 
    model="llama3-70b-8192", 
    model_provider="groq",
    temperature=0.5
  )
  ```
- The response is streamed back to the user.

![Langraph Workflow Diagram](assets/state_graph.png)

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


## API Endpoints

### **Authentication & User Management**
**Base URL:** `/auth`

- `POST /auth/jwt/login` - Authenticate users with JWT.
- `POST /auth/register` - Register a new user.
- `POST /auth/reset-password` - Reset user password.
- `POST /auth/verify` - Verify user email.
- `GET /users/me` - Get the current authenticated user.
- `PATCH /users/me` - Update the current user profile.
- `GET /users/{user_id}` - Fetch a user by ID (admin access).
- `DELETE /users/{user_id}` - Delete a user by ID (admin access).

### **Articles & Embeddings**
**Base URL:** `/articles`

- `POST /articles/{article_id}/embed` - Start embedding a specific article (async).
- `POST /articles/embed-all` - Start embedding all unprocessed articles (async).

### **AI Chat (REST API)**
**Base URL:** `/chat`

- `POST /chat/` - Process user queries and generate AI responses using retrieval-augmented generation (RAG).

### **AI Chat (WebSocket)**
**Base URL:** `/chat/ws`

- `WebSocket /chat/ws?token=<JWT_TOKEN>` - Connect to the real-time AI chat WebSocket.
- Allows streaming AI-generated responses.
- Users must authenticate via a JWT token.

---

This project showcases a production-ready **LLM-powered RAG chatbot** with real-time updates and automated data ingestion.
