from collections import defaultdict
from importlib import resources


unindexed_urls = set()
for s in resources.read_text(
        'ornacodex.patches', 'unindexed_urls.txt', encoding='utf-8').splitlines():
    if s.startswith(('#')):
        continue
    unindexed_urls.add(s.strip())
