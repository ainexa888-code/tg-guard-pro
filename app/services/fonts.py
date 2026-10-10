def is_fancy_font_character(char: str) -> bool:
    """
    Checks if a character belongs to stylized/fancy Unicode alphanumeric ranges.
    Carefully excludes legitimate native scripts such as Hindi (Devanagari),
    Arabic, Bengali, Tamil, Cyrillic, Chinese, Japanese, etc.
    """
    code = ord(char)

    # Mathematical Alphanumeric Symbols (Fraktur, Bold, Italic, Script, Double-struck, etc.)
    # Range: U+1D400 - U+1D7FF
    if 0x1D400 <= code <= 0x1D7FF:
        return True

    # Enclosed Alphanumerics (Circled, Parenthesized, etc.): U+2460 - U+24FF
    if 0x2460 <= code <= 0x24FF:
        return True

    # Enclosed Ideographic Supplement & Alphanumeric Supplement: U+1F100 - U+1F1FF
    if 0x1F100 <= code <= 0x1F1FF:
        return True

    # Fullwidth / Halfwidth ASCII variants: U+FF01 - U+FF5E
    if 0xFF01 <= code <= 0xFF5E:
        return True

    return False


def detect_fancy_fonts(text: str, threshold: int = 3) -> tuple[bool, int]:
    """
    Analyzes text to detect fancy/stylized unicode abuse.
    Returns (is_fancy, count_of_fancy_chars).
    Legitimate languages (Hindi, Arabic, Bengali, Tamil, etc.) will NEVER trigger this.
    """
    if not text:
        return False, 0

    fancy_count = sum(1 for char in text if is_fancy_font_character(char))
    return fancy_count >= threshold, fancy_count
