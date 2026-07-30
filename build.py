"""
build.py — gera dist/ a partir de templates/ + data/

Uso:
    python build.py

Saída:
    dist/index.html                    (PT home)
    dist/en/index.html                 (EN home)
    dist/casos/<slug>.html             (PT casos)
    dist/en/cases/<slug>.html          (EN casos)
    dist/styleguide.html               (fora do sitemap — noindex)
"""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "content.json"
CASES_DIR = ROOT / "data" / "cases"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_SRC = ROOT / "assets"
DIST = ROOT / "dist"

BASE_URL = "https://portfolio.paulodev.net"
OG_IMAGE  = f"{BASE_URL}/assets/img/og-image.png"


def load_content() -> dict:
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def load_cases() -> list[dict]:
    cases = []
    if CASES_DIR.exists():
        for path in sorted(CASES_DIR.glob("*.json")):
            with path.open(encoding="utf-8") as f:
                cases.append(json.load(f))
    return cases


def copy_assets():
    dest = DIST / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSETS_SRC, dest)


def home_ctx(lang: str, data: dict, canonical: str, hreflang_pt: str, hreflang_en: str) -> dict:
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
        "hero": data["hero"],
        "stack": data["stack"],
        "cases": data["cases"],
        "about": data["about"],
        "contact": data["contact"],
        "og_image": OG_IMAGE,
    }


def build_home(env: Environment, content: dict):
    for lang in ("pt", "en"):
        is_en = lang == "en"
        data = content[lang]
        out_dir = DIST / "en" if is_en else DIST
        out_dir.mkdir(parents=True, exist_ok=True)

        canonical = f"{BASE_URL}/en/" if is_en else f"{BASE_URL}/"
        ctx = home_ctx(lang, data, canonical, f"{BASE_URL}/", f"{BASE_URL}/en/")

        tmpl = env.get_template("index.html")
        (out_dir / "index.html").write_text(tmpl.render(**ctx), encoding="utf-8")


def build_cases(env: Environment, cases: list[dict]):
    for case_data in cases:
        pt_slug = case_data["pt"]["slug"]
        en_slug = case_data["en"]["slug"]

        for lang in ("pt", "en"):
            is_en = lang == "en"
            case = case_data[lang]
            slug = en_slug if is_en else pt_slug

            if is_en:
                out_dir = DIST / "en" / "cases"
                canonical = f"{BASE_URL}/en/cases/{slug}.html"
                hreflang_pt = f"{BASE_URL}/casos/{pt_slug}.html"
                hreflang_en = canonical
            else:
                out_dir = DIST / "casos"
                canonical = f"{BASE_URL}/casos/{slug}.html"
                hreflang_pt = canonical
                hreflang_en = f"{BASE_URL}/en/cases/{en_slug}.html"

            out_dir.mkdir(parents=True, exist_ok=True)

            ctx = {
                "lang": lang,
                "lang_code": "en" if is_en else "pt-BR",
                "meta": case["meta"],
                "canonical_url": canonical,
                "hreflang_pt": hreflang_pt,
                "hreflang_en": hreflang_en,
                "root_url": "/en/" if is_en else "/",
                "pt_url": "/",
                "en_url": "/en/",
                "case": case,
                "og_image": OG_IMAGE,
            }

            tmpl = env.get_template("caso.html")
            (out_dir / f"{slug}.html").write_text(tmpl.render(**ctx), encoding="utf-8")


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


def generate_robots():
    content = f"User-agent: *\nDisallow: /styleguide.html\nSitemap: {BASE_URL}/sitemap.xml\n"
    (DIST / "robots.txt").write_text(content, encoding="utf-8")


def generate_sitemap(cases: list[dict]):
    today = "2026-07-29"
    urls = [
        (f"{BASE_URL}/",    "1.0"),
        (f"{BASE_URL}/en/", "1.0"),
    ]
    for case_data in cases:
        pt_slug = case_data["pt"]["slug"]
        en_slug = case_data["en"]["slug"]
        urls.append((f"{BASE_URL}/casos/{pt_slug}.html",      "0.8"))
        urls.append((f"{BASE_URL}/en/cases/{en_slug}.html",   "0.8"))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority in urls:
        lines += [
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{today}</lastmod>",
            f"    <changefreq>monthly</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    content = load_content()
    cases = load_cases()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    copy_assets()
    build_home(env, content)
    build_cases(env, cases)
    build_styleguide(env)
    generate_robots()
    generate_sitemap(cases)

    pages = list(DIST.rglob("*.html"))
    print(f"Build concluído → {DIST} ({len(pages)} páginas + robots.txt + sitemap.xml)")


if __name__ == "__main__":
    main()
