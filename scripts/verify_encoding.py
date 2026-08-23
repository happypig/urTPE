"""One-off check that viewer/projects.data.js is valid UTF-8 Traditional Chinese, not mojibake."""
path = "viewer/projects.data.js"
raw = open(path, "rb").read()
text = raw.decode("utf-8")  # raises UnicodeDecodeError if bytes aren't valid UTF-8
print("OK: valid UTF-8, no decode errors, length =", len(text))
print("U+FFFD (replacement char) count:", text.count(chr(0xFFFD)))

sample = "中山區"
idx = text.find(sample)
print("sample substring found at", idx, "codepoints:", [hex(ord(c)) for c in sample])


def is_expected(c):
    o = ord(c)
    if o < 128:
        return True
    ranges = [
        (0x3000, 0x303F),  # CJK punctuation
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0x3400, 0x4DBF),  # CJK Ext A
        (0xF900, 0xFAFF),  # CJK Compatibility Ideographs (source PDF font uses some of these)
        (0xFF00, 0xFFEF),  # Fullwidth forms
        (0x2000, 0x206F),  # general punctuation
        (0x3100, 0x312F),  # Bopomofo
    ]
    return any(lo <= o <= hi for lo, hi in ranges)


bad = sorted(c for c in set(text) if not is_expected(c))
print("unexpected non-ASCII/non-CJK chars:", bad[:20], "total unique:", len(bad))
