import ast
import re

from scrapy.selector.unified import SelectorList

from .url_utils import UrlParser

split_pattern = re.compile(r':|：')
chance_pattern = re.compile(r'(?P<NAME>.+) \((?P<VALUE>\d+(\.\d+)?\%)\)$')
ability_pattern = re.compile(r'^\+(?P<NAME>.+)\: (?P<VALUE>.+)$')
bonus_pattern = re.compile(r'^(?!\+)(?P<NAME>.+)\: (?P<VALUE>.+)$')
condition_pattern = re.compile(r'(?P<VALUE>.+) \((?P<CONDITIONS>.+)\)')
number_pattern = re.compile(r'^(\+)?(?P<NUMBER>\-?\d+(\.\d+)*).*')
spell_level_pattern = re.compile(r'.+ \((.+) (?P<LEVEL>\d+)\)')


class Exctractor:

    @classmethod
    def extract_kv(cls, text: str) -> tuple[str, str] | tuple[str]:
        return tuple(s.strip() for s in split_pattern.split(text, maxsplit=1))

    @classmethod
    def extract_chance(cls, s: str) -> tuple[str, str | None]:
        match = chance_pattern.search(s.strip())
        if match:
            name = match.group('NAME')
            chance = match.group('VALUE')
            return name, chance
        return s, None

    @classmethod
    def extract_drop(cls, drop):
        drop_struct = {}
        # bestial bonds
        bond = drop.xpath('./span[@class="emph"]')
        if any(bond):
            drop_struct['name'] = split_pattern.split(
                bond.xpath('string()').get())[0]
            drop_struct['stats'] = ''.join(
                bond.xpath('../text()').getall()).strip()
            return drop_struct
        # passive ability
        ability = drop.xpath('./self::div[@class="spaced"]')
        if any(ability):
            name = drop.xpath('.//span').xpath('string()').get().strip()
            drop_struct['name'] = name
            description = drop.xpath('./div[@class="emph"]').xpath('string()')
            if any(description):
                drop_struct['description'] = description.get().strip()
            stats = drop.xpath('.//div[@class="codex-stats"]')
            if any(stats):
                stats_list = []
                for s in stats.xpath('./div[@class="codex-stat"]'):
                    stat = s.xpath('string()').get()
                    if ' / ' in stat:
                        for ss in stat.split('/'):
                            stats_list.append(
                                Exctractor.extract_kv(ss.strip()))
                    else:
                        stats_list.append(Exctractor.extract_kv(stat))
                if any(stats_list):
                    drop_struct['stats'] = stats_list
            icon = ability.xpath('.//img/@src').get()
            if icon:
                drop_struct['icon'] = UrlParser.icon(icon)
            return drop_struct
        # else
        name = drop.xpath('.//span').xpath('string()').get().strip()
        name, chance = cls.extract_chance(name)
        if chance:
            drop_struct['chance'] = chance
        drop_struct['name'] = name
        icon = drop.xpath('.//img/@src').get()
        if icon:
            drop_struct['icon'] = UrlParser.icon(icon)
        href = drop.xpath('.//a/@href').get()
        if href:
            drop_struct['href'] = href
        description = drop.xpath('./div[@class="emph"]').xpath('string()')
        if any(description):
            drop_struct['description'] = description.get().strip()
        return drop_struct

    @classmethod
    def extract_codex_id(cls, codex: str) -> list[str]:
        return codex.strip('/').split('/')[-2:]

    @classmethod
    def extract_codex_key(cls, codex: str) -> list[str]:
        return codex.strip('/')[6:]

    @classmethod
    def extract_bond(cls, bond_text: str) -> list:
        bb = []
        for b in map(lambda b: b.strip(), bond_text.split(',')):
            m = chance_pattern.match(b)
            if m:
                bb.append({
                    'name': m.group('NAME'),
                    'value': int(m.group('VALUE').strip('%')),
                    'type': 'BOND'
                })
                continue
            m = ability_pattern.match(b)
            if m:
                bb.append({
                    'name': m.group('VALUE'),
                    'type': 'ABILITY'
                })
                continue
            m = bonus_pattern.match(b)
            if m:
                bb.append({
                    'name': m.group('NAME'),
                    'value': m.group('VALUE'),
                    'type': 'BONUS'
                })
                continue
            # else
            bb.append({
                'name': b,
                'type': 'BONUS',
                'value': True
            })

        return bb

    @classmethod
    def extract_follower(cls, follower: SelectorList) -> list:
        k: str = split_pattern.split(follower.xpath(
            './text()').get(), maxsplit=1)[0].strip()
        name = follower.xpath('.//span').xpath('string()').get().strip()
        icon = follower.xpath('.//img/@src').get()
        if icon:
            icon = UrlParser.icon(icon)
        return [k, {'name': name, 'icon': icon}]

    @classmethod
    def extract_conditions(cls, text: str) -> tuple[str, list[str] | None]:
        m = condition_pattern.match(text)
        if m:
            v: str = m.group('VALUE')
            c: str = m.group('CONDITIONS')
            return [v, [s.strip() for s in c.split(',')]]
        else:
            return [text, None]

    @classmethod
    def extract_spell_level(cls, text: str):
        m = spell_level_pattern.match(text)
        if m:
            level: str = m.group('LEVEL')
            return level
        return None

    @classmethod
    def extract_number(cls, text: str) -> int | str:
        m = number_pattern.match(text)
        if m:
            num: str = m.group('NUMBER')
            return ast.literal_eval(num)
        else:
            return text
