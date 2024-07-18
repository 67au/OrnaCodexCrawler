import heapq
import json
from pathlib import Path

base_lang = 'en'


def run(data_dir: Path, output: str = None, generate: bool = False, target: str = None, **kwargs):
    index_dir = data_dir.joinpath('entries')
    item_types_dir = data_dir.joinpath('item_types')
    if output:
        ids = []
        with open(index_dir.joinpath(base_lang, 'items.json')) as fa, \
            open(item_types_dir.joinpath(base_lang, 'item_types.json')) as fb:
            items = json.load(fa)
            types = json.load(fb)
            types_set = set()
            for t in types:
                if t['type'] in ('weapon', 'armor'):
                    for id in t['items']:
                        types_set.add(id)
            for item in items:
                if item['id'] in types_set and item['place'] != 'Accessory':
                    heapq.heappush(ids, item["id"])
        with open(output, 'w') as f:
            f.write('\n'.join(heapq.heappop(ids) for _ in range(len(ids))))
