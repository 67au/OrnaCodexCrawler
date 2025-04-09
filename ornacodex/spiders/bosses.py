from scrapy.http.response import Response

from ..utils.url_utils import UrlParser
from ..utils.exctractor import Exctractor
from ..items import Bosses

from ._base import BaseSpider


class Spider(BaseSpider):
    name = "bosses"

    def parse_item(self, response: Response):
        struct = {}

        struct['category'] = self.category_text

        id = response.url.split('/')[-2]
        struct['id'] = id

        name = response.xpath('//h1').xpath('string()').get().strip()
        struct['name'] = name

        icon = response.xpath("//div[@class='codex-page-icon']/img/@src").get()
        struct['icon'] = UrlParser.icon(icon)

        events = response.xpath(
            '//div[@class="codex-page-description codex-page-description-highlight"]').xpath('string()')
        if any(events):
            struct['events'] = sorted(e.strip() for e in Exctractor.extract_kv(
                events.get().strip())[-1].split('/'))

        meta = response.xpath(
            "//div[@class='codex-page-meta'] | //div[@class='codex-page-description']").xpath('string()').getall()
        struct['meta'] = [Exctractor.extract_kv(m.strip()) for m in meta]

        aura = response.xpath(
            "//div[@class='codex-page-icon']/img/@class").get().strip()
        if any(aura):
            # struct['aura'] = aura
            # patch for `kin-of-kerberos`
            struct['aura'] = aura.split()[-1]

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

        yield Bosses(struct)
