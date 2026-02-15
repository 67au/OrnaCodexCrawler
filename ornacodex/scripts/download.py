from collections import defaultdict
from itertools import product
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Iterator
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

from ..utils.exctractor import Exctractor
from ..utils.path_config import TmpPathConfig

from ..patches.unindexed_urls import unindexed_urls

from ..spiders import bosses, classes, followers, item_types, items, monsters, raids, spells

from twisted.internet import asyncioreactor
asyncioreactor.install()

crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]


def merge2sort(iter1: Iterator[Any], iter2: Iterator[Any]) -> Iterator[Any]:
    return sorted({it['id']: it for it in iter1+iter2}.values(), key=lambda x: x['id'])


def urls2dict(urls: Iterator[str]):
    d = defaultdict(set)
    for url in urls:
        catergory, id = Exctractor.extract_codex_id(url)
        d[catergory].add(id)
    return d


def crawl_codex(settings: Settings, output: Path = None, **kwargs):
    patches_enabled = settings.get('PATCHES_ENABLED')

    tmp_dir_config = TmpPathConfig(output or 'tmp')
    if (tmp_dir_config.root.exists() and tmp_dir_config.root.is_dir()):
        shutil.rmtree(tmp_dir_config.root)
    tmp_dir_config.root.mkdir(parents=True, exist_ok=True)

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
    # disable logging
    logging.getLogger('scrapy.middleware').setLevel(logging.WARNING)
    logging.getLogger('scrapy.statscollectors').setLevel(logging.WARNING)

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

        # 索引结果
        indexed = set()
        # 扫描结果
        scanned = set(unindexed_urls if patches_enabled else [])

        def update_scan(files_dir: Path):
            for crawler in crawlers:
                category = crawler.Spider.name
                file_path = files_dir.joinpath(base_language, f'{category}.json')
                if file_path.exists():
                    with open(file_path) as f:
                        entries = json.load(f)
                        for entry in entries:
                            indexed.add(f'/codex/{category}/{entry["id"]}/')
                            for _, drops in entry.get('drops', []):
                                scanned.update(filter(lambda x: x is not None,
                                                      (drop.get('href') for drop in drops)))

        def backup(files_dir):
            bak = dict()
            for (language, crawler) in product(languages, crawlers):
                category = crawler.Spider.name
                file_path = files_dir.joinpath(language, f'{category}.json')
                if file_path.exists():
                    with open(file_path) as f:
                        entries = json.load(f)
                        bak[f'{category}/{language}'] = entries
            return bak

        def merge_backup(files_dir, bak):
            for (language, crawler) in product(languages, crawlers):
                category = crawler.Spider.name
                name = f'{category}/{language}'
                file_path = files_dir.joinpath(language, f'{category}.json')
                entries_bak = bak.get(name, [])

                if any(entries_bak) and not file_path.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'r+') as f:
                        json.dump(entries_bak, f, ensure_ascii=False, indent=4)

                if file_path.exists():
                    with open(file_path, 'r+') as f:
                        entries = json.load(f)
                        merged = merge2sort(entries, entries_bak)
                        f.seek(0)
                        f.truncate()
                        json.dump(merged, f, ensure_ascii=False, indent=4)

        update_scan(tmp_dir_config.entries)

        n = 0
        for _ in iter(lambda: scanned.issubset(indexed) or n > 2, True):
            backup_missed = backup(tmp_dir_config.miss)
            n += 1
            urls_dict = urls2dict(scanned - indexed)
            
            for crawler in crawlers:
                name = crawler.Spider.name
                start_ids = urls_dict.get(name, [])
                if len(start_ids) > 0:
                    for language in languages:
                        runner.crawl(crawler.Spider, language=language,
                                     start_ids=start_ids)
            yield runner.join()

            update_scan(tmp_dir_config.miss)
            merge_backup(tmp_dir_config.miss, backup_missed)
            invalid = scanned - indexed
            if (len(invalid) > 0):
                print('Invalid patched entries:', ', '.join(invalid))
                indexed = indexed - invalid

        merge_backup(tmp_dir_config.entries, backup(tmp_dir_config.miss))

        yield runner.stop()
        reactor.callFromThread(reactor.stop)

    crawl()
    reactor.run()


def run(settings: Settings, **kwargs):
    settings['LOG_LEVEL'] = 'INFO'
    
    crawl_codex(settings, **kwargs)
