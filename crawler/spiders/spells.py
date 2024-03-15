from scrapy.http.response import Response

from ..items import SpellsItem, Drop
from ..utils import parse_drop, parse_static_url, extract_kv

from ._base import BaseSpider

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

        tier, *spell_type = meta[0].get().strip().split()
        struct['tier'] = tier[1:]
        struct['spell_type'] = ''.join(spell_type)

        target = extract_kv(meta[1].get().strip())[-1].strip()
        struct['target'] = target

        if len(meta) > 2:
            costs = extract_kv(meta[-1].get().strip())[-1].strip().split(' ')[0]
            struct['costs'] = costs

        if len(meta) == 4:
            power = (': '.join(extract_kv(meta[2].get().strip())[1:])).strip()
            struct['power'] = power

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
                drop_list.append(Drop(parse_drop(d)))
                d = d.xpath("./following-sibling::*[1]")
            struct[self.reflect_trans[drop_name]] = drop_list 

        yield SpellsItem(struct)