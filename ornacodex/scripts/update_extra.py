import json
from pathlib import Path
from itertools import batched
from scrapy.settings import Settings
import tomlkit

from ornacodex.utils import get_entry_key
from ornacodex.utils.path_config import ExtraPathConfig


def get_names(translations: dict, key: str):
    names = {lang: translation[key]
             for lang, translation in translations.items()}
    return names


def is_upgradable(ent: dict):
    return ent.get('item_type') in ('weapon', 'armor') and ent.get('place') != 'accessory'


def update_boss_scaling(entries: list, translations: dict, extra_dir: ExtraPathConfig):
    boss_scaling = {}
    if extra_dir.boss_scaling.exists():
        with extra_dir.boss_scaling.open('r') as f:
            bs = tomlkit.load(f)
            for s in batched(bs.body, 2):
                comment, kv = s
                k = kv[0].as_string().strip()
                boss_scaling[k] = {
                    'name': comment[1],
                    'value': kv[1].value
                }
    boss_scaling_new = {}
    for entry in filter(lambda e: e['category'] == 'items' and is_upgradable(e), entries):
        id = entry['id']
        value = boss_scaling.get(id)
        boss_scaling_new[id] = {
            'name': tomlkit.comment(
                ' / '.join(get_names(translations, get_entry_key(entry)).values())
                ),
            'value': 0 if value is None else value.get('value', 0)
        }

    output_doc = tomlkit.document()
    for k, v in sorted((boss_scaling | boss_scaling_new).items(), key=lambda bs: bs[0]):
        output_doc.add(v['name'])
        output_doc.add(k, v['value'])
    with extra_dir.boss_scaling.open('w') as f:
        tomlkit.dump(output_doc, f)


def update_enemies(entries: list, translations: dict, extra_dir: ExtraPathConfig):
    enemies_dir = extra_dir.enemies
    enemy_categories = {'raids', 'bosses', 'monsters'}
    for category in enemy_categories:
        enemies_dir.joinpath(category).mkdir(exist_ok=True)

    for entry in filter(lambda e: e['category'] in enemy_categories, entries):
        key = get_entry_key(entry)
        enemy_file = enemies_dir.joinpath(f'{key}.toml')

        enemy_doc = tomlkit.document()
        if enemy_file.exists():
            with enemy_file.open('r+') as f:
                enemy_doc = tomlkit.load(f)
                enemy_doc['name'] = get_names(translations, key)
        else:
            # add new enemies
            print('New Enemy Found:', key)

            enemy_doc.add('id', key)
            enemy_doc.add(tomlkit.nl())
            enemy_doc.add('name', get_names(translations, key))
            enemy_doc.add(tomlkit.nl())
            comment_text = tomlkit.dumps({'data': {
                'elementWeaknesses': [],
                'elementImmunities': [],
                'elementResistances': [],
                'statusImmunities': []
            }})
            for s in comment_text.splitlines():
                enemy_doc.add(tomlkit.comment(s))

        with open(enemy_file, 'w') as f:
            tomlkit.dump(enemy_doc, f)


def main(settings: Settings, input: Path = None, output: Path = None):
    input_dir = Path(input or 'output')
    output_dir = Path(output or 'extra')
    extra_dir = ExtraPathConfig(output_dir)

    with open(input_dir.joinpath('manifest.json')) as f:
        manifest = json.load(f)

    with open(input_dir.joinpath(manifest['files']['codex'])) as f:
        codex = json.load(f)
        entries = codex['entries']

    translations = {}
    for language, filename in manifest['files']['locales'].items():
        translations[language] = {}
        with open(input_dir.joinpath('locales', filename)) as f:
            translation = json.load(f)
            translations[language] = {
                get_entry_key(ent): ent['name'] for ent in translation['entries']
            }
    print('Updating Enemies...')
    update_enemies(entries, translations, extra_dir)
    print('Enemies Updated!')

    print('Updating BossScaling...')
    update_boss_scaling(entries, translations, extra_dir)
    print('BossScaling Updated!')

def run(settings: Settings, **kwargs):
    main(settings=settings, **kwargs)
