import re
from typing import Optional

import nh3

# Allowlist CONFIRMED by the user 2026-10-15 (docs/SECURITY.md section 6).
ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "strong", "em", "u", "span"}
ALLOWED_ATTRIBUTES = {
    "p": {"class"},
    "li": {"class"},
    "span": {"class"},
    "strong": {"class"},
    "em": {"class"},
    "u": {"class"},
}
ALLOWED_CLASSES = (
    {f"ql-indent-{n}" for n in range(1, 9)}
    | {"ql-size-small", "ql-size-large", "ql-size-huge"}
)

_TAG_RE = re.compile(r"<[^>]*>")


def _attribute_filter(tag: str, attr: str, value: str) -> Optional[str]:
    # Keep only the editor's indent and size classes; drop everything else.
    if attr != "class":
        return None
    kept = [c for c in value.split() if c in ALLOWED_CLASSES]
    return " ".join(kept) if kept else None


def clean_rich_text(value: Optional[str]) -> Optional[str]:
    """Clean admin-submitted HTML. Returns None when nothing is left to show."""
    if value is None:
        return None
    cleaned = nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_attribute_filter,
    ).strip()
    text = _TAG_RE.sub("", cleaned).replace("&nbsp;", " ").strip()
    return cleaned if text else None
