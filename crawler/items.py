# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ItemTypes(scrapy.Item):
    type = scrapy.Field()
    name = scrapy.Field()
    items = scrapy.Field()

class Drop(scrapy.Item):
    name = scrapy.Field()
    href = scrapy.Field()
    icon = scrapy.Field()
    chance = scrapy.Field()
    description = scrapy.Field()

class BaseItem(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    icon = scrapy.Field()
    aura = scrapy.Field()
    category = scrapy.Field()

class ItemsItem(BaseItem):
    description = scrapy.Field()
    tier = scrapy.Field()
    rarity = scrapy.Field()
    exotic = scrapy.Field()
    useable_by = scrapy.Field()
    place = scrapy.Field()
    tags = scrapy.Field()
    stats = scrapy.Field()
    ability = scrapy.Field()

    causes = scrapy.Field()
    cures = scrapy.Field()
    dropped_by = scrapy.Field()
    gives = scrapy.Field()
    immunities = scrapy.Field()
    upgrade_materials = scrapy.Field()

class MonstersItem(BaseItem):
    event = scrapy.Field()
    family = scrapy.Field()
    rarity = scrapy.Field()
    tier = scrapy.Field()

    skills = scrapy.Field()
    abilities = scrapy.Field()
    drops = scrapy.Field()

class BossesItem(BaseItem):
    event = scrapy.Field()
    family = scrapy.Field()
    rarity = scrapy.Field()
    tier = scrapy.Field()

    skills = scrapy.Field()
    abilities = scrapy.Field()
    drops = scrapy.Field()

class RaidsItem(BaseItem):
    description = scrapy.Field()
    event = scrapy.Field()
    tier = scrapy.Field()
    hp = scrapy.Field()

    tags = scrapy.Field()

    skills = scrapy.Field()
    abilities = scrapy.Field()
    drops = scrapy.Field()

class FollowersItem(BaseItem):
    description = scrapy.Field()
    event = scrapy.Field()
    family = scrapy.Field()
    rarity = scrapy.Field()
    tier = scrapy.Field()

    stats = scrapy.Field()

    skills = scrapy.Field()
    bestial_bond = scrapy.Field()

class SpellsItem(BaseItem):
    description = scrapy.Field()
    tier = scrapy.Field()
    spell_type = scrapy.Field()
    target = scrapy.Field()
    power = scrapy.Field()
    costs = scrapy.Field()

    tags = scrapy.Field()

    causes = scrapy.Field()
    cures = scrapy.Field()
    dropped_by = scrapy.Field()
    gives = scrapy.Field()
    learned_by = scrapy.Field()
    summons = scrapy.Field()

class ClassesItem(BaseItem):
    description = scrapy.Field()
    tier = scrapy.Field()
    price = scrapy.Field()

    requirements = scrapy.Field()
    skills = scrapy.Field()
    abilities = scrapy.Field()
    celestial_classes = scrapy.Field()
