import json
from pathlib import Path
from scrapy.settings import Settings
import tomlkit
import tomlkit.items

from ornacodex.utils.path_config import ExtraPathConfig


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def generate_boss_scaling(codex: dict, translations: dict, output_file: Path):
    if output_file.exists():
        with open(output_file) as f:
            tmp = tomlkit.load(f)
            boss_scaling = {b[1][0].as_string().strip(): {
                'comment': b[0][1],
                'value': b[1][1].value
            }
                for b in chunks(tmp.body, 2)}
    else:
        boss_scaling = {}
    out = {}
    for id in sorted(codex['items'].keys()):
        if codex['items'][id].get('item_type') in ('weapon', 'armor') and codex['items'][id].get('place') != 'accessory':
            out[id] = {
                'comment': tomlkit.comment(
                    " / ".join(t['main']['items'][id]['name'] for t in translations.values())),
                'value': (boss_scaling.get(id) or {}).get('value', 0)
            }
    output = sorted((boss_scaling | out).items(), key=lambda a: a[0])
    output_doc = tomlkit.document()
    for key, v in output:
        output_doc.add(v['comment'])
        output_doc.add(key, v['value'])
    with open(output_file, 'w') as f:
        tomlkit.dump(output_doc, f)


def generate_enemy(codex: dict, translations: dict, output_dir: Path):
    enemies = ['bosses', 'monsters', 'raids']
    for enemy in enemies:
        output_files = output_dir.joinpath(enemy)
        output_files.mkdir(exist_ok=True)
        for id, entry in codex[enemy].items():
            enemy_file = output_files.joinpath(f'{entry['id']}.toml')
            names = " / ".join(t['main'][enemy][id]['name']
                               for t in translations.values())
            if enemy_file.exists():
                with open(enemy_file) as f:
                    enemy_doc = tomlkit.load(f)
                    if isinstance(enemy_doc.body[0][1], tomlkit.items.Comment):
                        enemy_doc.body[0] = [None, tomlkit.comment(names)]
                    else:
                        enemy_doc.body.insert(
                            0, [None, tomlkit.comment(names)])
            else:
                enemy_doc = tomlkit.document()
                enemy_doc.add(tomlkit.comment(names))
                enemy_doc.add('id', id)

                enemy_doc.add(tomlkit.nl())
                comment_text = tomlkit.dumps({
                    'elementWeaknesses': [],
                    'elementImmunities': [],
                    'elementResistances': [],
                    'statusImmunities': []
                })
                for s in comment_text.splitlines():
                    enemy_doc.add(tomlkit.comment(s))

            with open(enemy_file, 'w') as f:
                tomlkit.dump(enemy_doc, f)


def run(settings: Settings):
    input_dir = Path(settings.get('OUTPUT_DIR'))
    extra_dir = ExtraPathConfig(Path(settings.get('EXTRA_DIR')))
    extra_dir.root.mkdir(exist_ok=True)

    with open(input_dir.joinpath('index.json')) as f:
        index = json.load(f)

    with open(input_dir.joinpath(index['codex'])) as f:
        codex = json.load(f)

    translations = {}
    for language, file_path in index['i18n'].items():
        with open(input_dir.joinpath(file_path)) as f:
            translations[language] = json.load(f)

    print('update boss scaling list')
    generate_boss_scaling(codex['main'], translations, extra_dir.boss_scaling)

    print('update enemy stats')
    generate_enemy(codex['main'], translations, extra_dir.root)
