from collections import defaultdict
from functools import cache
import hashlib
import re


key_pattern = re.compile(r'[↓↑→\-+\s.:/\\\'\(\)]')
mapping = {'↓': 'd', '↑': 'u', '→': 'r'}


class Converter:

    @classmethod
    @cache
    def convert_key(cls, key: str) -> str:
        return key_pattern.sub(lambda m: mapping.get(m.group(0), '_'), key).lower()


class UniqueKeyGenerator:

    def __init__(self):
        self.name_counter = defaultdict(int)
        self.seen_combinations = dict()

    def generate_unique_key(self, identifier: tuple[str, str]):
        key = Converter.convert_key(identifier[0])
        if identifier in self.seen_combinations:
            return self.seen_combinations[identifier]
        if self.name_counter[key] == 0:
            unique_key = key
        else:
            hash_suffix = hashlib.md5(identifier[1].encode()).hexdigest()[:8]
            unique_key = f'{key}_{hash_suffix}'
        self.seen_combinations[identifier] = unique_key
        self.name_counter[key] += 1
        return unique_key
