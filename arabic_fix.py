"""Arabic shaping and bidirectional display helpers for Kivy."""
import re

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:
    arabic_reshaper = None
    get_display = None

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_RESHAPER = None


def ar(text):
    global _RESHAPER
    value = str(text)
    if arabic_reshaper is None or get_display is None:
        return value

    if _RESHAPER is None:
        _RESHAPER = arabic_reshaper.ArabicReshaper(
            configuration={
                "delete_harakat": False,
                "support_ligatures": True,
            }
        )

    lines = []
    for line in value.split("\n"):
        if not _ARABIC_RE.search(line):
            lines.append(line)
            continue
        try:
            lines.append(get_display(_RESHAPER.reshape(line), base_dir="R"))
        except Exception:
            lines.append(line)
    return "\n".join(lines)
