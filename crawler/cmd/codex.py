from collections import defaultdict
import heapq
import json
from pathlib import Path
from typing import Any, Iterator

from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

from crawler.spiders import bosses, classes, followers, items, monsters, raids, spells
from crawler.translations import langs, TRANSLATION
from crawler.utils import href_keys

crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

base_lang = 'en'


def merge_and_sort(iter1: Iterator[Any], iter2: Iterator[Any]) -> Iterator[Any]:
    merged_iter = heapq.merge(iter1, iter2, key=lambda x: x['id'])
    return list(merged_iter)

def run(data_dir: Path, output: str = None, generate: bool = False):
    output = Path(output) if output else Path('index.json')
    index_dir = data_dir.joinpath('index')
    miss_dir = data_dir.joinpath('miss')
    if not generate:
        from twisted.internet import reactor, defer
        configure_logging()
        settings = get_project_settings()
        settings['LOG_LEVEL'] = 'INFO'
        settings['FEEDS'] = {
            f'{index_dir}/%(lang)s/%(name)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'overwrite': True,
            }
        }

        @defer.inlineCallbacks
        def crawl():
            runner = CrawlerRunner(settings=settings)
            for lang in langs:
                for crawler in crawlers:
                    runner.crawl(crawler.CodexSpider, lang=lang)
            yield runner.join()

            settings['FEEDS'] = {
                    f'{miss_dir}/%(lang)s/%(name)s.json': {
                        'format': 'json',
                        'encoding': 'utf8',
                        'store_empty': False,
                        'overwrite': True,
                    }
                }
            runner.settings = settings
            for _ in range(5):
                index_codex = {}
                scan_codex = {}
                for crawler in crawlers:
                    with open(index_dir.joinpath(base_lang, f'{crawler.CodexSpider.name}.json')) as f:
                        items = json.load(f)
                        index_codex[crawler.CodexSpider.name] = set()
                        for item in items:
                            index_codex[crawler.CodexSpider.name].add(item['id'])
                            for key in href_keys:
                                match = item.get(key)
                                if match:
                                    for m in match:
                                        category, id = m
                                        if category not in scan_codex:
                                            scan_codex[category] = set()
                                        scan_codex[category].add(id)

                stop_flag = True
                for crawler in crawlers:
                    key = crawler.CodexSpider.name
                    diff_set = scan_codex.get(
                        key, set()) - index_codex.get(key, set())
                    if len(diff_set) == 0:
                        continue
                    stop_flag = False
                    start_ids = list(diff_set)
                    for lang in langs:
                        runner.crawl(crawler.CodexSpider,
                                    lang=lang, start_ids=start_ids)
                if stop_flag:
                    break
                else:
                    yield runner.join()

                for crawler in crawlers:
                    key = crawler.CodexSpider.name
                    if not miss_dir.joinpath(base_lang, f'{key}.json').exists():
                        continue
                    with open(index_dir.joinpath(base_lang, f'{key}.json'), 'r+') as f_index, open(miss_dir.joinpath(base_lang, f'{key}.json'), 'r') as f_miss:
                        index, miss = json.load(f_index), json.load(f_miss)
                        merged = merge_and_sort(index, miss)
                        f_index.seek(0)
                        f_index.truncate()
                        json.dump(merged, f_index, ensure_ascii=True, indent=4)
            reactor.callFromThread(reactor.stop)

        crawl()
        reactor.run()

    codex = {}
    upgrade_materials = defaultdict(list)
    skills = defaultdict(dict)
    for lang in langs:
        codex[lang] = {}
        for crawler in crawlers:
            key = crawler.CodexSpider.name
            codex[lang][key] = {}
            with open(index_dir.joinpath(lang, f'{key}.json'), ) as f:
                items = json.load(f)
                for item in items:
                    codex[lang][key][item['id']] = item
                    if lang == base_lang:
                        if key in ('items'):
                            match = item.get('upgrade_materials')
                            if match:
                                for _, id in match:
                                    upgrade_materials[id].append(item['id'])
                        if key in ('monsters', 'raids', 'follwers', 'bosses'):
                            match = item.get('skills')
                            if match:
                                for _, id in match:
                                    if skills[id].get(key) is None:
                                        skills[id][key] = []
                                    skills[id][key].append(item['id'])
                                        

    index = {
        'codex': codex,
        'translation': TRANSLATION,
        'upgrade_materials': upgrade_materials,
        'skills': dict(skills),
    }

    with open(output, 'w') as f:
        json.dump(index, f, ensure_ascii=False)