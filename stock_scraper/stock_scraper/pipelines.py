# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os

from itemadapter import ItemAdapter
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

load_dotenv()

class StockScraperPipeline:
    def process_item(self, item, spider):
        return item


class SupabasePipeline:
    def open_spider(self, spider):
        """Initialize Supabase client when the spider starts."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        if self.supabase_url and self.supabase_key:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def process_item(self, item, spider):
        """Insert scraped data into Supabase with error handling."""
        data = dict(item)  # Convert Scrapy Item to dictionary

        try:
            response = self.supabase.table("articles").upsert([data]).execute()

            if response.data:
                spider.logger.info(f"Inserted article: {data['title']}")
            else:
                spider.logger.error(f"Failed to insert: {response}")

        except APIError as e:
            error_msg = str(e)
            spider.logger.error(f"Supabase API Error: {error_msg}")

            # If it's a duplicate key error, log and skip
            if "duplicate key value" in error_msg:
                spider.logger.info(f"Skipping duplicate entry: {data['url']}")
                return item  # Continue processing other items

            # Otherwise, re-raise the error
            raise e

        return item  # Pass item to the next pipeline stage (if any)
