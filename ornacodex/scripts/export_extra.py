from datetime import datetime, timezone
import json
from pathlib import Path
from scrapy.settings import Settings
import tomlkit

def run(settings: Settings):
    input_dir = Path(settings.get('EXTRA_DIR'))
    export_dir = Path(settings.get('EXPORT_EXTRA_DIR'))
    export_dir.mkdir(exist_ok=True)

    for toml_file in input_dir.rglob('*.toml'):
        rel_path = toml_file.relative_to(input_dir)
        json_file = export_dir / rel_path.with_suffix('.json')
        json_file.parent.mkdir(parents=True, exist_ok=True)

        with toml_file.open('r', encoding='utf-8') as f:
            data = tomlkit.load(f)

        with json_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Converted: {toml_file} -> {json_file}")

        with open(export_dir.joinpath('index.json'), 'w') as f:
            json.dump({
                'version': settings.get('VERSION'),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, f)
