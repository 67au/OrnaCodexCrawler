import re
from scrapy.http.response import Response

from ..items import SpellsItem, Drop
from ..utils import parse_drop, parse_static_url, extract_kv

from ._base import BaseSpider

power_pattern = re.compile(r'\)|\d', re.IGNORECASE)
costs_pattern = re.compile(r'\d+ \W+')

def match_power(s: str) -> bool:
    return power_pattern.match(s) is not None

def match_costs(s: str) -> bool:
    return costs_pattern.match(s) is not None

multiple_pattern = re.compile(r'(?P<POWER>.+) \(x(?P<MULTI>\d+)\)$')

def extract_power(s: str):
    power = {}
    m = multiple_pattern.match(s)
    p = s
    if m:
        p = m.group('POWER')
        power['multi'] = m.group('MULTI')
    pp = p.split('-')
    if len(pp) == 1:
        power['value'] = pp[0]
    else:
        power['range'] = pp
    return power

class CodexSpider(BaseSpider):
    name = "spells"

    async def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.name

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = parse_static_url(icon)

        description = response.xpath("//div[@class='codex-page-description']").xpath('string()').get().strip()
        struct['description'] = description

        meta = response.xpath("//div[@class='codex-page-meta' and not(span[@class='exotic'])]").xpath('string()')

        elem = response.xpath("//div[contains(@class,'codex-stat')]").xpath('string()').get()

        tier, *spell_type = meta[0].get().strip().split()
        struct['tier'] = tier[1:]
        struct['spell_type'] = ''.join(spell_type)

        target = extract_kv(meta[1].get().strip())[-1].strip()
        struct['target'] = target

        stats = []
        if len(meta) > 2:
            for m in meta[2:]:
                s = m.get().strip()
                if match_power(s[-1]):
                    power = (': '.join(extract_kv(s)[1:])).strip()
                    p = tuple(i.strip() for i in power.split('|'))
                    power = {
                        'pve': extract_power(p[0])
                    }
                    if len(p) == 2:
                        power['pvp'] = extract_power(p[1][5:])
                    struct['power'] = power
                else:
                    stat = extract_kv(s)
                    stats.append([stat[0], stat[1].split()[0]])

        if elem:
            stats.append(['element', elem.strip()])
        
        if any(stats):
            struct['stats'] = stats

        tags = response.xpath("//div[@class='codex-page-tag']").xpath('string()')
        if any(tags):
            struct['tags'] = [s.get().strip()[2:] for s in tags]

        drops = response.xpath("//div[@class='codex-page'][1]/h4")
        for drop in drops:
            drop_name = extract_kv(drop.xpath('string()').get())[0].strip()
            d = drop.xpath("./following-sibling::*[1]")
            drop_list = []
            while any(d):
                if any(d.xpath('self::hr | self::h4')):
                    struct[self.reflect_trans[drop_name]] = drop_list
                    break
                if self.reflect_trans[drop_name] == 'summons':
                    for in_line in d:
                        for drop_in_line in in_line.xpath("./*[@class='drop']"):
                            drop_list.append(Drop(parse_drop(drop_in_line)))
                else:
                    drop_list.append(Drop(parse_drop(d)))
                d = d.xpath("./following-sibling::*[1]")
            struct[self.reflect_trans[drop_name]] = drop_list 

        yield SpellsItem(struct)