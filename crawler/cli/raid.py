import json
from pathlib import Path

from crawler.spiders import raids
from crawler.translations import langs

crawlers = [
    raids
]

from ._base import crawler

def run(data_dir: Path, output: str = None, generate: bool = False):
    output = Path(output) if output else Path('raid-hp.json')
    if not generate:
        crawler(data_dir=data_dir, langs=langs, crawlers=crawlers)

    raid = dict()
    for lang in langs:
        with open(data_dir.joinpath(f'{lang}/raids.json'), 'r') as fp:
            d = json.load(fp)
            for item in d:
                if raid.get(item['tier']) is None:
                    raid[item['tier']] = {}
                if raid[item['tier']].get(item['id']) is None:
                    raid[item['tier']][item['id']] = {'name': {}}
                raid[item['tier']][item['id']]['name'][lang] = item['name']
                if raid[item['tier']][item['id']].get('hp') is None:
                    # raid[item['tier']][item['id']]['tier'] = int(item['tier'])
                    raid[item['tier']][item['id']]['hp'] = int(item['hp'])
                    raid[item['tier']][item['id']]['icon'] = item['icon']
            
    with open(output, 'w', encoding='utf-8') as fp:
        json.dump(raid, fp, indent=4, ensure_ascii=False, sort_keys=True)