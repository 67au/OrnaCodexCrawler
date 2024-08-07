import re
from urllib.parse import urlparse

from .translations import TRANSLATION

href_keys = ['dropped_by', 'upgrade_materials', 'skills', 'learned_by', 'requirements', 'drops', 'celestial_classes']

split_pattern = re.compile(r':|：')

def extract_kv(text: str) -> tuple[str, str] | tuple[str]:
    return tuple(s.strip() for s in split_pattern.split(text, maxsplit=1))

def reflect_trans(lang: str) -> dict:
    return dict(zip(TRANSLATION[lang].values(), TRANSLATION[lang].keys()))

chance_pattern = re.compile(r'(?P<NAME>.+) \((?P<VALUE>\d+(\.\d+)?\%)\)$')

def extract_chance(s: str) -> tuple[str, str] | None:
    match = chance_pattern.search(s.strip())
    if match:
        name = match.group('NAME')
        chance = match.group('VALUE')
        return name, chance
    return None

def parse_drop(drop) -> dict:
    drop_struct = {}
    bond = drop.xpath('./span[@class="emph"]')
    if any(bond):
        drop_struct['name'] = split_pattern.split(bond.xpath('string()').get())[0]
        drop_struct['description'] = ''.join(bond.xpath('../text()').getall()).strip()
        return drop_struct
    name = drop.xpath('.//span').xpath('string()').get().strip()
    match = extract_chance(name)
    if match:
        name, chance = match
        drop_struct['chance'] = chance
    drop_struct['name'] = name
    icon = drop.xpath('.//img/@src').get()
    if icon:
        drop_struct['icon'] = parse_static_url(icon)
    href = drop.xpath('.//a/@href').get()
    if href:
        drop_struct['href'] = href
    description = drop.xpath('./div[@class="emph"]').xpath('string()')
    if any(description):
        drop_struct['description'] = description.get().strip()
    return drop_struct

def parse_codex_id(codex: str) -> list:
    return codex.strip('/').split('/')[-2:]

def parse_static_url(url: str) -> str:
    return urlparse(url).path[7:]
