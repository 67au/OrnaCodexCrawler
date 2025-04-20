import json
from pathlib import Path

from scrapy.settings import Settings
import tomlkit


def run(settings: Settings):
    input_dir = Path(settings.get('OUTPUT_DIR'))
    dump_dir = Path(settings.get('DUMP_DIR'))
    dump_dir.mkdir(exist_ok=True)

    with open(input_dir.joinpath('index.json')) as f:
        index = json.load(f)

    with open(input_dir.joinpath(index['codex'])) as f:
        codex = json.load(f)
    with open(dump_dir.joinpath('codex.toml'), 'w') as f:
        tomlkit.dump(codex, f, sort_keys=True)

    dump_dir.joinpath('i18n').mkdir(exist_ok=True)
    for language in index['i18n'].keys():
        with open(input_dir.joinpath('i18n', f'{language}.json')) as f:
            translation = json.load(f)
        with open(dump_dir.joinpath('i18n', f'{language}.toml'), 'w') as f:
            tomlkit.dump(translation, f,sort_keys=True)