import heapq
from itertools import product
import json
from typing import Any, Iterator
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

from ..utils.exctractor import Exctractor
from ..utils.path_config import TmpPathConfig

from ..spiders import bosses, classes, followers, item_types, items, monsters, raids, spells

from twisted.internet import asyncioreactor
asyncioreactor.install()

crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]


def merge2sort(iter1: Iterator[Any], iter2: Iterator[Any]) -> Iterator[Any]:
    merged_iter = heapq.merge(iter1, iter2, key=lambda x: x['id'])
    return list(merged_iter)


def crawl_codex(settings: Settings):

    tmp_dir_config = TmpPathConfig(settings.get('TMP_DIR'))

    base_language = settings.get('BASE_LANGUAGE')
    languages = settings.get('SUPPORTED_LANGUAGES', [])
    json_feed = {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'overwrite': True,
    }

    from twisted.internet import reactor, defer

    configure_logging()

    @defer.inlineCallbacks
    def crawl():
        runner = CrawlerRunner(settings=settings)

        # All
        settings['FEEDS'] = {
            f'{tmp_dir_config.entries}/%(language)s/%(name)s.json': json_feed
        }
        runner.settings = settings
        for (language, crawler) in product(languages, crawlers):
            runner.crawl(crawler.Spider, language=language)
            yield runner.join()

        # ItemTypes
        settings['FEEDS'] = {
            f'{tmp_dir_config.itemtypes}/%(language)s.json': json_feed
        }
        runner.settings = settings
        for language in languages:
            runner.crawl(item_types.Spider, language=language,
                         name_only=(language != base_language))
            yield runner.join()

        # Miss
        settings['FEEDS'] = {
            f'{tmp_dir_config.miss}/%(language)s/%(name)s.json': json_feed
        }
        runner.settings = settings
        for _ in range(3):
            indexed = {}
            scanned = {}
            for crawler in crawlers:
                name = crawler.Spider.name
                with open(tmp_dir_config.entries.joinpath(base_language, f'{name}.json')) as f:
                    entries = json.load(f)
                    indexed[name] = set()
                    for e in entries:
                        indexed[name].add(e['id'])
                        for _, drop in e.get('drops', []):
                            for category, id in (Exctractor.extract_codex_id(m) for m in (d.get('href') for d in drop) if m):
                                if category not in scanned:
                                    scanned[category] = set()
                                scanned[category].add(id)

            flag = True
            for crawler in crawlers:
                name = crawler.Spider.name
                set_diff = scanned.get(name, set()) - indexed.get(name, set())
                if len(set_diff) == 0:
                    continue
                flag = False
                start_ids = list(set_diff)
                for language in languages:
                    runner.crawl(crawler.Spider, language=language,
                                 start_ids=start_ids)

            if flag:
                yield runner.stop()
                continue
            else:
                yield runner.join()

            for (language, crawler) in product(languages, crawlers):
                name = crawler.Spider.name
                miss_path = tmp_dir_config.miss.joinpath(
                    language, f'{name}.json')
                if miss_path.exists():
                    with open(miss_path) as f:
                        miss = json.load(f)
                else:
                    miss = []
                with open(tmp_dir_config.entries.joinpath(language, f'{name}.json'), 'r+') as f:
                    entries = json.load(f)
                    merged = merge2sort(entries, miss)
                    f.seek(0)
                    f.truncate()
                    json.dump(merged, f, ensure_ascii=False, indent=4)

        reactor.callFromThread(reactor.stop)

    crawl()
    reactor.run()


def run(settings: Settings):
    settings = get_project_settings()
    settings['LOG_LEVEL'] = 'INFO'
    crawl_codex(settings)
