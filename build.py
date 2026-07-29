"""
build.py — gera dist/ a partir de templates/ + data/content.json

Uso:
    python build.py

Saída:
    dist/index.html          (PT)
    dist/en/index.html       (EN)
    dist/styleguide.html     (fora do sitemap — noindex)
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

BASE_URL = "https://portfolio.paulodev.net"


def load_content() -> dict:
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def copy_assets():
    dest = DIST / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSETS_SRC, dest)


def base_ctx(lang: str, data: dict, canonical: str, hreflang_pt: str, hreflang_en: str) -> dict:
    is_en = lang == "en"
    return {
        "lang": lang,
        "lang_code": "en" if is_en else "pt-BR",
        "meta": data["meta"],
        "canonical_url": canonical,
        "hreflang_pt": hreflang_pt,
        "hreflang_en": hreflang_en,
        "root_url": "/en/" if is_en else "/",
        "pt_url": "/",
        "en_url": "/en/",
        # content sections
        "hero": data["hero"],
        "stack": data["stack"],
        "cases": data["cases"],
        "about": data["about"],
        "contact": data["contact"],
    }


def build_lang(env: Environment, content: dict, lang: str):
    is_en = lang == "en"
    data = content[lang]
    out_dir = DIST / "en" if is_en else DIST
    out_dir.mkdir(parents=True, exist_ok=True)

    canonical = f"{BASE_URL}/en/" if is_en else f"{BASE_URL}/"
    ctx = base_ctx(lang, data, canonical, f"{BASE_URL}/", f"{BASE_URL}/en/")

    tmpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(tmpl.render(**ctx), encoding="utf-8")


def build_styleguide(env: Environment):
    ctx = {
        "lang": "pt",
        "lang_code": "pt-BR",
        "meta": {
            "title": "Styleguide — Paulo Souza Portfolio",
            "description": "Componentes do design system. Não indexado.",
        },
        "canonical_url": f"{BASE_URL}/styleguide.html",
        "hreflang_pt": f"{BASE_URL}/styleguide.html",
        "hreflang_en": f"{BASE_URL}/styleguide.html",
        "root_url": "/",
        "pt_url": "/",
        "en_url": "/en/",
        "is_styleguide": True,
    }
    tmpl = env.get_template("styleguide.html")
    (DIST / "styleguide.html").write_text(tmpl.render(**ctx), encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    content = load_content()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    copy_assets()
    build_lang(env, content, "pt")
    build_lang(env, content, "en")
    build_styleguide(env)

    pages = list(DIST.rglob("*.html"))
    print(f"Build concluído → {DIST} ({len(pages)} páginas)")


if __name__ == "__main__":
    main()
