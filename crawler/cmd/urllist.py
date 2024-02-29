import heapq
import json
from pathlib import Path
from crawler.spiders import bosses, classes, followers, items, monsters, raids, spells


crawlers = [
    bosses, classes, followers, items,
    monsters, raids, spells
]

base_lang = 'en'

def run(data_dir: Path, output: str = None, generate: bool = False, target: str = None):
    index_dir = data_dir.joinpath('index')
    if output:
        urls = []
        for crawler in crawlers:
            key = crawler.CodexSpider.name
            with open(index_dir.joinpath(base_lang, f'{key}.json')) as f:
                items = json.load(f)
                item_id_set = set()
                for item in items:
                    if item['id'] not in item_id_set:
                        item_id_set.add(item['id'])
                        heapq.heappush(urls, f'/codex/{item["category"]}/{item["id"]}/')
        with open(output, 'w') as f:
            f.writelines(f'{heapq.heappop(urls)}\n' for _ in range(len(urls)))
