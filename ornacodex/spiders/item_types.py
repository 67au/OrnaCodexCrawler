import asyncio
from collections.abc import Iterable
import scrapy

from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.utils.project import get_project_settings

from ..items import ItemTypes
from ..utils.exctractor import Exctractor
from ..utils.url_utils import UrlBuilder

settings = get_project_settings()


class Spider(scrapy.Spider):
    name = "item_types"
    allowed_domains = []

    def __init__(
        self,
        language: str = None,
        name_only: bool = False,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.language = language or settings.get('BASE_LANGUAGE')
        self.name_only = name_only
        self.category_url = UrlBuilder.category('items')
        # self.event = asyncio.Event()

    def start_requests(self) -> Iterable[Request]:
        yield scrapy.FormRequest(
            f"{self.category_url}",
            method='GET',
            formdata={'lang': self.language},
            callback=self.parse,
        )

    async def parse(self, response: Response):
        options: scrapy.Selector = response.xpath('//select[@name="c"]/option')
        struct = {}
        for option in options:
            value = option.attrib['value']
            if value == '':
                continue
            name = option.xpath('string()').get().strip()
            struct['type'] = value
            struct['name'] = name
            items_set = set()
            response.meta.update({'c': value})
            if not self.name_only:
                yield self.parse_page(response, items_set)
            struct['items'] = items_set
            yield ItemTypes(struct)

    def parse_page(self, response: Response, output: set):
        page = response.meta.get("page") or 1
        c = response.meta.get("c")
        return scrapy.FormRequest(
            url=self.category_url,
            method='GET',
            formdata={'p': str(page), 'lang': self.language, 'c': c},
            callback=self.parse_list,
            cb_kwargs=dict(output=output),
            errback=self.parse_err,
            meta={'page': page+1, 'c': c}
        )

    async def parse_list(self, response: Response, output: set):
        for elem in response.xpath('//div[@class="codex-entries"]/a'):
            output.add(Exctractor.extract_codex_id(elem.attrib['href'])[-1])
        yield self.parse_page(response, output)

    async def parse_err(self, response: Response):
        pass
