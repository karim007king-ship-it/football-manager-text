"""Mise en forme du texte arabe pour Kivy, sans dépendance externe.
ar(text) : relie les lettres arabes puis inverse l'ordre visuel (RTL)."""
import unicodedata

_FORMS = {}  # lettre de base -> {"isolated","final","initial","medial"}
_LIGA = {}   # (lam, alef-variante) -> {"isolated","final"}

for _cp in list(range(0xFE70, 0xFEFD)):
    _d = unicodedata.decomposition(chr(_cp))
    if not _d.startswith("<"):
        continue
    _parts = _d.split()
    _kind = _parts[0].strip("<>")
    _base = [chr(int(x, 16)) for x in _parts[1:]]
    if _kind not in ("isolated", "final", "initial", "medial"):
        continue
    if len(_base) == 1:
        _FORMS.setdefault(_base[0], {})[_kind] = chr(_cp)
    elif len(_base) == 2 and _base[0] == "\u0644":
        _LIGA.setdefault(tuple(_base), {})[_kind] = chr(_cp)

# Lettres qui ne se lient pas à la lettre suivante
_NO_NEXT = set("\u0627\u0622\u0623\u0625\u062F\u0630\u0631\u0632\u0648\u0629\u0621\u0624\u0649")
_TASHKEEL = set(chr(c) for c in range(0x064B, 0x0653))


def _is_ar(c):
    return c in _FORMS or c in _TASHKEEL or "\u0600" <= c <= "\u06FF"


def _shape(line):
    chars = list(line)
    out = []
    i = 0
    n = len(chars)

    def prev_joins(idx):
        j = idx - 1
        while j >= 0 and chars[j] in _TASHKEEL:
            j -= 1
        return j >= 0 and chars[j] in _FORMS and chars[j] not in _NO_NEXT

    def next_joins(idx):
        j = idx + 1
        while j < n and chars[j] in _TASHKEEL:
            j += 1
        return j < n and chars[j] in _FORMS

    while i < n:
        c = chars[i]
        if c not in _FORMS:
            out.append(c)
            i += 1
            continue
        # ligature lam + alef
        if c == "\u0644" and i + 1 < n and (c, chars[i + 1]) in _LIGA:
            lig = _LIGA[(c, chars[i + 1])]
            out.append(lig.get("final" if prev_joins(i) else "isolated", c))
            i += 2
            continue
        p = prev_joins(i)
        nx = c not in _NO_NEXT and next_joins(i)
        f = _FORMS[c]
        if p and nx:
            kind = "medial"
        elif p:
            kind = "final"
        elif nx:
            kind = "initial"
        else:
            kind = "isolated"
        out.append(f.get(kind) or f.get("isolated") or c)
        i += 1
    return out


def _is_ltr(c):
    return c.isascii() and c.isalnum()


def _visual(chars):
    """Ordre visuel simple : on inverse la ligne, mais les mots latins et
    les nombres gardent leur sens de lecture."""
    runs = []  # (is_ltr, [chars])
    for c in chars:
        l = _is_ltr(c)
        if runs and runs[-1][0] == l:
            runs[-1][1].append(c)
        elif (not l) and c in ".,:/-%" and runs and runs[-1][0]:
            runs[-1][1].append(c)   # 12,000 / 3-1 restent ensemble
        else:
            runs.append((l, [c]))
    mirror = {"(": ")", ")": "(", "[": "]", "]": "[", "<": ">", ">": "<"}
    res = []
    for l, r in reversed(runs):
        res.extend(r if l else [mirror.get(x, x) for x in reversed(r)])
    return "".join(res)


def ar(text):
    out = []
    for line in str(text).split("\n"):
        if any(_is_ar(c) for c in line):
            try:
                out.append(_visual(_shape(line)))
            except Exception:
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)
