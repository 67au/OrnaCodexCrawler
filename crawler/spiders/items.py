from scrapy.http.response import Response

from ..items import ItemsItem, Drop
from ..utils import parse_drop, parse_static_url, extract_kv

from ._base import BaseSpider

class CodexSpider(BaseSpider):
    name = "items"

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

        description = response.xpath("//pre[@class='codex-page-description']").xpath('string()').get().strip()
        struct['description'] = description

        exotic = response.xpath("//div[@class='codex-page-meta']/span[@class='exotic']")
        struct['exotic'] = any(exotic)

        meta = response.xpath("//div[@class='codex-page-meta' and not(span[@class='exotic'])]").xpath('string()')

        tier = extract_kv(meta[0].get())[-1].strip()[1:]
        struct['tier'] = tier

        rarity = extract_kv(meta[1].get().strip())[-1].strip()
        struct['rarity'] = rarity

        useable_by = extract_kv(meta[2].get())[-1].strip()
        struct['useable_by'] = useable_by

        if len(meta) > 3:
            place = extract_kv(meta[3].get())[-1].strip()
            struct['place'] = place

        tags = response.xpath("//div[@class='codex-page-tag']").xpath('string()')
        if any(tags):
            struct['tags'] = [s.get().strip()[2:] for s in tags]

        stats = response.xpath("//div[@class='codex-stats']/div[contains(@class,'codex-stat')]")
        if any(stats):
            tmp = []
            for s in stats:
                t = s.xpath("string()").get().strip()
                if len(s.xpath('@class').get().split()) > 1:
                    tmp.append(['element', [t]])
                    continue
                if ' / ' in t:
                    for u in t.split('/'):
                        tmp.append([i.strip() for i in extract_kv(u.strip())])
                else:
                    tmp.append([i.strip() for i in extract_kv(t)])
                if len(tmp[-1]) == 1:
                    tmp[-1].append(True)

            struct['stats'] = tmp

        ability = response.xpath("//div[@class='codex-page-description']/preceding-sibling::div[1] | //div[@class='codex-page-description']").xpath("string()")
        if len(ability) == 2:
            struct['ability'] = {
                'name': extract_kv(ability[0].get())[-1].strip(),
                'description': ability[1].get().strip()
            }

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

        yield ItemsItem(struct)