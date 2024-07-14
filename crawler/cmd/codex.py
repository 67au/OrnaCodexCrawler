from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from itertools import product
import heapq
import json
from pathlib import Path
from typing import Any, Iterator

from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings

from crawler.spiders import bosses, classes, followers, item_types, items, monsters, raids, spells
from crawler.translations import langs, TRANSLATION
from crawler.utils import href_keys, parse_codex_id

# Must: Items first, spells second
crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

base_lang = 'en'


@cache
def convert_key(key: str) -> str:
    return key.lower().replace(' ', '_').replace('.', '_').replace(':', '_') \
        .replace('↓', 'd').replace('↑', 'u').replace('/', '_').replace('\'', '_')


def merge_and_sort(iter1: Iterator[Any], iter2: Iterator[Any]) -> Iterator[Any]:
    merged_iter = heapq.merge(iter1, iter2, key=lambda x: x['id'])
    return list(merged_iter)


json_feed = {
    'format': 'json',
    'encoding': 'utf8',
    'store_empty': False,
    'overwrite': True,
}


def crawl_codex(target: str, data_dir: Path):
    entries_dir = data_dir.joinpath('entries')
    miss_dir = data_dir.joinpath('miss')
    item_types_dir = data_dir.joinpath('item_types')

    from twisted.internet import reactor, defer
    configure_logging()
    settings = get_project_settings()
    settings['LOG_LEVEL'] = 'INFO'

    @defer.inlineCallbacks
    def crawl():
        runner = CrawlerRunner(settings=settings)

        # all
        settings['FEEDS'] = {
            f'{entries_dir}/%(lang)s/%(name)s.json': json_feed
        }
        runner.settings = settings
        for (lang, crawler) in product(langs, crawlers):
            runner.crawl(crawler.CodexSpider, lang=lang, target=target)
            yield runner.join()

        # item_type
        settings['FEEDS'] = {
            f'{item_types_dir}/%(lang)s/%(name)s.json': json_feed
        }
        runner.settings = settings
        for lang in langs:
            runner.crawl(item_types.ItemTypesSpider, lang=lang,
                         target=target, name_only=(lang != base_lang))
        yield runner.join()

        # miss
        settings['FEEDS'] = {
            f'{miss_dir}/%(lang)s/%(name)s.json': json_feed
        }
        runner.settings = settings
        for _ in range(3):
            index_codex = {}
            scan_codex = {}
            for crawler in crawlers:
                name = crawler.CodexSpider.name
                with open(entries_dir.joinpath(base_lang, f'{name}.json')) as f:
                    items = json.load(f)
                    index_codex[name] = set()
                    for item in items:
                        index_codex[name].add(item['id'])
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
                    runner.crawl(crawler.CodexSpider, lang=lang,
                                 start_ids=start_ids, target=target)
            if stop_flag:
                yield runner.stop()
            else:
                yield runner.join()

            for (lang, crawler) in product(langs, crawlers):
                category = crawler.CodexSpider.name
                if not miss_dir.joinpath(lang, f'{category}.json').exists():
                    continue
                with open(entries_dir.joinpath(lang, f'{category}.json'), 'r+') as f_index, open(miss_dir.joinpath(lang, f'{category}.json'), 'r') as f_miss:
                    index, miss = json.load(f_index), json.load(f_miss)
                    merged = merge_and_sort(index, miss)
                    f_index.seek(0)
                    f_index.truncate()
                    json.dump(merged, f_index, ensure_ascii=True)

        reactor.callFromThread(reactor.stop)

    crawl()
    reactor.run()


Entries = dict[str, dict[str, dict[str, dict]]]


def load(entries_dir: Path) -> Entries:
    entries: Entries = {lang: {} for lang in langs}
    for (lang, crawler) in product(langs, crawlers):
        category = crawler.CodexSpider.name
        with open(entries_dir.joinpath(lang, f'{category}.json'), 'r') as f:
            items = json.load(f)
            entries[lang][category] = {item['id']: item for item in items}
    return entries


def load_item_type(item_types_dir: Path):
    item_types = {}
    for lang in langs:
        with open(item_types_dir.joinpath(lang, 'item_types.json'), 'r') as f:
            item_types[lang] = json.load(f)
    return item_types


translate_keys = {'rarity', 'useable_by',
                  'place', 'family', 'spell_type', 'target'}

href_keys = {'dropped_by', 'upgrade_materials', 'skills',
             'learned_by', 'requirements', 'drops', 'celestial_classes'}

status_keys = {'immunities', 'causes', 'cures', 'gives'}

not_trans_keys = {'name', 'description'}


@dataclass
class ScanResult:
    translations: dict
    miss: dict
    abilities: dict
    icons: dict = field(default_factory=lambda: {})

    spells: dict = field(default_factory=lambda: {})
    materials: dict = field(default_factory=lambda: defaultdict(list))
    offhand_items: dict = field(default_factory=lambda: defaultdict(list))
    offhand_skills: dict = field(default_factory=lambda: {})
    skills: dict = field(default_factory=lambda: defaultdict(list))

    def check_conflict_key(self, key: str, icon: str) -> str:
        new_key = key
        for ic in iter(lambda: self.icons.get(new_key), None):
            if ic == icon:
                return new_key
            new_key = f'{new_key}_'
        self.icons[new_key] = icon
        return new_key

    def check_conflict_ability(self, key: str, ability: dict) -> str:
        new_key = key
        for ab in iter(lambda: self.abilities[base_lang].get(new_key), None):
            if ab.get('description') == ability.get('description'):
                return new_key
            new_key = f'{new_key}_'
        return new_key        

    def get_spells_id(self, name: str):
        return self.spells.get(name)


def scan(entries: Entries):
    result = ScanResult(
        translations={lang: defaultdict(dict) for lang in langs},
        miss={lang: defaultdict(dict) for lang in langs},
        abilities={lang: {} for lang in langs},
    )

    event_conflict = {lang: {} for lang in langs}

    entries_base = entries[base_lang]
    for (lang, crawler) in product(langs, crawlers):
        category = crawler.CodexSpider.name
        tl = result.translations[lang]
        used = entries[lang][category]
        base = entries_base[category]
        for uid, entry in used.items():

            # check miss
            for key in href_keys:
                m = entry.get(key, [])
                for index, drop in enumerate(m):
                    href = drop.get('href')
                    if href:
                        drop_category, drop_id = parse_codex_id(href)
                        if drop_id not in entries[lang][drop_category]:
                            if result.miss[lang][drop_category].get(drop_id) is None:
                                result.miss[lang][drop_category][drop_id] = drop

            # translate
            # default
            for key in translate_keys:
                m = entry.get(key)
                if m:
                    tl[key][convert_key(base[uid][key])] = m

            # stats
            if category in {'items', 'followers'}:
                m = entry.get('stats', [])
                for index, stat in enumerate(m):
                    stat_base = base[uid]['stats'][index]
                    if stat_base[0] == 'element':
                        tl['stats'][convert_key(stat_base[1])] = stat[1]
                    else:
                        tl['stats'][convert_key(stat_base[0])] = stat[0]

            # status
            if category in {'items', 'spells'}:
                for key in status_keys:
                    m = entry.get(key, [])
                    for index, status in enumerate(m):
                        status_name = convert_key(
                            base[uid][key][index]['name'])
                        status_name = result.check_conflict_key(
                            status_name, status['icon'])
                        tl['status'][status_name] = status['name']

            if category in {'spells'}:
                key = 'summons'
                m = entry.get(key, [])
                for index, summon in enumerate(m):
                    summon_name = convert_key(base[uid][key][index]['name'])
                    summon_name = result.check_conflict_key(
                        summon_name, summon['icon'])
                    tl['summon'][summon_name] = summon['name']

            if category in {'bosses', 'monsters', 'raids', 'followers', 'items', 'spells'}:
                for key in ['tags', 'event']:
                    m = entry.get(key, [])
                    for index, tag in enumerate(m):
                        tag_key = convert_key(base[uid][key][index])
                        if key == 'event':
                            if event_conflict[lang].get(tag_key, False):
                                continue
                            else:
                                if len(m) == 1:
                                    event_conflict[lang][tag_key] = True
                        tl[key][tag_key] = tag

            if category in {'followers'}:
                key = 'bestial_bond'
                m = entry.get(key, [])
                for index, bond in enumerate(m):
                    tl['levels'][index+1] = bond['name']
                    for i, b in enumerate(bond['values']):
                        b_base = base[uid][key][index]['values'][i]
                        if b_base['type'] == 'bonus':
                            b_key = convert_key(b_base['name'])
                            tl['stats'][b_key] = b['name']
                        if b_base['type'] == 'bond':
                            b_key = convert_key(b_base['name'])
                            tl['bonds'][b_key] = b['name']

            if category in {'raids', 'bosses', 'monsters', 'classes'}:
                key = 'abilities'
                m = entry.get(key, [])
                for index, ability in enumerate(m):
                    a_base = base[uid][key][index]
                    a_key = convert_key(a_base['name'])
                    a_key = result.check_conflict_ability(a_key, a_base)
                    result.abilities[lang][a_key] = ability


    for crawler in crawlers:
        category = crawler.CodexSpider.name
        for uid, entry in entries_base[category].items():
            if category in {'items'}:
                m = entry.get('upgrade_materials', [])
                for t in m:
                    _, id = parse_codex_id(t['href'])
                    result.materials[id].append(entry['id'])
                m = entry.get('ability')
                if m:
                    result.offhand_items[m['name']].append(entry['id'])
            if category in {'spells'}:
                if entry['name'].endswith(' (Off-hand)'):
                    result.offhand_skills[entry['name'][:-11]] = uid
                else:
                    result.spells[entry['name']] = uid
            if category in {'monsters', 'raids', 'followers', 'bosses'}:
                m = entry.get('skills', [])
                for t in m:
                    _, id = parse_codex_id(t['href'])
                    result.skills[id].append([category, entry['id']])

    return result


def convert(entries: Entries, scanned: ScanResult, item_types: dict):
    entries_meta = defaultdict(dict)
    for crawler in crawlers:
        category = crawler.CodexSpider.name
        base = entries[base_lang][category]
        entries_meta[category] = {}
        for bid, entry in base.items():
            entries_meta[category][bid] = defaultdict(dict)
            meta = entries_meta[category][bid]
            for key in entry.keys():
                tmp = entry[key]

                if key in href_keys:
                    m = entry.get(key, [])
                    drop_list = []
                    for drop in m:
                        href = drop.get('href')
                        if href:
                            d_category, d_id = parse_codex_id(href)
                            drop_list.append([d_category, d_id])
                    tmp = drop_list

                if key != 'name' and key in not_trans_keys:
                    tmp = None

                if key in translate_keys:
                    m = entry.get(key)
                    if m:
                        tmp = convert_key(m)

                if key == 'ability' and category in {'items'}:
                    m = entry.get(key)
                    if m:
                        tmp = ['spells', scanned.offhand_skills.get(m['name'])]

                if key == 'abilities' and category in {'raids', 'bosses', 'monsters', 'classes'}:
                    m = entry.get(key)
                    if m:
                        tmp = [scanned.check_conflict_ability(convert_key(ab['name']), ab) for ab in m]

                if key == 'name' and category in {'spells'}:
                    m = entry['name'].endswith(' (Off-hand)')
                    if m:
                        name = entry['name'][:-11]
                        ents = scanned.offhand_items.get(name)
                        if ents:
                            meta['items'] = ents

                if key == 'stats' and category in {'items', 'followers'}:
                    m = entry.get(key, [])
                    stats_struct = {}
                    for k, v in m:
                        stat_key = convert_key(k)
                        if stat_key == 'element':
                            stats_struct[stat_key] = convert_key(v)
                        else:
                            stats_struct[stat_key] = v
                    tmp = stats_struct

                if key in status_keys and category in {'items', 'spells'}:
                    m = entry.get(key, [])
                    status_list = []
                    for status in m:
                        status_name = convert_key(status['name'])
                        status_name = scanned.check_conflict_key(
                            status_name, status['icon'])
                        status_struct = {
                            'name': status_name,
                        }
                        if 'chance' in status:
                            status_struct['chance'] = status['chance']
                        status_list.append(status_struct)
                    tmp = status_list

                if key == 'summons' and category in {'spells'}:
                    m = entry.get(key, [])
                    summons_list = []
                    for summon in m:
                        summon_name = convert_key(summon['name'])
                        summon_name = scanned.check_conflict_key(
                            summon_name, summon['icon'])
                        summons_list.append({
                            'name': summon_name,
                            'chance': summon['chance']
                        })
                    tmp = summons_list

                if key in {'tags', 'event'} and category in {'bosses', 'monsters', 'raids', 'followers', 'items', 'spells'}:
                    m = entry.get(key, [])
                    tmp = [convert_key(tag) for tag in m]

                if key in {'bestial_bond'} and category in {'followers'}:
                    m = entry.get(key, [])
                    bonds_struct = {}
                    for index, bb in enumerate(m, 1):
                        bb_list = []
                        for b in bb['values']:
                            b_tmp = None
                            if b['type'] == 'bond':
                                b_key = convert_key(b['name'])
                                if b_key in scanned.translations[base_lang]['status']:
                                    b_tmp = ['buff', b_key, b['value']]
                                else:
                                    b_tmp = [b['type'], b_key, b['value']]
                            elif b['type'] == 'ability':
                                spell_id = scanned.get_spells_id(b['name'])
                                if spell_id:
                                    b_tmp = [b['type'], spell_id]
                            elif b['type'] == 'bonus':
                                if 'value' in b:
                                    b_tmp = [b['type'], convert_key(
                                        b['name']), b['value']]
                                else:
                                    b_tmp = [b['type'], convert_key(b['name'])]
                            if b_tmp is None:
                                b_tmp = [b['type'], b['name'], b['value']]
                            bb_list.append(b_tmp)
                        bonds_struct[index] = bb_list
                    tmp = bonds_struct

                if tmp is not None:
                    meta[key] = tmp

    for lang in langs:
        scanned.translations[lang]['item_type'] = {
            item_type['type']: item_type['name'] for item_type in item_types[lang]
        }
        if lang == base_lang:
            for item_type in item_types[lang]:
                for id in item_type['items']:
                    entries_meta['items'][id]['item_type'] = item_type['type']

            for id, ents in scanned.skills.items():
                entries_meta['spells'][id]['users'] = ents

            for id, ents in scanned.materials.items():
                entries_meta['items'][id]['source'] = ents

    return entries_meta


def save_translations(entries: Entries, scanned: ScanResult, output: Path):
    for lang in langs:
        output_path = output.joinpath(f'codex.{lang}.json')
        with open(output_path, 'w') as f:
            base = defaultdict(dict)
            for category, ents in entries[lang].items():
                for id, entry in ents.items():
                    entry_struct = {}
                    for key in not_trans_keys:
                        value = entry.get(key)
                        if value:
                            entry_struct[key] = value
                    base[category][id] = entry_struct
            json.dump({
                'base': base,
                'meta': {**scanned.translations[lang], **TRANSLATION[lang]},
                'abilities': scanned.abilities[lang],
                'miss': scanned.miss[lang],
            }, f, ensure_ascii=False)
            print('output:', output_path)


def run(data_dir: Path, output: str = None, generate: bool = False, target: str = None, **kwargs):
    output_dir = Path(output) if output else None

    if not generate:
        crawl_codex(target=target, data_dir=data_dir)

    if output:
        entries = load(data_dir.joinpath('entries'))
        item_types = load_item_type(data_dir.joinpath('item_types'))
        scanned = scan(entries)
        converted = convert(entries, scanned, item_types)
        save_translations(entries, scanned, output_dir)
        output_path = output_dir.joinpath('codex.json')
        with open(output_path, 'w') as f:
            json.dump({
                'meta': converted,
                'extra': {
                    'icons': scanned.icons
                },
            }, f)
        print('output:', output_path)
