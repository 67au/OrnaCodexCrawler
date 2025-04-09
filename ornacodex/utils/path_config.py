from pathlib import Path


class TmpPathConfig:

    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir)
        self.entries = self.root.joinpath('entries')
        self.miss = self.root.joinpath('miss')
        self.itemtypes = self.root.joinpath('itemtypes')
        self.categories = self.root.joinpath('categories')


class ExtraPathConfig:

    def __init__(self, extra_dir: str | Path):
        self.root = Path(extra_dir)
        self.boss_scaling = self.root.joinpath('boss_scaling.toml')
