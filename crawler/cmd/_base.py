from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def crawler(data_dir: Path, langs: list, crawlers: list):
    settings = get_project_settings()
    settings['FEEDS'] = {
        f'{data_dir}/%(lang)s/%(name)s.json': {
            'format': 'json',
            'encoding': 'utf8',
            'store_empty': False,
            'overwrite': True,
        }
    }
    settings['LOG_LEVEL'] = 'INFO'

    process = CrawlerProcess(settings)
    for crawler in crawlers:
        for lang in langs:
            process.crawl(crawler.CodexSpider, lang=lang)

    process.start()
