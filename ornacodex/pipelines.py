# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import scrapy
from scrapy.pipelines.files import FilesPipeline


class OrnacodexPipeline:
    def process_item(self, item, spider):
        return item


class IconFilesPipeline(FilesPipeline):

    def get_media_requests(self, item, info):
        for image in item['file_urls']:
            yield scrapy.Request(image, meta={'icon': item['icon'].strip('/')})

    def file_path(self, request: scrapy.Request, response=None, info=None, *, item=None):
        image_filepath = request.meta.get('icon')
        return image_filepath
