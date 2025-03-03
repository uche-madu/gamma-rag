import re
import sqlite3
from datetime import datetime, timezone
import scrapy

class NewsSpider(scrapy.Spider):
    name = "news"
    allowed_domains = ["finance.yahoo.com"]
    start_urls = [
        "https://finance.yahoo.com/quote/NVDA/news",
        "https://finance.yahoo.com/quote/TSLA/news",
        "https://finance.yahoo.com/quote/GOOG/news"
    ]

    def __init__(self, *args, **kwargs):
        """Initialize database connection and create table if it doesn't exist."""
        super().__init__(*args, **kwargs)
        self.conn = sqlite3.connect("articles.db")  # SQLite database
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,
                stock_symbol TEXT,
                title TEXT,
                author TEXT,
                published_date TEXT,
                content TEXT,
                scraped_at TEXT
            )
            """
        )
        self.conn.commit()

    def parse(self, response):
        """Extract news article links from Yahoo Finance stock pages and follow them."""
        stock_symbol = response.url.split("/")[-3]  # Extract NVDA, TSLA, or GOOG

        articles = response.xpath('//ul[contains(@class, "stream-items")]//a[contains(@class, "subtle-link")]')

        for article in articles:
            article_url = article.xpath("./@href").get()

            # Ensure absolute URL format
            if article_url and not article_url.startswith("http"):
                article_url = response.urljoin(article_url)

            # Check if the article URL is already scraped
            self.cursor.execute("SELECT url FROM articles WHERE url=?", (article_url,))
            if self.cursor.fetchone():
                self.logger.info(f"Skipping already scraped article: {article_url}")
                continue  # Skip scraping this URL

            yield response.follow(article_url, self.parse_article, meta={"stock": stock_symbol})

    def parse_article(self, response):
        """Extract details from the news article page."""
        stock_symbol = response.meta["stock"]

        # Extract title
        title = response.xpath('//div[contains(@class, "cover-title")]/text()').get()

        # Extract published date
        published_date = response.xpath('//time[@class="byline-attr-meta-time"]/@datetime').get()

        # Extract all text within each <p> tag (including inside <a> tags)
        content = " ".join(response.xpath('//div[contains(@class, "body")]//p[contains(@class, "yf-1090901")]//text()').getall()).strip()

        # Extract author (handling different formats)
        author_div = response.xpath('//div[contains(@class, "byline-attr-author")]')

        # Try to get author from <a> tag first
        author = author_div.xpath('.//a/text()').get()

        if not author:
            author = author_div.xpath('normalize-space(text())').get()
            if author and "(" in author:
                match = re.search(r"\((.*?)\)", author)
                if match:
                    author = match.group(1)

        # Save the article to the database
        self.cursor.execute(
            """
            INSERT INTO articles (url, stock_symbol, title, author, published_date, content, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (response.url, stock_symbol, title, author.strip() if author else "Unknown", published_date, content, datetime.now(timezone.utc).isoformat())
        )
        self.conn.commit()

        yield {
            "stock": stock_symbol,
            "title": title,
            "author": author.strip() if author else "Unknown",
            "published_date": published_date,
            "content": content,
            "url": response.url,
        }

    def closed(self, reason):
        """Close the database connection when the spider finishes."""
        self.conn.close()
