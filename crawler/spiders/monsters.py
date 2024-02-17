from scrapy.http.response import Response

from ..items import MonstersItem, Drop
from ..utils import parse_drop, parse_static_url, split_pattern

from ._base import BaseSpider

class CodexSpider(BaseSpider):
    name = "monsters"

    async def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.name

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = parse_static_url(icon)

        aura = response.xpath("//div[@class='codex-page-icon']/img/@class").get().strip()
        if any(aura):
            struct['aura'] = aura

        event = response.xpath('//div[@class="codex-page-description codex-page-description-highlight"]').xpath('string()')
        if any(event):
            struct['event'] = sorted(e.strip() for e in split_pattern.split(event.get().strip())[-1].split('/'))

        description = response.xpath('//div[@class="codex-page-description"]').xpath('string()')

        family = split_pattern.split(description[0].get().strip())[-1].strip()
        struct['family'] = family

        rarity = split_pattern.split(description[1].get().strip())[-1].strip()
        struct['rarity'] = rarity

        tier = split_pattern.split(response.xpath("//div[@class='codex-page-meta']").xpath('string()').get())[-1].strip()[1:]
        struct['tier'] = tier

        drops = response.xpath("//div[@class='codex-page'][1]/h4")
        for drop in drops:
            drop_name = split_pattern.split(drop.xpath('string()').get())[0].strip()
            d = drop.xpath("./following-sibling::*[1]")
            drop_list = []
            while any(d):
                if any(d.xpath('self::hr | self::h4')):
                    struct[self.reflect_trans[drop_name]] = drop_list
                    break
                drop_list.append(Drop(parse_drop(d)))
                d = d.xpath("./following-sibling::*[1]")
            struct[self.reflect_trans[drop_name]] = drop_list

        yield MonstersItem(struct)