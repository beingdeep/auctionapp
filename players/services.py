import csv
from io import StringIO, TextIOWrapper

from players.models import Player


def _row_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def _upsert_player(tournament, row):
    name = str(_row_value(row, "name", "player", "player name", "full name")).strip()
    if not name:
        return None

    player, _ = Player.objects.get_or_create(
        tournament=tournament,
        name=name,
        defaults={"sport_type": tournament.sport_type},
    )
    player.sport_type = tournament.sport_type
    player.role_position = str(_row_value(row, "preferred position", "position", "role")).strip()
    player.city = str(_row_value(row, "city")).strip()
    player.notes = str(_row_value(row, "notes")).strip()
    age_value = _row_value(row, "age")
    base_price_value = _row_value(row, "base price", "price")
    player.age = int(age_value) if str(age_value).strip() else 0
    player.base_price = base_price_value or 0
    player.save()
    return player


def _import_name_list(tournament, raw_content):
    imported = []
    names = []
    for line in raw_content.splitlines():
        parts = [part.strip() for part in line.split(",")]
        names.extend([part for part in parts if part])

    for name in names:
        player = _upsert_player(tournament, {"name": name})
        if player:
            imported.append(player)
    return imported


def import_players_from_file(tournament, upload):
    imported = []
    extension = upload.name.lower().rsplit(".", 1)[-1]

    if extension != "csv":
        raise ValueError("Unsupported file type. Upload CSV only for now.")

    wrapper = TextIOWrapper(upload.file, encoding="utf-8-sig")
    raw_content = wrapper.read()
    wrapper.close()

    sample = raw_content.lstrip()
    if not sample:
        return imported

    first_line = sample.splitlines()[0].lower()
    if "name" not in first_line and "," in sample:
        return _import_name_list(tournament, raw_content)

    reader = csv.DictReader(StringIO(raw_content))
    for row in reader:
        player = _upsert_player(tournament, {key.strip().lower(): value for key, value in row.items()})
        if player:
            imported.append(player)
    return imported
