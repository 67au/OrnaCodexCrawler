from typing import Any, Iterable
import asyncio
from urllib.parse import urlparse
import scrapy
from scrapy.http import Request
from scrapy.http.response import Response
scrapy.utils.reactor.install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

from ..utils import reflect_trans

TARGET_URL = 'https://playorna.com'

class BaseSpider(scrapy.Spider):
    allowed_domains = []

    def __init__(self, name: str | None = None, lang: str = 'en', start_ids: list = None, target_url: str = None, **kwargs: Any):
        super().__init__(name, **kwargs)
        self.lang = lang
        self.event = asyncio.Event()
        self.reflect_trans = reflect_trans(self.lang)
        self.target_url = target_url or TARGET_URL
        self.stop_request = False
        self.start_ids = start_ids or []
        self.allowed_domains.append(urlparse(self.target_url).netloc)

    def start_requests(self) -> Iterable[Request]:
        if any(self.start_ids):
            for id in self.start_ids:
                yield scrapy.FormRequest(
                    f'{self.target_url}/codex/{self.name}/{id}',
                    method='GET',
                    formdata={'lang': self.lang},
                    dont_filter=True,
                    callback=self.parse_item,
                )
        else:
            yield scrapy.Request(
                self.target_url,
                dont_filter=True,
                callback=self.parse
            )

    async def parse(self, response: Response):
        page = 1
        while not self.stop_request:
            yield scrapy.FormRequest(
                f'{self.target_url}/codex/{self.name}/',
                formdata={'p': str(page), 'lang': self.lang},
                callback=self.parse_page,
                errback=self.parse_page_404,
                method='GET'
            )
            page += 1
            await self.event.wait()
            self.event.clear()

    async def parse_page(self, response: Response):
        self.event.set()
        for elem in response.xpath('//div[@class="codex-entries"]/a'):
            # yield response.follow(elem.attrib['href'], self.parse_item)
            yield scrapy.FormRequest(
                    f"{self.target_url}{elem.attrib['href']}",
                    method='GET',
                    formdata={'lang': self.lang},
                    dont_filter=True,
                    callback=self.parse_item,
                )

    async def parse_page_404(self, response: Response):
        self.stop_request = True
        self.event.set()
