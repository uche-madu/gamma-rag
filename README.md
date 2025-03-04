# Financial Advice System - Stock Scraper

## Overview
The Financial Advice System for Stock Trading is a Retrieval-Augmented Generation (RAG) system designed to provide users with stock trading insights using real-time financial data. This system automatically scrapes financial news and discussions on NVIDIA (NVDA), Tesla (TSLA), and Alphabet (GOOG) every 6 hours, temporarily storing the data for analysis before deletion. The extracted data will later be processed into embeddings and stored in a vector database for efficient retrieval.

## Current Progress
### **Completed Tasks**
✅ **Task 1 - Data Scraping Mechanism**
- Implemented a Scrapy-based web scraper to collect news articles related to NVDA, TSLA, and GOOG.
- Integrated Supabase for temporary data storage.
- Ensured the scraper runs automatically every 6 hours using GitHub Actions.
- Handled duplicate entries gracefully to prevent redundant data storage.

✅ **Task 2 - Temporary Data Storage**
- Configured Supabase to store scraped articles.
- Implemented a system where articles are retained for 24 hours before automatic deletion using `pg_cron` in Supabase.
- Improved error handling in the Scrapy pipeline to log API errors instead of stopping execution.
- See `supabase.sql` for the database schema and scheduling implementation.

### **Upcoming Tasks**
🔜 **Task 3 - Vector Store for Text Retrieval**
- Process scraped text into embeddings using an embedding API.
- Store processed embeddings in Pinecone or Supabase as a vector database for retrieval.

🔜 **Task 4 - Financial Advice Query System**
- Implement a system where users can query stock trading insights.
- Retrieve relevant financial information from the vector store.
- Generate responses using an LLM-based reasoning engine.

🔜 **Task 5 - System Deployment and Usability**
- Develop an API or UI for users to interact with the system.
- Ensure responses are clear, accurate, and user-friendly.

## Features
- **Automated Financial News Scraping** – Scrapes stock-related news every 6 hours.
- **Temporary Data Storage** – Stores data for 24 hours before automatic deletion.
- **Duplicate Handling** – Skips redundant entries to maintain efficiency.
- **Error Logging** – Captures and logs Supabase API errors gracefully.
- **GitHub Actions Automation** – Ensures the scraper runs on schedule without manual intervention.

## Project Structure
```
├── .github
    |── workflows
    |   |──  scrapy.yml          # Workflow automation
├── README.md
└── stock_scraper
    ├── scrapy.cfg               # Scrapy project configuration
    ├── setup.py                 # Project setup
    ├── requirements.txt         # Dependencies
    ├── supabase.sql             # Database schema and scheduling code
    ├── stock_scraper
    │   ├── items.py              # Defines the data structure
    │   ├── middlewares.py        # Custom Scrapy middlewares
    │   ├── pipelines.py          # Handles data storage (Supabase integration)
    │   ├── settings.py           # Scrapy settings
    │   └── spiders
    │       └── news.py           # Main spider for extracting articles
```

## Installation
### **Prerequisites**
- Python 3.12+
- `uv` for package management
- Supabase account and API keys
- ScrapeOps Proxy API key
- PostgreSQL installed locally (for testing)
- Supabase CLI installed

### **Setup**
1. Clone the repository:
   ```sh
   git clone https://github.com/your-username/stock_scraper.git
   cd stock_scraper
   ```

2. Install dependencies:
   ```sh
   pip install uv
   uv pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory with the following values:
   ```ini
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   SCRAPEOPS_API_KEY=your_scrapeops_api_key
   ```

4. Install and configure PostgreSQL (for local development):
   ```sh
   sudo apt update && sudo apt install postgresql
   sudo systemctl start postgresql
   sudo -u postgres psql
   ```
   Inside the PostgreSQL shell, create a database and user:
   ```sql
   CREATE DATABASE stock_scraper;
   CREATE USER scraper_user WITH ENCRYPTED PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE stock_scraper TO scraper_user;
   ```

5. Install and configure Supabase CLI:
   ```sh
   curl -fsSL https://deb.supabase.com/setup | sh
   sudo apt install supabase-cli
   supabase link --project-ref your_project_ref
   ```

6. Apply the database schema from `supabase.sql`:
   ```sh
   supabase db push
   ```

## Running the Scraper
To manually run the Scrapy spider, use:
```sh
cd stock_scraper
scrapy crawl news
```

## Handling Errors Gracefully
- **Duplicate Key Errors** – Logged and skipped instead of breaking execution.
- **Supabase API Errors** – Logged without stopping the scraper.
- **General Debugging** – Logs are stored for debugging failed runs.

## GitHub Actions Workflow
The scraper runs automatically every 6 hours via GitHub Actions.
```yaml
name: Scrapy Spider Scheduler

on:
  schedule:
    - cron: "0 */6 * * *"  # Runs every 6 hours
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install uv and dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt

      - name: Set up environment variables
        run: |
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" >> $GITHUB_ENV
          echo "SUPABASE_KEY=${{ secrets.SUPABASE_KEY }}" >> $GITHUB_ENV
          echo "SCRAPEOPS_API_KEY=${{ secrets.SCRAPEOPS_API_KEY }}" >> $GITHUB_ENV

      - name: Run Scrapy Spider
        run: |
          cd stock_scraper
          scrapy crawl news
```

## Future Enhancements
- **Store processed text embeddings in Pinecone or Supabase** for efficient retrieval.
- **Enable LLM-based financial insights** using the scraped data.
- **Develop a query system** to allow users to ask stock-related questions.
- **Expand data sources** to include discussions from financial forums.
- **Improve monitoring** with a dashboard to track scraped data and insights.

## Contributors
- [Uche Madu](https://github.com/uche-madu)

## License
This project is licensed under the MIT License.

