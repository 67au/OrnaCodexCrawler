from collections import defaultdict
from functools import cache


class Converter:

    @classmethod
    @cache
    def convert_key(cls, key: str) -> str:
        return key.lower().replace(' ', '_').replace('.', '_').replace(':', '_') \
            .replace('↓', 'd').replace('↑', 'u').replace('/', '_').replace('\'', '_')

class UniqueKeyGenerator:

    def __init__(self):
        self.name_counter = defaultdict(int)
        self.seen_combinations = dict()

    def generate_unique_key(self, identifier: tuple[str, str]):
        key = identifier[0]
        if identifier in self.seen_combinations:
            return self.seen_combinations[identifier]
        if self.name_counter[key] == 0:
            unique_key = key
        else:
            unique_key = f'{key}_{self.name_counter[key]}'
        self.seen_combinations[identifier] = unique_key
        self.name_counter[key] += 1
        return unique_key