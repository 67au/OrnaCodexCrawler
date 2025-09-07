from scrapy.http.response import Response

from ..utils.exctractor import Exctractor
from ..utils.url_utils import UrlParser
from ..items import Items

from ._base import BaseSpider


class Spider(BaseSpider):
    name = "items"

    def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.category_text

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = UrlParser.icon(icon)

        aura = response.xpath(
            "//div[@class='codex-page-icon']/img/@class").get().strip()
        if any(aura):
            struct['aura'] = aura

        description = response.xpath(
            "//pre[@class='codex-page-description']").xpath('string()').get().strip()
        struct['description'] = description

        exotic = response.xpath(
            "//div[@class='codex-page-meta']/span[@class='exotic']").xpath('string()').get()
        if exotic is not None:
            struct['exotic'] = exotic

        meta = response.xpath(
            "//div[@class='codex-page-meta' and not(span[@class='exotic'])]").xpath('string()').getall()
        struct['meta'] = [Exctractor.extract_kv(m.strip()) for m in meta]

        tags = response.xpath(
            "//div[@class='codex-page-tag']").xpath('string()').getall()
        if any(tags):
            struct['tags'] = [s.strip()[2:] for s in tags]

        stats = response.xpath(
            "//div[@class='codex-stats']/div[contains(@class,'codex-stat')]")
        if any(stats):
            tmp = []
            for stat in stats:
                s = stat.xpath("string()").get().strip()
                if len(stat.xpath("@class").get().split()) > 1:
                    tmp.append(('element', [s]))
                else:
                    if ' / ' in s:
                        for ss in s.split('/'):
                            tmp.append(tuple(i.strip()
                                       for i in Exctractor.extract_kv(ss.strip())))
                    elif ', ' in s:
                        for ss in s.split(','):
                            tmp.append(tuple(i.strip()
                                       for i in Exctractor.extract_kv(ss.strip())))
                    
                    else:
                        tmp.append(tuple(i.strip()
                                   for i in Exctractor.extract_kv(s)))
            struct['stats'] = tmp

        ability = response.xpath(
            "//div[@class='codex-page-description']/preceding-sibling::div[1] | //div[@class='codex-page-description']").xpath("string()").getall()
        if len(ability) == 2:
            struct['ability'] = (
                Exctractor.extract_kv(ability[0])[-1].strip(),
                ability[1].strip()
            )

        drops = response.xpath("//div[@class='codex-page'][1]/h4")
        if any(drops):
            tmp = []
            for drop in drops:
                drop_name = Exctractor.extract_kv(drop.xpath('string()').get())[0].strip()
                d = drop.xpath("./following-sibling::*[1]")
                d_list = []
                while any(d):
                    if any(d.xpath('self::hr | self::h4')):
                        break
                    d_list.append(Exctractor.extract_drop(d))
                    d = d.xpath("./following-sibling::*[1]")
                tmp.append((drop_name, d_list))
            struct['drops'] = tmp

        yield Items(struct)
