# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os

from itemadapter import ItemAdapter
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class StockScraperPipeline:
    def process_item(self, item, spider):
        return item


class SupabasePipeline:
    def open_spider(self, spider):
        """Initialize Supabase client when the spider starts."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def process_item(self, item, spider):
        """Insert scraped data into Supabase."""
        data = dict(item)  # Convert Scrapy Item to dictionary
        response = self.supabase.table("articles").upsert([data]).execute()

        if response.data:
            spider.logger.info(f"Inserted article: {data['title']}")
        else:
            spider.logger.error(f"Failed to insert: {response}")

        return item  # Pass item to the next pipeline stage (if any)