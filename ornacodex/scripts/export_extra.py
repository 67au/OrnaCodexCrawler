from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from scrapy.settings import Settings
import tomlkit

from ornacodex.utils import get_hash


def export_enemies(input_dir: Path):
    enemies = []
    for toml_file in input_dir.rglob('enemies/**/*.toml'):
        with toml_file.open('r') as f:
            enemy = tomlkit.load(f)
            id = enemy.get('id')
            data = enemy.get('data')
            if data is not None:
                enemies.append({
                    'id': id,
                    'data': data
                })
    return enemies

def export_boss_scaling(input_dir: Path):
    toml_file = input_dir.joinpath('boss_scaling.toml')
    with toml_file.open('r') as f:
        bs = tomlkit.load(f)
    return bs

def main(settings: Settings, input: Path = None, output: Path = None):
    input_dir = Path(input or 'input')
    output_dir = Path(output or 'build')
    if (output_dir.exists() and output_dir.is_dir()):
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    enemies = export_enemies(input_dir)
    file_content = json.dumps(enemies, ensure_ascii=False)
    file_hash = get_hash(file_content)
    file_name = f'enemies.{file_hash}.json'
    with open(output_dir.joinpath(file_name), 'w') as f:
        f.write(file_content)
    files['enemies'] = file_name
    print(f"Converted: enemies -> {file_name}")


    boss_scaling = export_boss_scaling(input_dir)
    file_content = json.dumps(boss_scaling, ensure_ascii=False)
    file_hash = get_hash(file_content)
    file_name = f'boss_scaling.{file_hash}.json'
    with open(output_dir.joinpath(file_name), 'w') as f:
        f.write(file_content)
    files['boss_scaling'] = file_name
    print(f"Converted: boss_scaling -> {file_name}")

    manifest = {
        'version': settings.get('VERSION'),
        'last_updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'files': files
    }

    file_name = 'manifest.json'
    with open(output_dir.joinpath(file_name), 'w') as f:
        json.dump(manifest, f, ensure_ascii=False)
    print(f"Converted: boss_scaling -> {file_name}")

    ###
    print('=== Manifest ===')
    print(json.dumps(manifest, ensure_ascii=False, indent=4))


def run(settings: Settings, **kwargs):
    main(settings=settings, **kwargs)
