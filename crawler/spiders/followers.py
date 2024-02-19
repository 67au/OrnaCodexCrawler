from scrapy.http.response import Response

from ..items import FollowersItem, Drop
from ..utils import parse_drop, parse_static_url, extract_kv

from ._base import BaseSpider

class CodexSpider(BaseSpider):
    name = "followers"
    
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

        description = response.xpath('//div[@class="codex-page-description"]').xpath('string()')
        struct['description'] = description.get().strip()

        event = response.xpath('//div[@class="codex-page-description codex-page-description-highlight"]').xpath('string()')
        if any(event):
            struct['event'] = sorted(e.strip() for e in extract_kv(event.get().strip())[-1].split('/'))

        family = extract_kv(description[1].get().strip())[-1].strip()
        struct['family'] = family

        rarity = extract_kv(description[2].get().strip())[-1].strip()
        struct['rarity'] = rarity

        tier = extract_kv(response.xpath("//div[@class='codex-page-meta']").xpath('string()').get())[-1].strip()[1:]
        struct['tier'] = tier

        stats = response.xpath("//dl[@class='stats']")
        stats_iter = zip(stats.xpath("./dt/text()").getall(), stats.xpath("./dd/text()").getall())
        struct['stats'] = list(stats_iter)

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

        yield FollowersItem(struct)