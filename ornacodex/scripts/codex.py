from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
from scrapy.settings import Settings
from scrapy.utils.project import get_project_settings

from ornacodex.utils.converter import Converter, UniqueKeyGenerator
from ornacodex.utils.exctractor import Exctractor

from ..utils.path_config import TmpPathConfig

from ..spiders import bosses, classes, followers, items, monsters, raids, spells


crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

settings = get_project_settings()
base_language = settings.get('BASE_LANGUAGE')
languages = settings.get('SUPPORTED_LANGUAGES', [])


def load(entries_dir: Path):
    entries = {language: {} for language in languages}
    for (language, crawler) in product(languages, crawlers):
        name = crawler.Spider.name
        with open(entries_dir.joinpath(language, f'{name}.json')) as f:
            entries[language][name] = {i['id']: i for i in sorted(json.load(f), key=lambda k: k['id'])}
    return entries


def load_itemtypes(itemtypes_dir: Path):
    itemtypes = {}
    for language in languages:
        with open(itemtypes_dir.joinpath(f'{language}.json')) as f:
            itemtypes[language] = json.load(f)
    return itemtypes


def scan(entries, itemtypes):

    translations = {language: defaultdict(dict) for language in languages}
    cm = {}
    ct = {language: defaultdict(dict) for language in languages}
    icons = {}

    events_conflict = {language: {} for language in languages}

    icon_key_generator = UniqueKeyGenerator()
    abilities_key_generator = UniqueKeyGenerator()

    for (language, crawler) in product(languages, crawlers):
        category = crawler.Spider.name
        used = entries[language][category]
        base = entries[base_language][category]
        cm_tmp = defaultdict(dict)
        for id, entry in used.items():

            cm_tmp[id]['category'] = category
            translations[language]['category'][category] = entry['category']

            exotic = entry.get('exotic')
            if exotic:
                translations[language]['exotic'] = exotic
                cm_tmp[id]['exotic'] = True

            events = entry.get('events')
            if events:
                cm_tmp[id]['events'] = []
                for i, event in enumerate(events):
                    key = Converter.convert_key(base[id]['events'][i])
                    cm_tmp[id]['events'].append(key)
                    if events_conflict[language].get(key, False):
                        continue
                    else:
                        if len(events) == 1:
                            events_conflict[language][key] = True
                    translations[language]['events'][key] = event

            tags = entry.get('tags')
            if tags:
                cm_tmp[id]['tags'] = []
                for i, tag in enumerate(tags):
                    key = Converter.convert_key(base[id]['tags'][i])
                    cm_tmp[id]['tags'].append(key)
                    translations[language]['tags'][key] = tag

            meta = entry.get('meta')
            if meta:
                for i, m in enumerate(meta):
                    key = Converter.convert_key(base[id]['meta'][i][0])
                    translations[language]['meta'][key] = m[0]
                    if key == 'tier':
                        cm_tmp[id][key] = int(m[1].strip('★'))
                    elif key == 'hp':
                        cm_tmp[id][key] = m[1]
                    else:
                        value = Converter.convert_key(
                            base[id]['meta'][i][1])
                        cm_tmp[id][key] = value
                        translations[language][key][value] = m[1]

            stats = entry.get('stats')
            if stats:
                cm_tmp[id]['stats'] = {}
                for i, m in enumerate(stats):
                    key = Converter.convert_key(base[id]['stats'][i][0])
                    # move from `stats` to `meta`
                    if key == 'targets':
                        value = Converter.convert_key(
                            base[id]['stats'][i][1])
                        translations[language]['meta'][key] = m[0]
                        translations[language][key][value] = m[1]
                        cm_tmp[id][key] = value
                    ###
                    elif key == 'element':
                        cm_tmp[id]['stats'][key] = []
                        for ii, e in enumerate(m[1]):
                            value = Converter.convert_key(
                                key=base[id]['stats'][i][1][ii])
                            translations[language][key][value] = e
                            cm_tmp[id]['stats'][key].append(value)
                    elif key == 'costs':
                        translations[language]['stats'][key] = m[0]
                        cm_tmp[id]['stats'][key] = base[id]['stats'][i][1].split()[
                            0]
                    else:
                        translations[language]['stats'][key] = m[0]
                        if len(m) > 1:
                            cm_tmp[id]['stats'][key] = base[id]['stats'][i][1]
                        else:
                            cm_tmp[id]['stats'][key] = True

            drops = entry.get('drops')
            if drops:
                for i, m in enumerate(drops):
                    key = Converter.convert_key(base[id]['drops'][i][0])
                    translations[language]['meta'][key] = m[0]
                    d_list = []
                    for ii, d in enumerate(m[1]):
                        href = d.get('href')
                        icon = d.get('icon')
                        if href:
                            d_list.append(Exctractor.extract_codex_id(href))
                        elif icon:
                            icon_key = Converter.convert_key(
                                base[id]['drops'][i][1][ii]['name'])
                            unique_key = icon_key_generator.generate_unique_key(
                                (icon_key, icon))
                            description = d.get('description')
                            chance = d.get('chance')
                            icons[unique_key] = icon
                            tmp = {
                                'name': unique_key,
                            }
                            if description:
                                abilities_key = abilities_key_generator.generate_unique_key(
                                    (icon_key, hashlib.md5(base[id]['drops'][i][1][ii]['description'].encode()).digest()))
                                # abilities
                                translations[language]['abilities'][abilities_key] = d
                                tmp['name'] = abilities_key
                            else:
                                translations[language]['status'][unique_key] = d['name']
                            if chance:
                                tmp['chance'] = chance
                            d_list.append(tmp)
                        else:
                            if category == 'followers':
                                bb_base = Exctractor.extract_bond(
                                    base[id]['drops'][i][1][ii]['description'])
                                bb = Exctractor.extract_bond(d['description'])
                                tmp = []
                                for iii, bbb in enumerate(bb_base):
                                    if bbb['type'] == 'ABILITY':
                                        tmp.append(bbb)
                                        continue
                                    bb_key = Converter.convert_key(bbb['name'])
                                    tmp.append({**bbb, 'name': bb_key})
                                    translations[language]['bestial_bond'][bb_key] = bb[iii]['name']
                                d_list.append(tmp)
                            else:
                                # dummy
                                pass
                    if any(d_list):
                        cm_tmp[id][key] = d_list

            cm_tmp[id]['id'] = entry['id']

            tier = entry.get('tier')
            if tier:
                cm_tmp[id]['tier'] = int(tier)

            hp = entry.get('hp')
            if hp:
                cm_tmp[id]['hp'] = int(hp)

            spell_type = entry.get('spell_type')
            if spell_type:
                key = Converter.convert_key(base[id]['spell_type'])
                translations[language]['spell_type'][key] = spell_type
                cm_tmp[id]['spell_type'] = key

            ct[language][id]['name'] = entry['name']
            description = entry.get('description')
            if description:
                ct[language][id]['description'] = description

            ability = entry.get('ability')
            if ability:
                cm_tmp[id]['ability'] = base[id]['ability']

        cm[category] = cm_tmp

    for its in itemtypes[base_language]:
        for id in its['items']:
            cm['items'][id]['item_type'] = its['type']

    offhand_skills = {
        entries[base_language]['spells'][spell['id']]['name'][:-11]: spell['id'] for spell in cm['spells'].values() if 'off-hand_ability' in spell.get('tags', [])
    }

    for item_id, item in entries[base_language]['items'].items():
        ability = item.get('ability')
        if ability:
            spell_id = offhand_skills.get(ability[0])
            cm['items'][item_id]['ability'] = ['spells', spell_id]
            if 'off-hands' not in cm['spells'][spell_id]:
                cm['spells'][spell_id]['off-hands'] = []
            cm['spells'][spell_id]['off-hands'].append(['items', item_id])

    for category in ['followers', 'raids', 'bosses', 'monsters']:
        for id, entry in cm[category].items():
            skills = entry.get('skills')
            if skills:
                for _, spell_id in skills:
                    if 'used_by' not in cm['spells'][spell_id]:
                        cm['spells'][spell_id]['used_by'] = []
                    cm['spells'][spell_id]['used_by'].append([category, id])

    skills = {
        entries[base_language]['spells'][spell['id']]['name']: spell['id'] for spell in cm['spells'].values()
    }

    for id in cm['followers'].keys():
        bestial_bond = cm['followers'][id].get('bestial_bond', [])
        for i, b in enumerate(bestial_bond):
            for ii, bb in enumerate(b):
                if bb['type'] == 'ABILITY':
                    cm['followers'][id]['bestial_bond'][i][ii]['name'] = skills[bb['name']]

    materials = defaultdict(list)
    for item_id, item in cm['items'].items():
        for _, id in item.get('upgrade_materials', []):
            materials[id].append(['items', item['id']])
    for id in materials.keys():
        cm['items'][id]['source'] = materials[id]

    for language in languages:
        for its in itemtypes[language]:
            translations[language]['item_type'][its['type']] = its['name']
        translations[language]['main'] = ct[language]

    return (cm, icons, translations)


def generate_options(codex: dict):
    options = defaultdict(set)
    # single = ['category', 'tier', 'family', 'rarity', 'useable_by',
    #           'place', 'type', 'spell_type', 'item_type', 'targets']
    # manual = ['exotic', 'element']
    # multiple = ['immunities', 'causes', 'gives',
    #             'cures', 'tags', 'events', 'abilities']
    option_keys = [
        # single
        'category', 'tier', 'family', 'rarity', 'useable_by', 'place', 'type', 'spell_type', 'item_type', 'targets',
        # multiple
        'immunities', 'causes', 'gives', 'cures', 'tags', 'events', 'abilities'
    ]

    for crawler in crawlers:
        category = crawler.Spider.name
        for entry in codex[category].values():
            for key in option_keys:
                m = entry.get(key)
                if m:
                    if isinstance(m, list):
                        for mm in m:
                            options[key].add(
                                mm['name'] if isinstance(mm, dict) else mm)
                    else:
                        options[key].add(m)
            # element
            stats = entry.get('stats')
            if stats:
                for m in stats.get('element', []):
                    options['element'].add(m)
            # exotic
            options['exotic'] = set([True, False])

    return {k: sorted(v) for k, v in options.items()}

def save_codex(output_dir: Path, codex: dict):
    with open(output_dir.joinpath('codex.json'), 'w') as f:
        json.dump(codex, f, ensure_ascii=False)
    return 'codex.json'


def save_translations(output_dir: Path, translations: dict):
    i18n_dir = output_dir.joinpath('i18n')
    i18n_dir.mkdir(exist_ok=True)
    for language in languages:
        with open(i18n_dir.joinpath(f'{language}.json'), 'w') as f:
            json.dump(translations[language], f, ensure_ascii=False)

    return [f'i18n/{language}.json' for language in languages]

def run(settings: Settings):
    tmp_dir_config = TmpPathConfig(settings.get('TMP_DIR'))
    output_dir = Path(settings.get('OUTPUT_DIR'))
    output_dir.mkdir(exist_ok=True)

    itemtypes = load_itemtypes(tmp_dir_config.itemtypes)
    entries = load(tmp_dir_config.entries)
    codex, icons, translations = scan(entries, itemtypes)
    options = generate_options(codex)

    codex_files = save_codex(
        output_dir,
        {
            'main': codex,
            'icons': icons,
            'options': options
        })
    translations_files = save_translations(output_dir, translations)

    index = {
        'version': settings.get('VERSION'),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'languages': languages,
        'data_files': {
            'codex': codex_files,
            'i18n': translations_files
        }
    }
    with open(output_dir.joinpath('index.json'), 'w') as f:
        json.dump(index, f)

    print(f'=== Output: {str(output_dir)} ===')
    print(json.dumps(index, indent=4, ensure_ascii=False))