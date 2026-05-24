import re


def clean_whatsapp_text(text: str) -> str:
    """Clean AI reply text for WhatsApp delivery while preserving basic readability."""
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = re.sub(r"```+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.replace("•", "- ")
    return cleaned
