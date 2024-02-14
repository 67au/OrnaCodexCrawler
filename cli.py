import argparse
import importlib
from pathlib import Path

parser = argparse.ArgumentParser(
    prog='OrnaCodexCrawler',
)

parser.add_argument('module', help='use crawler module')
parser.add_argument('-d', '--dir', action='store', default='tmp', help='use download directory, default: tmp')
parser.add_argument('-o', '--output', action='store', help='output file')
parser.add_argument('-g', '--generate', action='store_true', help='generate only')
parser.add_argument('-v', '--verbose', action='store_true')

def main() -> None:
    args = parser.parse_args()

    module = args.module

    data_dir = Path(args.dir)
    if not data_dir.exists():
        data_dir.mkdir()
    
    output = args.output
    generate = args.generate

    mod = importlib.import_module(f'crawler.cli.{module}')
    mod.run(data_dir, output, generate)
    

if __name__ == '__main__':
    main()