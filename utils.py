import re
from datetime import datetime

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "item"

def fmt_date(dt_str: str) -> str:
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M")
    except Exception:
        return dt_str
