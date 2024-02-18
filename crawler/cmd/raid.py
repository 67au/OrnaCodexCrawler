import json
from pathlib import Path

from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

from crawler.spiders import raids, items
from crawler.translations import langs

def run(data_dir: Path, output: str = None, generate: bool = False):
    output = Path(output) if output else Path('raid-hp.json')
    index_dir = data_dir.joinpath('index')
    if not generate:
        from twisted.internet import reactor, defer
        configure_logging()
        settings = get_project_settings()
        settings['FEEDS'] = {
            f'{index_dir}/%(lang)s/%(name)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'overwrite': True,
            }
        }
        settings['LOG_LEVEL'] = 'INFO'
        @defer.inlineCallbacks
        def crawl():
            runner = CrawlerRunner(settings=settings)
            yield runner.crawl(items.CodexSpider, lang='en')
            raid = set()
            with open(index_dir.joinpath('en', 'items.json')) as f:
                item = json.load(f)
                for i in item:
                    for d in i.get('dropped_by', []):
                        if d[0] == 'raids':
                            raid.add(d[1])
            for lang in langs:
                runner.crawl(raids.CodexSpider, lang=lang, start_ids=list(raid))
            yield runner.join()
            reactor.stop()
        crawl()
        reactor.run()

    raid = dict()
    for lang in langs:
        with open(index_dir.joinpath(lang, 'raids.json'), 'r') as fp:
            d = json.load(fp)
            for item in d:
                if raid.get(item['id']) is None:
                    raid[item['id']] = {'name': {}}
                raid[item['id']]['name'][lang] = item['name']
                if raid[item['id']].get('hp') is None:
                    raid[item['id']]['tier'] = int(item['tier'])
                    raid[item['id']]['hp'] = int(item['hp'])
                    raid[item['id']]['icon'] = item['icon']

    with open(output, 'w', encoding='utf-8') as fp:
        json.dump(raid, fp, indent=4, ensure_ascii=False, sort_keys=True)
