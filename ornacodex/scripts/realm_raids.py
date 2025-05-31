import json
from pathlib import Path
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging

from ornacodex.spiders import images
from ornacodex.utils.path_config import ExtraPathConfig

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


def run(settings: Settings):
    input_dir = Path(settings.get('OUTPUT_DIR'))
    extra_dir = ExtraPathConfig(Path(settings.get('EXTRA_DIR')))
    extra_dir.root.mkdir(exist_ok=True)

    realm_file = extra_dir.root.joinpath('realm.json')

    with open(input_dir.joinpath('index.json')) as f:
        index = json.load(f)

    with open(input_dir.joinpath(index['codex'])) as f:
        codex = json.load(f)
        raids = {k: {
            'tier': v['tier'],
            'icon': v['icon'],
            'hp': v['hp'],
            'name': {}
        } for k, v in codex['main']['raids'].items()}

    for language in index['i18n'].keys():
        with open(input_dir.joinpath('i18n', f'{language}.json')) as f:
            translation = json.load(f)
            for k, v in translation['main']['raids'].items():
                raids[k]['name'][language] = v['name']

    settings.update(
        {
            'FILES_STORE': str(extra_dir.root),
        })
    crawl_images(settings, [r['icon'] for r in raids.values()])

    with open(realm_file, 'w') as f:
        json.dump(raids, f, ensure_ascii=False)
        print('Dump other realm raids finished!')
