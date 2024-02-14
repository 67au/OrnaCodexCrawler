from typing import Any, Iterable
import asyncio
import scrapy
from scrapy.http import Request
from scrapy.http.response import Response

from ..utils import reflect_trans

BASE_URL = 'https://playorna.com'

class BaseSpider(scrapy.Spider):
    allowed_domains = ["playorna.com"]
    
    def __init__(self, name: str | None = None, lang: str = 'en', **kwargs: Any):
        super().__init__(name, **kwargs)
        self.lang = lang
        self.event = asyncio.Event()
        self.reflect_trans = reflect_trans(self.lang)
        self.stop_request = False

    def start_requests(self) -> Iterable[Request]:
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