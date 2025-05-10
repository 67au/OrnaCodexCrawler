import argparse
import importlib

from scrapy.utils.project import get_project_settings

def main():
    parser = argparse.ArgumentParser(
        prog="OrnaCodexCrawler",
    )
    parser.add_argument('command', help='Command')
    parser.add_argument('--tmp', help="tmp dir")
    parser.add_argument('--output', help="output dir")
    parser.add_argument('--extra', help="extra dir")
    parser.add_argument('--dump', help="dump dir")
    parser.add_argument('--export', help="export dir")
    parser.add_argument('--httpcache', action='store_true', help='enable scrapy httpcache')
    parser.add_argument('--base', help='Set BASE_URL')

    args = parser.parse_args()
    command = args.command
    try:
        mod = importlib.import_module(f'ornacodex.scripts.{command}')
    except Exception as e:
        print(f'Load module {command} failed: {e}')
        exit(1)

    settings  = get_project_settings()
    if args.tmp:
        settings.set('TMP_DIR', args.tmp)
    if args.output:
        settings.set('OUTPUT_DIR', args.output)
    if args.extra:
        settings.set('EXTRA_DIR', args.extra)
    if args.dump:
        settings.set('DUMP_DIR', args.dump)
    if args.export:
        settings.set('EXPORT_EXTRA_DIR', args.export)
    if args.httpcache:
        settings.set('HTTPCACHE_ENABLED', True)
    if args.base:
        settings.set('BASE_URL', args.base)
    mod.run(settings)

if __name__ == '__main__':
    main()
