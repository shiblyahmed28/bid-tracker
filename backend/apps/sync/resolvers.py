"""Person/Client dedup (§8). Case-insensitive match on the whitespace-stripped
name; unlike normalizers.py these touch the database, so callers running a
dry-run rely on the whole sync being wrapped in a rolled-back transaction
rather than any special-casing here.
"""

from .normalizers import norm_text


def resolve_person(cache, raw_name):
    from apps.bids.models import Person

    name = norm_text(raw_name)
    if name is None:
        return None

    key = name.lower()
    if key in cache:
        return cache[key]

    person = Person.objects.filter(canonical_name__iexact=name).first()
    if person is None:
        person = Person.objects.create(canonical_name=name)
    elif person.canonical_name != name and name not in person.aliases:
        person.aliases = [*person.aliases, name]
        person.save(update_fields=["aliases"])

    cache[key] = person
    cache[person.canonical_name.lower()] = person
    return person


def resolve_client(cache, raw_name):
    from apps.bids.models import Client

    name = norm_text(raw_name)
    if name is None:
        return None

    key = name.lower()
    if key in cache:
        return cache[key]

    client = Client.objects.filter(canonical_name__iexact=name).first()
    if client is None:
        client = Client.objects.create(name=name, canonical_name=name)

    cache[key] = client
    cache[client.canonical_name.lower()] = client
    return client
