import hashlib


def get_entry_key(ent: dict):
    return f"{ent['category']}/{ent['id']}"


def get_hash(content: str):
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]