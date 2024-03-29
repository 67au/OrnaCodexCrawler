# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

from .utils import parse_codex_id, href_keys

class CrawlerPipeline:

    async def process_item(self, item, spider):
        return item

class HrefPipeline:

    async def process_item(self, item: ItemAdapter, spider):
        for key in href_keys:
            match = item.get(key)
            if match:
                for i, m in enumerate(match):
                    href = m.get('href')
                    if href:
                        item[key][i] = parse_codex_id(href)
        return item
