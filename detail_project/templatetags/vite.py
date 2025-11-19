import json
from pathlib import Path

from django import template
from django.conf import settings

register = template.Library()

_manifest_cache = None
_manifest_mtime = None
_manifest_file = None


def _manifest_path() -> Path:
    base_path = Path(settings.BASE_DIR) / "detail_project" / "static" / "detail_project" / "dist"
    manifest = base_path / "manifest.json"
    if manifest.exists():
        return manifest
    return base_path / ".vite" / "manifest.json"


def _load_manifest():
    global _manifest_cache, _manifest_mtime, _manifest_file

    manifest_file = _manifest_path()
    try:
        mtime = manifest_file.stat().st_mtime
    except FileNotFoundError:
        _manifest_cache = {}
        _manifest_mtime = None
        _manifest_file = None
        return _manifest_cache

    if (
        _manifest_cache is None
        or _manifest_mtime != mtime
        or _manifest_file != manifest_file
    ):
        with manifest_file.open("r", encoding="utf-8") as f:
            _manifest_cache = json.load(f)
        _manifest_mtime = mtime
        _manifest_file = manifest_file

    return _manifest_cache


def _normalize_entry_path(entry: str) -> str:
    if not entry:
        return ""
    normalized = entry.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _entry_name_variants(entry: str) -> set[str]:
    normalized = _normalize_entry_path(entry)
    last_segment = normalized.rsplit("/", 1)[-1] if normalized else ""
    if last_segment.endswith(".js"):
        last_segment = last_segment[:-3]

    variants = {last_segment} if last_segment else set()
    if last_segment:
        variants.add(last_segment.replace("-", "_"))
        variants.add(last_segment.replace("_", "-"))

    return {variant for variant in variants if variant}


def _resolve_entry(entry):
    manifest = _load_manifest()
    if not manifest:
        return None

    normalized_entry = _normalize_entry_path(entry)
    base_entry = normalized_entry[:-3] if normalized_entry.endswith(".js") else normalized_entry

    candidate_chain = [
        normalized_entry,
        base_entry,
        f"{base_entry}.js" if base_entry else "",
        f"assets/{base_entry}",
        f"assets/{base_entry}.js" if base_entry else "",
        f"assets/js/{base_entry}",
        f"assets/js/{base_entry}.js" if base_entry else "",
    ]

    for candidate in dict.fromkeys(filter(None, candidate_chain)):
        if candidate in manifest:
            return manifest[candidate].get("file")

    entry_names = _entry_name_variants(entry)
    if entry_names:
        for data in manifest.values():
            manifest_name = data.get("name")
            if manifest_name and manifest_name in entry_names:
                return data.get("file")

            src_name = data.get("src")
            src_variants = _entry_name_variants(src_name) if src_name else set()
            if src_variants and (
                src_variants & entry_names
                or any(
                    src_variant.startswith(entry_name)
                    for src_variant in src_variants
                    for entry_name in entry_names
                )
            ):
                return data.get("file")

    return None


@register.simple_tag
def vite_asset(entry, fallback=None):
    """
    Returns the static path for a Vite-built asset using manifest.json.

    Usage:
        {% vite_asset 'assets/js/jadwal-kegiatan.js' as bundle_path %}
        <script src="{% static bundle_path %}"></script>
    """
    resolved = _resolve_entry(entry)
    if resolved:
        return f"detail_project/dist/{resolved}"

    if fallback:
        return fallback

    # Default fallback assumes unhashed filename
    clean_entry = entry.replace("assets/", "")
    return f"detail_project/dist/assets/{clean_entry}"
