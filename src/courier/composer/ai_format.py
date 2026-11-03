"""Build a ChatGPT prompt that turns plain text into an HTML email in the house style."""

from __future__ import annotations

from importlib.resources import files
from urllib.parse import quote

CHATGPT_URL = "https://chatgpt.com/"
LOGO_URL = "https://sudic.md/images/logo.png"


def style_reference() -> str:
    return files("courier.composer").joinpath("style_reference.html").read_text(encoding="utf-8")


def build_prompt(plain_text: str) -> str:
    return f"""Convert the email text below into a complete HTML email that copies the REFERENCE EMAIL's design exactly.

Rules:
1. Reuse the reference structure and every inline style unchanged: outer #f5f5f5 table with 40px padding, 600px white card with 12px radius and shadow, dark #1f1f1f header, body cell with padding 30px 40px, color #333333, 16px Arial, line-height 1.6, and the #fafafa footer with "© SUDIC. Toate drepturile rezervate."
2. The header must contain exactly this logo tag, unchanged:
<img src="{LOGO_URL}" alt="SUDIC" width="169" height="56" border="0" style="display:block; width:169px; height:56px; max-width:169px; border:0; outline:none; text-decoration:none; margin:0 auto;" />
3. Keep the text's language, wording, and diacritics exactly as written. Do not translate, rewrite, add, or drop content. Only fix obvious typos.
4. Put each paragraph in <p style="margin:0 0 20px;">. Bold the key facts (names, dates, companies, places, "documentul anexat" style calls to action) with <strong>, like the reference does.
5. Format the greeting as the first paragraph and the sign-off block like the reference: <p style="margin:30px 0 0;"> with <br /> line breaks and the sender name in <strong>.
6. Set <html lang> to the text's language and <title> to a short subject taken from the text.
7. Email-safe only: tables and inline styles, no <style> blocks, classes, scripts, external CSS, web fonts, or em dashes. Keep any {{{{email}}}} merge fields exactly as written.
8. Reply with ONLY the full HTML document in one code block, with no explanation.

EMAIL TEXT:
\"\"\"
{plain_text.strip()}
\"\"\"

REFERENCE EMAIL (copy this design):
{style_reference()}
"""


def chatgpt_url(plain_text: str) -> str:
    return f"{CHATGPT_URL}?q={quote(build_prompt(plain_text), safe='')}"
