from crypt import methods
import json
from typing import Any, Iterable
import asyncio
import scrapy
from scrapy.http import Request
from scrapy.http.response import Response
scrapy.utils.reactor.install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

from ..utils import reflect_trans

BASE_URL = 'https://playorna.com'

class BaseSpider(scrapy.Spider):
    allowed_domains = ["playorna.com"]

    def __init__(self, name: str | None = None, lang: str = 'en', start_ids: list = None, **kwargs: Any):
        super().__init__(name, **kwargs)
        self.lang = lang
        self.event = asyncio.Event()
        self.reflect_trans = reflect_trans(self.lang)
        self.stop_request = False
        self.start_ids = start_ids or []

    def start_requests(self) -> Iterable[Request]:
        if any(self.start_ids):
            for id in self.start_ids:
                yield scrapy.FormRequest(
                    f'{BASE_URL}/codex/{self.name}/{id}',
                    method='GET',
                    formdata={'lang': self.lang},
                    dont_filter=True,
                    callback=self.parse_item,
                )
        else:
            yield scrapy.Request(
                BASE_URL,
                dont_filter=True,
                callback=self.parse
            )

    async def parse(self, response: Response):
        page = 1
        while not self.stop_request:
            yield scrapy.FormRequest(
                f'{BASE_URL}/codex/{self.name}/',
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
            yield response.follow(elem.attrib['href'], self.parse_item)

    async def parse_page_404(self, response: Response):
        self.stop_request = True
        self.event.set()
