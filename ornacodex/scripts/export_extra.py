from datetime import datetime, timezone
import json
from pathlib import Path
from scrapy.settings import Settings
import tomlkit

def run(settings: Settings):
    input_dir = Path(settings.get('EXTRA_DIR'))
    export_dir = Path(settings.get('EXPORT_EXTRA_DIR'))
    export_dir.mkdir(exist_ok=True)

    categories = ['bosses', 'monsters', 'raids']

    for category in categories:
        output = {}
        for toml_file in input_dir.joinpath(category).rglob('*.toml'):
            with toml_file.open('r', encoding='utf-8') as f:
                data = tomlkit.load(f)
                id = data.pop('id')
                output[id] = data

        json_file = export_dir.joinpath(category + '.json')
        json_file.parent.mkdir(parents=True, exist_ok=True)
        with json_file.open('w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False)

        print(f"Converted: {category} -> {json_file}")

    for toml_file in input_dir.glob('*.toml'):
        rel_path = toml_file.relative_to(input_dir)
        json_file = export_dir / rel_path.with_suffix('.json')
        with toml_file.open('r', encoding='utf-8') as f:
            data = tomlkit.load(f)
        with json_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        print(f"Converted: {toml_file} -> {json_file}")


    with open(export_dir.joinpath('index.json'), 'w') as f:
        json.dump({
            'version': settings.get('VERSION'),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'categories': categories
        }, f)
