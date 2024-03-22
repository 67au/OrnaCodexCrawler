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
from crawler.utils import href_keys, parse_codex_id

# Must: Items first, spells second
crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

base_lang = 'en'


def convert_key(key: str) -> str:
    return key.lower().replace(' ', '_').replace('.', '_').replace(':', '_') \
        .replace('↓', 'd').replace('↑', 'u').replace('/', '_').replace('\'', '_')


def merge_and_sort(iter1: Iterator[Any], iter2: Iterator[Any]) -> Iterator[Any]:
    merged_iter = heapq.merge(iter1, iter2, key=lambda x: x['id'])
    return list(merged_iter)


def run(data_dir: Path, output: str = None, generate: bool = False, target: str = None):
    output = Path(output) if output else None
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
                    runner.crawl(crawler.CodexSpider, lang=lang, target=target)
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
            for _ in range(3):
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
                                        category, id = parse_codex_id(m['href'])
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
                                    lang=lang, start_ids=start_ids, target=target)
                if stop_flag:
                    yield runner.stop()
                else:
                    yield runner.join()
                
                for lang in langs:
                    for crawler in crawlers:
                        category = crawler.CodexSpider.name
                        if not miss_dir.joinpath(lang, f'{category}.json').exists():
                            continue
                        with open(index_dir.joinpath(lang, f'{category}.json'), 'r+') as f_index, open(miss_dir.joinpath(lang, f'{category}.json'), 'r') as f_miss:
                            index, miss = json.load(f_index), json.load(f_miss)
                            merged = merge_and_sort(index, miss)
                            f_index.seek(0)
                            f_index.truncate()
                            json.dump(merged, f_index, ensure_ascii=True, indent=4)
        
            reactor.callFromThread(reactor.stop)

        crawl()
        reactor.run()
        

    if output:
        # Analysis
        # Load Items
        codex = {}
        for lang in langs:
            codex[lang] = {}
            for crawler in crawlers:
                category = crawler.CodexSpider.name
                codex[lang][category] = {}
                with open(index_dir.joinpath(lang, f'{category}.json'), ) as f:
                    items = json.load(f)
                    for item in items:
                        codex[lang][category][item['id']] = item

        # scan miss entries and transform href
        icons = {}

        def check_conflict_key(key: str, icon: str) -> str:
            new_key = key
            for ic in iter(lambda: icons.get(new_key), None):
                if ic == icon:
                    return new_key
                new_key = f'{new_key}_'
            icons[new_key] = icon
            return new_key

        miss_entries = {}
        translations = dict()
        for lang in langs:
            translations[lang] = defaultdict(dict)
            for crawler in crawlers:
                category = crawler.CodexSpider.name
                used = codex[lang][category]
                for used_id, item in used.items():
                    for key in href_keys:
                        match = item.get(key)
                        if match:
                            for i, m in enumerate(match):
                                href = m.get('href')
                                if href:
                                    cate, cid = parse_codex_id(href)
                                    if not (cid in codex[lang][cate]):
                                        miss_entries[f'{lang}/{cate}/{cid}'] = m
                                    used[used_id][key][i] = [cate, cid]

                    for key in ['rarity', 'useable_by', 'place', 'family', 'spell_type', 'target']:
                        match = item.get(key)
                        if match:
                            translations[lang][key][convert_key(
                                codex[base_lang][category][used_id][key])] = match
                # stats
                if category in {'items', 'followers'}:
                    for used_id, item in used.items():
                        match = item.get('stats')
                        if match:
                            for n, stat in enumerate(match):
                                if len(stat) == 2:
                                    translations[lang]['stats'][codex[base_lang][category][used_id]['stats'][n][0].lower(
                                    ).replace(' ', '_')] = stat[0]
                                if len(stat) == 1:
                                    translations[lang]['stats'][codex[base_lang][category][used_id]['stats'][n][0].lower(
                                    ).replace(' ', '_')] = stat[0]
                # status
                if category in {'items', 'spells'}:
                    for used_id, item in used.items():
                        for key in ['immunities', 'causes', 'cures', 'gives']:
                            match = item.get(key)
                            if match:
                                for n, status in enumerate(match):
                                    status_name = convert_key(
                                        codex[base_lang][category][used_id][key][n]['name'])
                                    status_name = check_conflict_key(status_name, status['icon'])
                                    translations[lang]['status'][status_name] = status['name']
                if category in {'spells'}:
                    for used_id, item in used.items():
                        for key in ['summons']:
                            match = item.get(key)
                            if match:
                                for n, summon in enumerate(match):
                                    summon_name = convert_key(
                                        codex[base_lang][category][used_id][key][n]['name'])
                                    summon_name = check_conflict_key(
                                        summon_name, summon['icon'])
                                    translations[lang]['summons'][summon_name] = summon['name']
                # list
                if category in {'bosses', 'monsters', 'raids', 'followers', 'items', 'spells'}:
                    for used_id, item in used.items():
                        for key in ['tags', 'event']:
                            match = item.get(key)
                            if match:
                                for n, m in enumerate(match):
                                    translations[lang][key][convert_key(
                                        codex[base_lang][category][used_id][key][n])] = m

        codex_base = defaultdict(dict)
        not_trans_keys = {'name', 'description', 'bestial_bond', 'abilities'}
        for crawler in crawlers:
            category = crawler.CodexSpider.name
            used = codex[base_lang][category]
            based = codex_base[category]
            for used_id, item in used.items():
                based[used_id] = {}
                for key in item.keys():
                    based[used_id][key] = used[used_id][key]

                    if key in {'rarity', 'useable_by', 'place', 'family', 'spell_type', 'target'}:
                        match = item.get(key)
                        if match:
                            based[used_id][key] = convert_key(match)

                    if category in {'items', 'followers'}:
                        if key == 'stats':
                            match = item.get('stats')
                            stat_dict = dict()
                            for stat in match:
                                stat_key = convert_key(stat[0])
                                if len(stat) == 2:
                                    stat_dict[stat_key] = stat[1]
                                if len(stat) == 1:
                                    if stat_key == 'two_handed':
                                        stat_dict[stat_key] = True
                                    else:
                                        stat_dict['element'] = stat[0].lower()
                            based[used_id]['stats'] = stat_dict

                    if category in {'items', 'spells'}:
                        if key in {'immunities', 'causes', 'cures', 'gives'}:
                            match = item.get(key)
                            based[used_id][key] = list()
                            for status in match:
                                status_name = convert_key(status['name'])
                                status_name = check_conflict_key(
                                    status_name, status['icon'])
                                if 'chance' in status:
                                    based[used_id][key].append(
                                        {'name': status_name, 'chance': status['chance']})
                                else:
                                    based[used_id][key].append(
                                        {'name': status_name})
                        if key in {'summons'}:
                            match = item.get(key)
                            based[used_id][key] = list()
                            for summon in match:
                                summon_name = convert_key(summon['name'])
                                summon_name = check_conflict_key(
                                    summon_name, summon['icon'])
                                based[used_id][key].append(
                                    {'name': summon_name, 'chance': summon['chance']})
                    if category in {'bosses', 'monsters', 'raids', 'followers', 'items', 'spells'}:
                        if key in {'tags', 'event'}:
                            match = item.get(key)
                            based[used_id][key] = list()
                            for m in match:
                                based[used_id][key].append(convert_key(m))

                    if key in not_trans_keys:
                        if key != 'name':
                            del based[used_id][key]

        upgrade_materials = defaultdict(list)
        skills = defaultdict(dict)
        ability_items = defaultdict(list)
        offhand_skills = dict()
        for crawler in crawlers:
            category = crawler.CodexSpider.name
            for id, item in codex[base_lang][category].items():
                if category in ('items'):
                    match = item.get('upgrade_materials')
                    if match:
                        for _, id in match:
                            upgrade_materials[id].append(item['id'])
                    # Must: Items first, spells second
                    match = item.get('ability')
                    if match:
                        ability_items[match[0]].append(item['id'])
                if category in ('spells'):
                    # spells second
                    match = item['name'].endswith(' (Off-hand)')
                    if match:
                        name = item['name'][:-11]
                        if name in ability_items:
                            offhand_skills[item['id']] = ability_items[name]
                if category in ('monsters', 'raids', 'followers', 'bosses'):
                    match = item.get('skills')
                    if match:
                        for _, id in match:
                            if skills[id].get(category) is None:
                                skills[id][category] = []
                            skills[id][category].append(item['id'])

        meta = {
            'base': codex_base,
            'extra': {
                'not_trans_keys': list(not_trans_keys),
                'icons': icons,
                'miss_entries': miss_entries,
                'upgrade_materials': upgrade_materials,
                'skills': dict(skills),
                'offhand_skills': dict(offhand_skills),
                'offhand_items': {item: spell for spell, items in offhand_skills.items() for item in items},
            },
        }

        with open(output, 'w') as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
            print('output:', output)

        for lang in langs:
            output_lang = output.parent.joinpath(f'{output.stem}.{lang}.json')
            with open(output_lang, 'w') as f:
                base = {}
                for category, c in codex[lang].items():
                    base[category] = {}
                    for id, item in c.items():
                        item_lang = {}
                        for key in not_trans_keys:
                            value = item.get(key)
                            if value:
                                item_lang[key] = value
                        base[category][id] = item_lang
                codex_lang = {
                    'base': base,
                    'meta': translations[lang],
                    'key': TRANSLATION[lang],
                }
                json.dump(codex_lang, f, ensure_ascii=False, indent=4)
                print('output:', output_lang)
