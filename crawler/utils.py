import re
from urllib.parse import urlparse

from .translations import TRANSLATION

split_pattern = re.compile(r':|：')

def reflect_trans(lang: str) -> dict:
    return dict(zip(TRANSLATION[lang].values(), TRANSLATION[lang].keys()))

chance_pattern = re.compile(r'(?P<name>.+) \((?P<chance>\d+\%)\)$')

def parse_drop(drop) -> dict:
    drop_struct = {}
    bond = drop.xpath('./span[@class="emph"]')
    if any(bond):
        drop_struct['name'] = split_pattern.split(bond.xpath('string()').get())[0]
        drop_struct['description'] = ''.join(bond.xpath('../text()').getall()).strip()
        return drop_struct
    name = drop.xpath('.//span').xpath('string()').get().strip()
    match = chance_pattern.search(name)
    if match:
        name = match.group('name')
        chance = match.group('chance')
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