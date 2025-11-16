import re

from scrapy.selector.unified import SelectorList

from .url_utils import UrlParser

split_pattern = re.compile(r':|：')
chance_pattern = re.compile(r'(?P<NAME>.+) \((?P<VALUE>\d+(\.\d+)?\%)\)$')
ability_pattern = re.compile(r'^\+(?P<NAME>.+)\: (?P<VALUE>.+)$')
bonus_pattern = re.compile(r'^(?!\+)(?P<NAME>.+)\: (?P<VALUE>.+)$')

class Exctractor:

    @classmethod
    def extract_kv(cls, text: str) -> tuple[str, str] | tuple[str]:
        return tuple(s.strip() for s in split_pattern.split(text, maxsplit=1))

    @classmethod
    def extract_chance(cls, s: str) -> tuple[str, str] | None:
        match = chance_pattern.search(s.strip())
        if match:
            name = match.group('NAME')
            chance = match.group('VALUE')
            return name, chance
        return None

    @classmethod
    def extract_drop(cls, drop):
        drop_struct = {}
        bond = drop.xpath('./span[@class="emph"]')
        if any(bond):
            drop_struct['name'] = split_pattern.split(bond.xpath('string()').get())[0]
            drop_struct['description'] = ''.join(bond.xpath('../text()').getall()).strip()
            return drop_struct
        name = drop.xpath('.//span').xpath('string()').get().strip()
        match = cls.extract_chance(name)
        if match:
            name, chance = match
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
    def extract_codex_id(cls, codex: str) -> list:
        return codex.strip('/').split('/')[-2:]

    @classmethod
    def extract_bond(cls, bond_text: str) -> list:
        bb = []
        for b in map(lambda b: b.strip(), bond_text.split(',')):
            m = chance_pattern.match(b)
            if m:
                bb.append({
                    'name': m.group('NAME'),
                    'chance': m.group('VALUE'),
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
            bb.append({
                    'name': b.strip('+'),
                    'type': 'BUFF'
                })
            
        return bb

    @classmethod
    def extract_follower(cls, follower: SelectorList) -> list:
        k: str = split_pattern.split(follower.xpath('./text()').get(), maxsplit=1)[0].strip()
        name = follower.xpath('.//span').xpath('string()').get().strip()
        icon = follower.xpath('.//img/@src').get()
        if icon:
            icon= UrlParser.icon(icon)
        return [k, {'name': name, 'icon': icon}]