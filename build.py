"""
build.py — gera dist/ a partir de templates/ + data/content.json

Uso:
    python build.py

Saída: dist/ (PT) e dist/en/ (EN)
"""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "content.json"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_SRC = ROOT / "assets"
DIST = ROOT / "dist"


def load_content() -> dict:
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def copy_assets():
    dest = DIST / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSETS_SRC, dest)


def build_lang(env: Environment, content: dict, lang: str):
    data = content[lang]
    is_en = lang == "en"
    out_dir = DIST / "en" if is_en else DIST

    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = {
        "lang": lang,
        "meta": data["meta"],
        "root_url": "/en/" if is_en else "/",
        "assets_root": "../../" if is_en else "",
        "pt_url": "/",
        "en_url": "/en/",
    }

    tmpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(tmpl.render(**ctx), encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    content = load_content()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    copy_assets()
    build_lang(env, content, "pt")
    build_lang(env, content, "en")

    print(f"Build concluído → {DIST}")


if __name__ == "__main__":
    main()
