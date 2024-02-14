from pathlib import Path

from crawler.spiders import bosses, classes, followers, items, monsters, raids, spells
from crawler.translations import langs

crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

from ._base import crawler

def run(data_dir: Path, output: str = None, generate: bool = False):
    output = Path(output) if output else Path('index.json')
    if not generate:
        crawler(data_dir=data_dir, langs=langs, crawlers=crawlers)

    