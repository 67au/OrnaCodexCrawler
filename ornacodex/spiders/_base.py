from abc import abstractmethod
from collections.abc import Iterable
import scrapy

from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.utils.project import get_project_settings

from ..utils.url_utils import UrlBuilder

settings = get_project_settings()


class BaseSpider(scrapy.Spider):
    name = "_base"
    allowed_domains = []

    def __init__(
        self,
        name: str = None,
        language: str = None,
        start_ids: list[str] | str = None,
        **kwargs
    ) -> None:
        super().__init__(name, **kwargs)
        self.language = language or settings.get('BASE_LANGUAGE')
        self.category_url = UrlBuilder.category(self.name)
        if isinstance(start_ids, str):
            self.start_ids = [start_ids]
        else:
            self.start_ids = start_ids or []

    def start_requests(self) -> Iterable[Request]:
        yield scrapy.FormRequest(
            self.category_url,
            method='GET',
            formdata={'lang': self.language},
            callback=self.parse_pre,
        )

    def parse_pre(self, response: Response):
        self.category_text = response.xpath(
            '//h1[@class="herotext"]').xpath('string()').get().strip()
        if any(self.start_ids):
            for id in self.start_ids:
                yield scrapy.FormRequest(
                    f"{self.category_url}/{id}",
                    method='GET',
                    formdata={'lang': self.language},
                    callback=self.parse_item,
                )
        else:
            yield self.parse(response)

    def parse(self, response: Response) -> scrapy.FormRequest:
        page = response.meta.get("page") or 1
        return scrapy.FormRequest(
            url=self.category_url,
            method='GET',
            formdata={'p': str(page), 'lang': self.language},
            callback=self.parse_page,
            errback=self.parse_err,
            meta={'page': page+1}
        )

    def parse_page(self, response: Response):
        for entry in response.xpath('//div[@class="codex-entries"]/a'):
            id = entry.attrib['href']
            yield scrapy.FormRequest(
                f"{UrlBuilder.base}{id}",
                method='GET',
                formdata={'lang': self.language},
                callback=self.parse_item,
            )
        yield self.parse(response)

    @abstractmethod
    def parse_item(self, response: Response):
        pass

    def parse_err(self, response: Response):
        pass
