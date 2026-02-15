import argparse
import importlib
from pathlib import Path

from scrapy.utils.project import get_project_settings


def main():
    settings = get_project_settings()
    supported_languages = settings.get('SUPPORTED_LANGUAGES', [])

    parser = argparse.ArgumentParser(
        prog="OrnaCodexCrawler",
    )
    parser.add_argument('command', help='Command')
    parser.add_argument('--tmp', help="tmp dir")
    parser.add_argument('--input', help="input dir")
    parser.add_argument('--output', help="output dir")
    parser.add_argument('--languages', help="supported languages: " + ', '.join(supported_languages))
    parser.add_argument('--httpcache', action='store_true',
                        help='enable scrapy httpcache')
    parser.add_argument('--disallow-patches', action='store_true',
                        help='disallow apply unindexed urls patches')
    parser.add_argument('--base', help='Set BASE_URL')

    args = parser.parse_args()
    command = args.command
    try:
        mod = importlib.import_module(f'ornacodex.scripts.{command}')
    except Exception as e:
        print(f'Load module {command} failed: {e}')
        exit(1)

   
    input_struct = {
        'input': Path(args.input) if args.input else None,
        'output': Path(args.output) if args.output else None,
    }

    if args.tmp:
        settings.set('TMP_DIR', args.tmp)
    if args.languages:
        languages: list[str] = []
        for lang in args.languages.strip().split(','):
            if lang in supported_languages:
                languages.append(lang)
            else:
                print(f'Not supported: ' + lang)
        if 'en' not in languages:
            languages.append('en')
            print('Add base language: en')
        print('Run crawler in: ' + ', '.join(languages))
        settings.set('SUPPORTED_LANGUAGES', languages)     
    if args.httpcache:
        settings.set('HTTPCACHE_ENABLED', True)
        settings.set('HTTPCACHE_DIR',  'httpcache')
        settings.set('HTTPCACHE_STORAGE',
                     'scrapy.extensions.httpcache.FilesystemCacheStorage')
    if args.disallow_patches:
        settings.set('PATCHES_ENABLED', False)
    if args.base:
        settings.set('BASE_URL', args.base)
    mod.run(settings, **input_struct)


if __name__ == '__main__':
    main()
