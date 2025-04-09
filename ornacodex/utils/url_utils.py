from urllib.parse import urlparse
from scrapy.utils.project import get_project_settings

settings = get_project_settings()

class UrlBuilder:

    base = settings.get('BASE_URL')
    codex = f"{base}/codex"

    @classmethod
    def category(cls, category: str) -> str:
        return f"{cls.codex}/{category}"

class UrlParser:

    @classmethod
    def icon(cls, url: str) -> str:
        return urlparse(url).path[7:]