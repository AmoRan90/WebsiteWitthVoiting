"""Минимальный движок шаблонов на основе string.Template."""

from pathlib import Path
from string import Template

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

def render(template_name: str, **context) -> str:
    path = TEMPLATES_DIR / template_name
    text = path.read_text(encoding="utf-8")
    return Template(text).substitute(**context)