from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

from ..spiders import images
from ..patches.image_urls import image_urls

from twisted.internet import asyncioreactor
asyncioreactor.install()

def crawl_images(settings: Settings, icons: list[str]):
    from twisted.internet import reactor, defer 
    configure_logging()

    @defer.inlineCallbacks
    def crawl():
        runner = CrawlerRunner(settings=settings)
        runner.crawl(images.Spider, images=icons)
        yield runner.join()

        reactor.callFromThread(reactor.stop)

    crawl()
    reactor.run()

def main(settings: Settings, input: Path = None, output: Path = None):
    input_dir = Path(input or 'output')
    output_dir = Path(output or 'build')
    if (output_dir.exists() and output_dir.is_dir()):
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_dir.joinpath('manifest.json')) as f:
        manifest = json.load(f)

    with open(input_dir.joinpath(manifest['files']['codex'])) as f:
        codex = json.load(f)
        icons = codex['icons'].values()
        entry_icons = [entry['icon'] for entry in codex['entries']]
    
    images = [*icons, *entry_icons, *image_urls]

    settings.update({'FILES_STORE': str(output_dir)})
    crawl_images(settings, images)

    manifest = {
        'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }

    with open(output_dir.joinpath('manifest.json'), 'w') as f:
        json.dump(manifest, f, ensure_ascii=False)

def run(settings: Settings, **kwargs):
    main(settings=settings, **kwargs)