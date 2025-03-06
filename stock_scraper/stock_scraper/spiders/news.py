import os
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse
from dateutil import parser
from dotenv import load_dotenv
import scrapy

from ..items import NewsItem

load_dotenv()


SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

def get_proxy_url(url):
    payload = {'api_key': SCRAPEOPS_API_KEY, 'url': url}
    proxy_url = 'https://proxy.scrapeops.io/v1/?' + urlencode(payload)
    return proxy_url


class NewsSpider(scrapy.Spider):
    name = "news"
    allowed_domains = ["finance.yahoo.com", "proxy.scrapeops.io"]
    start_urls = [
        "https://finance.yahoo.com/quote/NVDA/news",
        "https://finance.yahoo.com/quote/TSLA/news",
        "https://finance.yahoo.com/quote/GOOG/news"
    ]

    def start_requests(self):
        """Route all initial URLs through the ScrapeOps proxy."""
        for url in self.start_urls:
            stock_symbol = url.split("/")[-2]  # Extract "NVDA", "TSLA", "GOOG"
            yield scrapy.Request(
                url=get_proxy_url(url),
                callback=self.parse,
                meta={"stock_symbol": stock_symbol, "original_url": url}
            )

    def parse(self, response):
        """Extracts article links from Yahoo Finance stock pages."""
        stock_symbol = response.meta["stock_symbol"]

        articles = response.xpath('//ul[contains(@class, "stream-items")]//a[contains(@class, "subtle-link")]')
        for article in articles:
            article_url = article.xpath("./@href").get()

            # Convert relative URLs to absolute
            if article_url and not article_url.startswith("http"):
                article_url = response.urljoin(article_url)

            yield scrapy.Request(
                url=get_proxy_url(article_url),
                callback=self.parse_article,
                meta={"stock_symbol": stock_symbol, "original_url": article_url}
            )

    def parse_article(self, response):
        """Extracts details from the news article page."""
        stock_symbol = response.meta["stock_symbol"]

        # Extract the actual Yahoo Finance URL
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        actual_url = query_params.get("url", [response.meta["original_url"]])[0]  # Fallback if proxy failed

        title = response.xpath('//div[contains(@class, "cover-title")]/text()').get()
        published_date = response.xpath('//time[@class="byline-attr-meta-time"]/@datetime').get()

        # Convert published_date to UTC
        if published_date:
            try:
                dt = parser.parse(published_date)  # Parse the date
                dt = dt.astimezone(timezone.utc)  # Convert to UTC
                published_date = dt.isoformat()  # Format as string
            except Exception as e:
                self.logger.error(f"Failed to parse date {published_date}: {e}")
                published_date = None  # Handle parsing failure gracefully



        content = " ".join(response.xpath('//div[contains(@class, "body")]//p[contains(@class, "yf-1090901")]//text()').getall()).strip()

        # Extract author
        author_div = response.xpath('//div[contains(@class, "byline-attr-author")]')
        author = author_div.xpath('.//a/text()').get() or author_div.xpath('normalize-space(text())').get()
        if author and "(" in author:
            match = re.search(r"\((.*?)\)", author)
            if match:
                author = match.group(1)

        # Create NewsItem
        item = NewsItem(
            url=actual_url,  # Store the corrected URL
            stock_symbol=stock_symbol,
            title=title,
            author=author.strip() if author else "Unknown",
            published_date=published_date,
            content=content,
            scraped_at=datetime.now(timezone.utc).isoformat()
        )

        yield item  # This sends data to the Item Pipeline
