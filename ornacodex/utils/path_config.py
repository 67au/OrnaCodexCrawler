from pathlib import Path


class TmpPathConfig:

    def __init__(self, dir_path: str | Path):
        self.root = Path(dir_path)
        self.entries = self.root.joinpath('entries')
        self.miss = self.root.joinpath('miss')
        self.itemtypes = self.root.joinpath('itemtypes')


class OutputPathConfig:

    def __init__(self):
        pass


class ExtraPathConfig:

    def __init__(self, dir_path: str | Path):
        self.root = Path(dir_path)
        self.boss_scaling = self.root.joinpath('boss_scaling.toml')
        self.enemies = self.root.joinpath('enemies')
