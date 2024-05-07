from ..items import ItemTypes
from ..utils import reflect_trans, parse_codex_id
from typing import Any, Iterable
import asyncio
from urllib.parse import urlparse
import scrapy
from scrapy.http import Request
from scrapy.http.response import Response
scrapy.utils.reactor.install_reactor(
    'twisted.internet.asyncioreactor.AsyncioSelectorReactor')


TARGET_URL = 'https://playorna.com'


class ItemTypesSpider(scrapy.Spider):
    name = 'item_types'
    allowed_domains = []

    def __init__(self, name: str | None = None, lang: str = 'en', target: str = None, name_only: bool = False, **kwargs: Any):
        super().__init__(name, **kwargs)
        self.lang = lang
        self.event = asyncio.Event()
        self.reflect_trans = reflect_trans(self.lang)
        self.target_url = target or TARGET_URL
        self.stop_request = False
        self.name_only = name_only
        self.allowed_domains.append(urlparse(self.target_url).netloc)

    def start_requests(self) -> Iterable[Request]:
        yield scrapy.FormRequest(
            f'{self.target_url}/codex/items/',
            method='GET',
            formdata={'lang': self.lang},
            dont_filter=True,
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
            page = 1
            self.stop_request = False
            while not self.stop_request and not self.name_only:
                request = scrapy.FormRequest(
                    f'{self.target_url}/codex/items/',
                    formdata={
                        'p': str(page),
                        'lang': self.lang,
                        'c': value,
                    },
                    callback=self.parse_page,
                    cb_kwargs=dict(output_set=items_set),
                    errback=self.parse_page_404,
                    method='GET'
                )
                yield request
                page += 1
                await self.event.wait()
                self.event.clear()
            struct['items'] = items_set
            yield ItemTypes(struct)

    async def parse_page(self, response: Response, output_set: set):
        self.event.set()
        for elem in response.xpath('//div[@class="codex-entries"]/a'):
            output_set.add(parse_codex_id(elem.attrib['href'])[-1])

    async def parse_page_404(self, response: Response):
        self.stop_request = True
        self.event.set()
