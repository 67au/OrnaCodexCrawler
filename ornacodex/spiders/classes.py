from scrapy.http.response import Response

from ..utils.url_utils import UrlParser
from ..utils.exctractor import Exctractor
from ..items import Classes

from ._base import BaseSpider


class Spider(BaseSpider):
    name = "classes"

    def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.category_text

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = UrlParser.icon(icon)

        description = response.xpath(
            "//div[@class='codex-page-description']").xpath('string()').get().strip()
        struct['description'] = description

        meta = response.xpath(
            "//div[@class='codex-page-meta']").xpath('string()').getall()
        struct['meta'] = [Exctractor.extract_kv(m.strip()) for m in meta]

        drops = response.xpath("//div[@class='codex-page'][1]/h4")
        if any(drops):
            tmp = []
            for drop in drops:
                drop_name = Exctractor.extract_kv(
                    drop.xpath('string()').get())[0].strip()
                d = drop.xpath("./following-sibling::*[1]")
                d_list = []
                while any(d):
                    if any(d.xpath('self::hr | self::h4')):
                        break
                    d_list.append(Exctractor.extract_drop(d))
                    d = d.xpath("./following-sibling::*[1]")
                tmp.append((drop_name, d_list))
            struct['drops'] = tmp

        yield Classes(struct)
