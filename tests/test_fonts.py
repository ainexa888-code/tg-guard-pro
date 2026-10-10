from app.services.fonts import detect_fancy_fonts


def test_fancy_font_detection():
    # Mathematical Alphanumeric Fraktur / Bold / Italic / Double-struck
    fancy_text = "𝕿𝖍𝖎𝖘 𝖎𝖘 𝖆 𝖋𝖆𝖓𝖈𝖞 𝖙𝖊𝖝𝖙 𝖇𝖔𝖙"
    is_fancy, count = detect_fancy_fonts(fancy_text)
    assert is_fancy is True
    assert count > 5

    # Enclosed / Circled text: ⓣⓔⓢⓣ
    circled_text = "ⓓⓞⓜⓐⓘⓝ"
    is_fancy, count = detect_fancy_fonts(circled_text)
    assert is_fancy is True
    assert count >= 3


def test_native_scripts_not_flagged():
    # Hindi (Devanagari)
    hindi_text = "नमस्ते आप कैसे हैं? यह ग्रुप सुरक्षा के लिए है।"
    is_fancy, count = detect_fancy_fonts(hindi_text)
    assert is_fancy is False
    assert count == 0

    # Arabic
    arabic_text = "مرحبا كيف حالك هذا اختبار للغة العربية"
    is_fancy, count = detect_fancy_fonts(arabic_text)
    assert is_fancy is False
    assert count == 0

    # Bengali
    bengali_text = "নমস্কার কেমন আছেন এটি পরীক্ষার জন্য"
    is_fancy, count = detect_fancy_fonts(bengali_text)
    assert is_fancy is False
    assert count == 0

    # Tamil
    tamil_text = "வணக்கம் எப்படி இருக்கிறீர்கள்"
    is_fancy, count = detect_fancy_fonts(tamil_text)
    assert is_fancy is False
    assert count == 0

    # Standard English Latin
    normal_text = "Hello welcome to our official group!"
    is_fancy, count = detect_fancy_fonts(normal_text)
    assert is_fancy is False
    assert count == 0
