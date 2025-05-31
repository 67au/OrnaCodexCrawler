from collections.abc import Iterable
import scrapy
from scrapy.http.response import Response
from scrapy.utils.project import get_project_settings

from ornacodex.items import Image
from ornacodex.spiders._base import UrlBuilder


settings = get_project_settings()


class Spider(scrapy.Spider):
    name = "images"

    custom_settings = {
        'ITEM_PIPELINES': {
            'ornacodex.pipelines.IconFilesPipeline': 1,
        },
        'FILES_URLS_FIELD': 'file_urls',
        'FILES_RESULT_FIELD': 'files',
    }

    def __init__(
        self,
        images: list[str],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.images = images

    def start_requests(self) -> Iterable[scrapy.Request]:
        yield scrapy.Request(UrlBuilder.base, self.parse)

    def parse(self, response: Response):
        for image in self.images:
            if image:
                item = Image()
                item['file_urls'] = [UrlBuilder.icon(image)]
                item['icon'] = image
                yield item
