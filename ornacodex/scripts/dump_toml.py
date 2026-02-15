import json
from pathlib import Path
import shutil

from scrapy.settings import Settings
import tomlkit


def main(settings: Settings, input: Path = None, output: Path = None):
    input_dir = Path(input or 'output')
    output_dir = Path(output or 'dump')
    if (output_dir.exists() and output_dir.is_dir()):
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_dir.joinpath('manifest.json')) as f:
        manifest = json.load(f)

    with open(input_dir.joinpath(manifest['files']['codex'])) as f:
        codex = json.load(f)
    with open(output_dir.joinpath('codex.yaml'), 'w') as f:
        tomlkit.dump({
            **codex,
            'entries': {f'{ent['category']}/{ent['id']}': ent for ent in codex['entries']},
        }, f, sort_keys=True)

    output_dir.joinpath('locales').mkdir(parents=True, exist_ok=True)
    for language, filename in manifest['files']['locales'].items():
        with open(input_dir.joinpath('locales', filename)) as f:
            translation = json.load(f)
        with open(output_dir.joinpath('locales', f'{language}.toml'), 'w') as f:
            tomlkit.dump({
                **translation,
                'entries': {f'{ent['category']}/{ent['id']}': ent for ent in translation['entries']},
                'abilities': {a['id']: a for a in translation['abilities']}
            }, f, sort_keys=True)


def run(settings: Settings, **kwargs):
    main(settings=settings, **kwargs)
