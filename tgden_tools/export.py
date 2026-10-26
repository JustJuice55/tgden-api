"""Result files, CSV formula safety, and rollback for partial write failures."""
import csv
import json
import os
from pathlib import Path
import shutil
import tempfile

_FILES = ("result.json", "result.csv", "metadata.json")
_DEFAULT_COLUMNS = {
    "channel-posts": ("channel", "message_url", "text", "posted_at", "views"),
    "buyer-preview": ("chat_username", "chat_title", "snippet", "posted_at", "tg_link"),
    "classifieds": ("id", "title", "country", "category", "price_amount", "price_currency", "market_url"),
    "post-search": ("channel_username", "telegram_msg_id", "snippet", "posted_at", "views", "tme_url"),
    "lookup": ("username", "lookup_status", "title", "telegram_url", "catalog_url"),
}


def csv_cell(value):
    """Keep JSON unchanged; prefix risky CSV cells with a literal apostrophe."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    else:
        value = str(value)
    if value and (value[0] in "=+-@\t\r\n" or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def _stage(result, stage):
    with (stage / "result.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    metadata = {key: value for key, value in result.items() if key != "items"}
    metadata["files"] = list(_FILES)
    with (stage / "metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    columns = list(dict.fromkeys(key for item in result["items"] for key in item))
    if not columns:
        columns = _DEFAULT_COLUMNS.get(result["tool"], ("username", "title", "entity_type", "telegram_url", "catalog_url"))
    with (stage / "result.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in result["items"]:
            writer.writerow({key: csv_cell(value) for key, value in row.items()})


def write_results(result, output):
    """Write all three outputs after success, restoring old files on a replace error."""
    output = Path(output).expanduser().absolute()
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("output must be a real directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tgden-export-", dir=output.parent) as temporary:
        temporary = Path(temporary)
        stage = temporary / "new"
        stage.mkdir()
        _stage(result, stage)
        if not output.exists():
            os.replace(stage, output)
            return output
        backup = temporary / "old"
        backup.mkdir()
        for name in _FILES:
            target = output / name
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError("Result paths must be regular files")
            if target.exists():
                shutil.copy2(target, backup / name)
        changed = []
        try:
            for name in _FILES:
                os.replace(stage / name, output / name)
                changed.append(name)
        except OSError:
            for name in reversed(changed):
                if (backup / name).exists():
                    os.replace(backup / name, output / name)
                else:
                    (output / name).unlink()
            raise
    return output
