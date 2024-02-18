from scrapy.http.response import Response

from ..items import ClassesItem, Drop
from ..utils import parse_drop, parse_static_url, extract_kv

from ._base import BaseSpider

class CodexSpider(BaseSpider):
    name = "classes"

    async def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.name

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = parse_static_url(icon)

        description = response.xpath('//div[@class="codex-page-description"]').xpath('string()').get().strip()
        struct['description'] = description

        meta = response.xpath("//div[@class='codex-page-meta']")

        tier = extract_kv(meta[0].xpath('string()').get())[-1].strip()[1:]
        struct['tier'] = tier

        if len(meta) == 2:
            price = extract_kv(meta[1].xpath('string()').get())[-1].strip().split()[0].replace(',', '')
            struct['price'] = price

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

        yield ClassesItem(struct)