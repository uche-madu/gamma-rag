# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class StockScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class NewsItem(scrapy.Item):
    url = scrapy.Field()
    stock_symbol = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    published_date = scrapy.Field()
    content = scrapy.Field()
    scraped_at = scrapy.Field()
