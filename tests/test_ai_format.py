from courier.composer.ai_format import LOGO_URL, build_prompt, chatgpt_url


def test_prompt_contains_text_logo_and_reference():
    p = build_prompt("Stimați proprietari,\n\nTest {{email}}")
    assert "Stimați proprietari" in p and "{{email}}" in p
    assert LOGO_URL in p and "#1f1f1f" in p and "REFERENCE EMAIL" in p


def test_url_is_encoded():
    u = chatgpt_url("a b&c")
    assert u.startswith("https://chatgpt.com/?q=") and " " not in u and "&c" not in u
