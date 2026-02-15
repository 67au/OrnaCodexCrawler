from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
import json
from pathlib import Path
import shutil
from scrapy.settings import Settings

from ornacodex.utils import get_hash
from ornacodex.utils.converter import Converter, UniqueKeyGenerator
from ornacodex.utils.exctractor import Exctractor
from ornacodex.utils.path_config import TmpPathConfig
from ..spiders import bosses, classes, followers, items, monsters, raids, spells

import glom


crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]


def load_item_types(itemtypes_dir: Path, languages: list[str]):
    itemtypes = {}
    for language in languages:
        with open(itemtypes_dir.joinpath(f'{language}.json')) as f:
            itemtypes[language] = json.load(f)
    return itemtypes


def load_entries(entries_dir: Path, languages: list[str]):
    entries = defaultdict(dict)
    for (language, crawler) in product(languages, crawlers):
        category: str = crawler.Spider.name
        with open(entries_dir.joinpath(language, f'{category}.json')) as f:
            for entry in sorted(json.load(f), key=lambda e: e['id']):
                key = f"{category}/{entry['id']}"
                entries[language][key] = entry
    return entries


icon_key_generator = UniqueKeyGenerator()
abilities_key_generator = UniqueKeyGenerator()


def get_default_translation():
    return {
        'msg': defaultdict(dict),
        'entries': dict(),
        'abilities': dict()
    }


def get_value_type(value: str):
    value_type = {}
    if value.startswith('+'):
        value_type['type'] = 'SIGNED'
    if value.endswith('%'):
        value_type['unit'] = 'PERCENT'
    if value.endswith(('turn', 'turns')):
        value_type['unit'] = 'TURN'
    if value.endswith('mana'):
        value_type['unit'] = 'MANA'
    if value.endswith('/m'):
        value_type['unit'] = 'PER_M'
    return value_type


def isSpellKey(key) -> bool:
    return key.startswith('_') and key.endswith(('spell', 'skill'))


def scan(settings: Settings, input_dir: Path):
    base_language = settings.get('BASE_LANGUAGE')
    languages = settings.get('SUPPORTED_LANGUAGES')

    # icons
    icons = dict()

    def set_icon(key, new_icon):
        icon = icons.get(key)
        if icon:
            return
        icons[key] = new_icon

    # attached spells
    attached_spells = dict()

    def set_attached_spells(key, name):
        spell = attached_spells.get(key)
        if spell:
            return
        attached_spells[key] = name

    # value type
    value_types = dict()

    def set_value_types(key, new_value: dict):
        old_value = value_types.get(key)
        if old_value and old_value.get('type'):
            return
        if any(new_value):
            value_types[key] = new_value

    entries = load_entries(input_dir.entries, languages)

    # base entries
    base_entries = entries[base_language]
    tmp_entries = {key: {} for key in base_entries.keys()}

    def set_ent(path: str, value):
        _ = glom.assign(tmp_entries, path, value)

    # translations
    translations = {lang: get_default_translation() for lang in languages}
    for lang in languages:
        for entry_key, entry in entries[lang].items():
            translations[lang]['entries'][entry_key] = {'name': entry['name']}
            description = entry.get('description')
            if description:
                translations[lang]['entries'][entry_key]['description'] = description

    def set_msg(language: str, msg_path: str,  value):
        msg = translations[language]['msg']
        is_empty = glom.glom(msg, glom.Coalesce(
            msg_path, default=None)) is None
        if is_empty:
            if value:
                glom.assign(msg, msg_path, value)

    def set_msg_by_path(msg_path: str, value_path: str):
        for language in languages:
            used_entries = entries[language]
            value = glom.glom(used_entries, glom.Coalesce(
                value_path, default=None))
            set_msg(language, msg_path, value)

    # abilities_stats
    ability_stats = dict()

    def set_ability_stat(ability_key: str, stat: list[str, str], value_path: str):
        stats = ability_stats[ability_key]
        key, value = stat
        if key in {'bestial_bond_level', 'mana_rush'}:
            base_value = Converter.convert_key(value)
            set_value_types('abilities.'+key, {'type': 'TEXT'})
            stats[key] = base_value
            for language in languages:
                val = glom.glom(entries[language], value_path)
                set_msg(language, 'stats_text.'+base_value, val)
            return

        # normal type
        value_type = get_value_type(value)
        set_value_types('abilities.'+key, value_type)
        if any(value_type) or value[-1].isdigit():
            stats[key] = Exctractor.extract_number(value)
            return

        # elif gives/causes = 'Rot (1%), Blight (2%)'
        if key in {'gives', 'causes'}:
            base_buffs = [[Converter.convert_key(n), c]for n, c in (
                Exctractor.extract_chance(v.strip()) for v in value.split(','))]
            stats[key] = [{'name': buf[0], 'chance': int(buf[1].strip('%') if buf[1] else None)}
                          for buf in base_buffs]
            for language in languages:
                buffs = [Exctractor.extract_chance(v.strip()) for v in glom.glom(
                    entries[language], value_path).split(',')]
                for i, base_buf in enumerate(base_buffs):
                    base_name = base_buf[0]
                    set_msg(language, 'status.'+base_name, buffs[i][0])
            return

        # else what?
        print('missed abilities stats type:', key, value)

    # abilities

    def set_abilities(entry_key, path):
        ###
        base_abilities = []
        for index, base in enumerate(glom.glom(base_entries, glom.Coalesce(
                f'{entry_key}.{path}', default=[]))):
            icon = base.get('icon')
            unique_key = icon_key_generator.generate_unique_key(
                (base.get('name'), icon))
            unique_key = abilities_key_generator.generate_unique_key(
                (unique_key, base.get('description', ''))
            )
            set_icon(unique_key, icon)
            base_abilities.append(unique_key)
            # stats
            stats = base.get('stats')
            if stats and ability_stats.get(unique_key) is None:
                ability_stats[unique_key] = {}
                stats_path = f'{entry_key}.{path}.{index}.stats'
                base_stats = glom.glom(
                    base_entries, glom.Coalesce(stats_path, default=[]))
                for i, stat in enumerate(base_stats):
                    stat_key = Converter.convert_key(stat[0])
                    stat_key_path = f'{stats_path}.{i}.0'
                    stat_value_path = f'{stats_path}.{i}.1'

                    # patch for bestial_bond_level
                    if stat_key == 'bestial_bond' and stat[1][-1].isdigit():
                        stat_key = 'bestial_bond_level'

                    set_msg_by_path('stats.'+stat_key,
                                    stat_key_path)
                    if len(stat) == 1:
                        set_value_types('abilities.' +
                                        stat_key, {'type': 'FLAG'})
                        ability_stats[unique_key][stat_key] = True
                    else:
                        set_ability_stat(unique_key, [
                            stat_key, stat[1]], stat_value_path)
            ###
        set_ent(f'{entry_key}.abilities', base_abilities)
        ###
        for language in languages:
            translation = translations[language]['abilities']
            for index, value in enumerate(glom.glom(entries[language], glom.Coalesce(f'{entry_key}.{path}', default=[]))):
                is_empty = glom.glom(translation, glom.Coalesce(
                    base_abilities[index], default=None)) is None
                if is_empty:
                    value_filtered = {k: v for k, v in value.items() if k in {
                        'name', 'description'}}
                    glom.assign(
                        translation, base_abilities[index], value_filtered)
        ###

    # bestial bond
    def set_bestial_bond(entry_key, path):
        ###
        base_bbs = []
        for base_bond in glom.glom(base_entries, glom.Coalesce(
                f'{entry_key}.{path}', default=[])):
            tmp = []
            for bb in Exctractor.extract_bond(base_bond['stats']):
                bb_key = Converter.convert_key(bb['name'])

                bb_dict = {**bb, 'name': bb_key}
                if bb['type'] == 'ABILITY':
                    set_attached_spells(bb_key, bb['name'])
                if bb['type'] == 'BONUS':
                    if bb.get('value') is None:
                        bb_dict['value'] = 1
                        set_value_types('bonds.'+bb_key, {'type': 'FLAG'})
                    else:
                        value_type = get_value_type(bb['value'])
                        set_value_types('bonds.'+bb_key, value_type)
                        bb_dict['value'] = Exctractor.extract_number(
                            bb['value'])
                if bb['type'] == 'BOND':
                    pass
                tmp.append(bb_dict)
            base_bbs.append(tmp)
        set_ent(f'{entry_key}.bestial_bond', base_bbs)
        ###
        for language in languages:
            for index, bond in enumerate(glom.glom(entries[language], glom.Coalesce(
                    f'{entry_key}.{path}', default=[]))):
                for i, bb in enumerate(Exctractor.extract_bond(bond['stats'])):
                    base_bb = base_bbs[index][i]
                    if bb['type'] == 'ABILITY':
                        continue
                    if bb['type'] == 'BONUS':
                        # 'BONUS' merge to stats
                        set_msg(
                            language, f'stats.{base_bb["name"]}', bb["name"])
                    if bb['type'] == 'BOND':
                        # 'BOND' merge to status
                        set_msg(
                            language, f'status.{base_bb["name"]}', bb["name"])
        ###

    def set_stat(entry_key: str, stat: list[str, str], value_path: str):
        key, value = stat
        value, conditions = Exctractor.extract_conditions(value)
        if conditions:
            is_empty = glom.glom(tmp_entries, glom.Coalesce(
                f'{entry_key}.stats_conditions', default=None)) is None
            if is_empty:
                glom.assign(tmp_entries, f'{entry_key}.stats_conditions', {})
            base_conds = [Converter.convert_key(cond) for cond in conditions]
            for language in languages:
                _, conds = Exctractor.extract_conditions(
                    glom.glom(entries[language], value_path))
                for index, cond in enumerate(conds):
                    set_msg(language, 'stats_conditions.' +
                            base_conds[index], cond)
            set_ent(f'{entry_key}.stats_conditions.{key}', base_conds)

        if key in {'stat_bonus', 'bestial_bond_level'}:
            value_type = {'type': 'TEXT'}
            set_value_types('stats.'+key, value_type)
            base_value = Converter.convert_key(value)
            set_ent(f'{entry_key}.stats.{key}', base_value)
            for language in languages:
                value, _ = Exctractor.extract_conditions(
                    glom.glom(entries[language], value_path))
                set_msg(language, 'stats_text.' + base_value, value)
            return

        value_type = get_value_type(value)
        set_value_types('stats.'+key, value_type)
        if any(value_type) or value[-1].isdigit():
            set_ent(f'{entry_key}.stats.{key}',
                    Exctractor.extract_number(value))
            return

        # spells key
        if isSpellKey(key):
            base_value = Converter.convert_key(value)
            set_attached_spells(base_value, value)
            spells = glom.glom(tmp_entries, glom.Coalesce(
                f'{entry_key}.stats.{key}', default=[]))
            spells.append({'name': base_value})
            set_ent(f'{entry_key}.stats.{key}', spells)
            set_value_types('stats.'+key, {'type': 'TEXT'})
            for language in languages:
                value, _ = Exctractor.extract_conditions(
                    glom.glom(entries[language], value_path))
                set_msg(language, 'stats_text.' + base_value, value)
            return

        # else text
        base_value = Converter.convert_key(value)
        set_ent(f'{entry_key}.stats.{key}', base_value)
        set_value_types('stats.'+key, {'type': 'TEXT'})
        for language in languages:
            value, _ = Exctractor.extract_conditions(
                glom.glom(entries[language], value_path))
            set_msg(language, 'stats_text.' + base_value, value)

    # scan started
    for entry_key, entry in base_entries.items():

        # category = str
        category: str = entry_key.split('/')[0]
        category_key = entry_key+'.category'
        set_ent(category_key, category)
        set_msg_by_path('category.' + category, category_key)

        # id
        id = entry.get('id')
        if id:
            set_ent(entry_key + '.id', id)

        # icon
        icon = entry.get('icon')
        if icon:
            set_ent(entry_key+'.icon', icon)

        # tier (for spells)
        tier = entry.get('tier')
        if tier:
            set_ent(entry_key + '.tier', int(tier))

        # spell_type
        spell_type = entry.get('spell_type')
        if spell_type:
            base_value = Converter.convert_key(spell_type)
            set_ent(entry_key + '.spell_type', base_value)
            set_msg_by_path('spell_type.'+base_value,
                            entry_key + '.spell_type')

        # offhand_ability
        offhand_ability = entry.get('ability')
        if offhand_ability:
            set_ent(entry_key + '.offhand_ability', offhand_ability)

        # exotic = 1 | 0
        exotic = entry.get('exotic')
        if exotic:
            exotic_key = entry_key+'.exotic'
            set_ent(exotic_key, 1)
            set_msg_by_path('meta.exotic', exotic_key)
        else:
            exotic_key = entry_key+'.exotic'
            if category == 'items':
                set_ent(exotic_key, 0)

        # aura
        aura = entry.get('aura')
        if aura:
            aura_key = entry_key + '.aura'
            set_ent(aura_key, aura)

        # stats
        stats = entry.get('stats')
        if stats:
            entry_stats_key = entry_key + '.stats'
            if any(list(filter(lambda s: s[0] not in {'Targets'}, stats))):
                set_ent(entry_stats_key, {})
            for index, stat in enumerate(stats):
                stat_key = Converter.convert_key(stat[0])
                entry_stat_key_path = f'{entry_stats_key}.{index}.0'
                entry_stat_value_path = f'{entry_stats_key}.{index}.1'
                # targets, move to meta
                if stat_key == 'targets':
                    targets = Converter.convert_key(stat[1])
                    set_msg_by_path('meta.targets', entry_stat_key_path)
                    set_msg_by_path('targets.'+targets, entry_stat_value_path)
                    set_ent(entry_key+'.targets', targets)
                # elements
                elif stat_key == 'element':
                    elements = [Converter.convert_key(
                        elem) for elem in stat[1]]
                    for i, elem in enumerate(elements):
                        set_msg_by_path('stats_text.' + elem,
                                        f'{entry_stat_value_path}.{i}')
                    set_value_types('stats.' + stat_key, {'type': 'TEXT'})
                    set_ent(f'{entry_stats_key}.element', elements)
                elif stat_key == 'power':
                    set_msg_by_path('stats.' + stat_key, entry_stat_key_path)
                    set_value_types('stats.' + stat_key, {'type': 'TEXT'})
                    set_ent(f'{entry_stats_key}.power', stat[1])
                else:

                    # patch for bestial_bond_level
                    if stat_key == 'bestial_bond' and stat[1][-1].isdigit():
                        stat_key = 'bestial_bond_level'

                    # set stats key
                    set_msg_by_path('stats.' + stat_key, entry_stat_key_path)

                    # stat_value = Converter.convert_key(stat[1])
                    if len(stat) == 1:
                        set_value_types('stats.' + stat_key, {'type': 'FLAG'})
                        set_ent(f'{entry_stats_key}.{stat_key}', True)
                    else:
                        set_stat(entry_key, [
                                 stat_key, stat[1]], entry_stat_value_path)

        # drops = list[tuple[str, list[Any]]]
        drops = entry.get('drops')
        if drops:
            for index, drop in enumerate(drops):
                key = Converter.convert_key(drop[0])
                set_msg_by_path('meta.'+key, f'{entry_key}.drops.{index}.0')
                drop_value_path = f'drops.{index}.1'
                if key == 'abilities':
                    set_abilities(entry_key, drop_value_path)
                elif key == 'bestial_bond':
                    set_bestial_bond(entry_key, drop_value_path)
                else:
                    drops_list = []
                    for i, d in enumerate(drop[1]):
                        href: str = d.get('href')
                        # deal href
                        if href:
                            drops_list.append(
                                '/'.join(Exctractor.extract_codex_id(href)))
                            continue

                        icon = d.get('icon')
                        chance = d.get('chance')
                        if icon:
                            unique_key = icon_key_generator.generate_unique_key(
                                (d.get('name'), icon))
                            set_icon(unique_key, icon)
                            tmp = {'name': unique_key}
                            if chance:
                                tmp['chance'] = int(chance.strip('%'))
                            # status
                            set_msg_by_path('status.'+unique_key,
                                            f'{entry_key}.drops.{index}.1.{i}.name')
                            drops_list.append(tmp)
                            continue

                    # collect drops
                    if any(drops_list):
                        set_ent(f'{entry_key}.{key}', drops_list)

        # check spell level
        drops = entry.get('drops')
        if drops and category == 'classes':
            for index, drop in enumerate(drops):
                key = Converter.convert_key(drop[0])
                if key == 'skills':
                    skills_level = {Exctractor.extract_codex_key(
                        d['href']): Exctractor.extract_spell_level(d['name']) for d in drop[1]}
                    set_ent(entry_key + '.skills_level', skills_level)

        # follower = ['Follower', {'name', 'icon'}]
        follower = entry.get('follower')
        if follower:
            follower_key = entry_key + '.follower'
            set_msg_by_path('meta.follower', f'{follower_key}.0')
            unique_key = icon_key_generator.generate_unique_key(
                tuple(follower[1].values())
            )
            set_ent(follower_key, unique_key)
            set_icon(unique_key, follower[1]['icon'])
            set_msg_by_path(f'follower.'+unique_key, f'{follower_key}.1.name')

        # tags = list[str]
        tags = entry.get('tags')
        if tags:
            tags_list = [Converter.convert_key(tag) for tag in tags]
            tags_key = entry_key + '.tags'
            set_ent(tags_key, tags_list)
            for index, tag in enumerate(tags_list):
                set_msg_by_path('tags.' + tag, f'{tags_key}.{index}')

        # meta = list[tuple[str, str]]
        metas: list[tuple[str, str]] | None = entry.get('meta')
        if metas:
            for index, meta in enumerate(metas):
                key = Converter.convert_key(meta[0])
                value_key = entry_key + '.' + key
                set_msg_by_path('meta.'+key, f'{entry_key}.meta.{index}.0')
                if key == 'tier':
                    set_ent(value_key, int(meta[1].strip('★')))
                elif key == 'hp':
                    set_ent(value_key, int(meta[1].replace(',', '')))
                else:
                    value = Converter.convert_key(meta[1])
                    set_ent(value_key, value)
                    set_msg_by_path(f'{key}.{value}',
                                    f'{entry_key}.meta.{index}.1')

    # events
    unordered_events = {
        lang: {} for lang in languages
    }

    def set_conflict_events(event, index_key):
        for language in languages:
            used_entries = entries[language]
            value = glom.glom(used_entries, glom.Coalesce(
                index_key, default=None))
            if unordered_events[language].get(event, None) is None:
                unordered_events[language][event] = value

    for entry_key, entry in base_entries.items():
        events = entry.get('events')
        if events:
            events_list = [Converter.convert_key(event) for event in events]
            value_key = entry_key+'.events'
            set_ent(value_key, events_list)
            if len(events_list) == 1:
                set_msg_by_path('events.'+events_list[0], value_key + '.0')
            else:
                for index, event in enumerate(events_list):
                    set_conflict_events(event, f'{value_key}.{index}')
    # mitigate bug of unordered events
    for language, translation in translations.items():
        translation['msg']['events'].update(unordered_events[language])

    item_types = load_item_types(input_dir.itemtypes, languages)

    return {
        'icons': icons,
        'entries': tmp_entries,
        'translations': translations,
        'attached_spells': attached_spells,
        'value_types': value_types,
        'ability_stats': ability_stats,
        'item_types': item_types,
    }


def analyze(scanned: dict, settings: Settings):
    base_language = settings.get('BASE_LANGUAGE')
    languages = settings.get('SUPPORTED_LANGUAGES')

    entries = scanned['entries']
    translations = scanned['translations']
    attached_spells = scanned['attached_spells']
    value_types = scanned['value_types']
    item_types = scanned['item_types']

    # set item_types
    for its in item_types[base_language]:
        for id in its['items']:
            entries['items/' + id]['item_type'] = its['type']

    # set two_handed
    for entry_key, entry in entries.items():
        is_weapon = entry.get('item_type') == 'weapon'
        if is_weapon:
            is_two_handed = entry.get('stats', {}).get('two_handed') == 1
            entries[entry_key]['two_handed'] = 1 if is_two_handed else 0

    # offhand_skills = { name: entry_key }
    skills_filp = {entry['name']: entry_key for entry_key,
                   entry in translations[base_language]['entries'].items()}

    for entry_key, entry in entries.items():
        offhand_ability = entry.get('offhand_ability')
        if offhand_ability:
            name = offhand_ability[0] + ' (Off-hand)'
            spell_key = skills_filp.get(name)
            spell_entry = entries[spell_key]
            # add off_hands items to spells
            if 'off_hands' not in spell_entry:
                spell_entry['off_hands'] = []
            spell_entry['off_hands'].append(entry_key)
            # replace offhand_ability
            entry['offhand_ability'] = spell_key

    # attached_spells
    attached_ability = {}
    for id, name in attached_spells.items():
        spell_key = skills_filp.get(name)
        attached_ability[id] = spell_key or name

    # used_by, spells used by enemies
    for entry_key, entry in entries.items():
        skills = entry.get('skills')
        if entry['category'] != 'classes' and skills:
            for key in skills:
                spell_entry = entries[key]
                if 'used_by' not in spell_entry:
                    spell_entry['used_by'] = []
                spell_entry['used_by'].append(entry_key)

    # materials
    for entry_key, entry in entries.items():
        upgrade_materials = entry.get('upgrade_materials')
        if upgrade_materials:
            for key in upgrade_materials:
                material_entry = entries[key]
                if 'dismantled_by' not in material_entry:
                    material_entry['dismantled_by'] = []
                material_entry['dismantled_by'].append(entry_key)

    # patch value types
    for key in ['follower_stats', 'summon_stats']:
        val = value_types.get('stats.' + key)
        value_types['_' + key] = val

    # patch translation
    for language in languages:
        msg = translations[language]['msg']
        for it in item_types[language]:
            type, name = it['type'], it['name']
            msg['item_type'][type] = name

        for key in ['follower_stats', 'summon_stats']:
            val = msg['stats'][key]
            msg['stats']['_' + key] = '+' + val

    # get options
    options_dict_set = defaultdict(set)
    options_key_set = {'category', 'tier', 'events', 'exotic',  'item_type',
                       'rarity',  'family', 'place', 'type', 'useable_by', 'two_handed',
                       'causes',  'gives', 'cures', 'immunities', 'summons',  # status
                       'abilities',  # abilities
                       'spell_type', 'targets', 'tags', }
    for entry in entries.values():
        for key in entry.keys():
            value = entry.get(key)

            if key in options_key_set:
                if isinstance(value, list):
                    for v in value:
                        options_dict_set[key].add(
                            v['name'] if isinstance(v, dict) else v
                        )
                else:
                    options_dict_set[key].add(value)

            if key == 'stats':
                stats = value
                for k in stats.keys():
                    if isSpellKey(k) or k == 'element':
                        for v in stats.get(k, []):
                            options_dict_set['stats.' + k].add(
                                v['name'] if isinstance(v, dict) else v
                            )

    options = {k: sorted(v) for k, v in options_dict_set.items()}
    ###

    # get sorts
    sorts_dict_set = {
        'items': set(),
        'followers': set(),
        'spells': set(),
        'raids': {'hp'},
    }
    skip_sorts_set = {'power', 'element'}
    for entry in entries.values():
        category = entry['category']
        stats = entry.get('stats')
        if category in sorts_dict_set and stats:
            for key in stats.keys():
                if key in skip_sorts_set or isSpellKey(key):
                    continue
                sorts_dict_set[category].add('stats.' + key)
    sorts = {k: sorted(v) for k, v in sorts_dict_set.items()}
    ###

    # trans translations
    locales = {language: {
        'msg': translations[language]['msg'],
        'entries': [],
        'abilities': [],
    } for language in languages}

    for language, t in translations.items():
        for entry_key, e in t['entries'].items():
            entry = entries[entry_key]
            ent = {
                **e,
                'language': language,
                'category': entry['category'],
                'id': entry['id'],

            }
            locales[language]['entries'].append(ent)
        for key, e in t['abilities'].items():
            ability = {
                **e,
                'language': language,
                'id': key,

            }
            locales[language]['abilities'].append(ability)

    return (
        {
            'entries': list(entries.values()),
            'meta': {
                'value_types': value_types,
                'icons': scanned['icons'],
                'ability_stats': scanned['ability_stats'],
                'attached_ability': attached_ability,
                'options': options,
                'sorts': sorts,
            }
        },
        locales
    )


def main(settings: Settings, input: Path = None, output: Path = None):
    input_dir = TmpPathConfig(input or 'tmp')
    output_dir = Path(output or 'output')

    print('scanning entries...')
    scanned = scan(settings, input_dir)

    print('analyzing entries...')
    analyzed = analyze(scanned, settings)
    codex, locales = analyzed

    if (output_dir.exists() and output_dir.is_dir()):
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.joinpath('locales').mkdir()

    files = {
        'codex': '',
        'locales': {},
    }

    # save codex
    file_content = json.dumps(codex, ensure_ascii=False)
    file_hash = get_hash(file_content)
    file_name = f'codex.{file_hash}.json'
    with open(output_dir.joinpath(file_name), 'w') as f:
        f.write(file_content)
    files['codex'] = file_name
    print('save file:', file_name)

    # save locales
    for languange, locale in locales.items():
        file_content = json.dumps(locale, ensure_ascii=False)
        file_hash = get_hash(file_content)
        file_name = f'{languange}.{file_hash}.json'
        with open(output_dir.joinpath('locales', file_name), 'w') as f:
            f.write(file_content)
        files['locales'][languange] = file_name
        print('save file:', file_name)

    manifest = {
        'version': settings.get('VERSION'),
        'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'files': files
    }

    with open(output_dir.joinpath('manifest.json'), 'w') as f:
        json.dump(manifest, f, ensure_ascii=False)
    print('save file:', 'manifest.json')

    ###
    print('=== Manifest ===')
    print(json.dumps(manifest, ensure_ascii=False, indent=4))


def run(settings: Settings, **kwargs):
    main(settings=settings, **kwargs)
