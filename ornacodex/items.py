# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class Image(scrapy.Item):
    icon = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()

class Base(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    icon = scrapy.Field()
    aura = scrapy.Field()
    category = scrapy.Field()


class Items(Base):
    description = scrapy.Field()
    exotic = scrapy.Field()
    meta = scrapy.Field()
    tags = scrapy.Field()
    stats = scrapy.Field()
    ability = scrapy.Field()
    drops = scrapy.Field()


class Bosses(Base):
    events = scrapy.Field()
    meta = scrapy.Field()
    drops = scrapy.Field()


class Monsters(Bosses):
    pass


class Raids(Base):
    description = scrapy.Field()
    events = scrapy.Field()
    meta = scrapy.Field()
    tags = scrapy.Field()
    drops = scrapy.Field()


class Followers(Base):
    description = scrapy.Field()
    events = scrapy.Field()
    stats = scrapy.Field()
    meta = scrapy.Field()
    drops = scrapy.Field()


class Classes(Base):
    description = scrapy.Field()
    meta = scrapy.Field()
    drops = scrapy.Field()


class Spells(Base):
    tier = scrapy.Field()
    spell_type = scrapy.Field()
    description = scrapy.Field()
    tags = scrapy.Field()
    stats = scrapy.Field()
    drops = scrapy.Field()


class ItemTypes(scrapy.Item):
    type = scrapy.Field()
    name = scrapy.Field()
    items = scrapy.Field()
