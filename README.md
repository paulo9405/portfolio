# Portfólio — Paulo Souza

Site estático bilíngue (PT/EN). Build em Python + Jinja2. Hospedado no Cloudflare Pages.

## Como rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build.py
```

O build gera `dist/` com a versão PT e `dist/en/` com a versão EN.

Para visualizar localmente (qualquer servidor HTTP simples serve):

```bash
python -m http.server 8000 --directory dist
```

Acesse `http://localhost:8000`.

## Estrutura

```
build.py          # script de build
data/
  content.json    # fonte única de verdade do conteúdo (PT e EN)
templates/
  base.html       # layout base
  index.html      # home
  caso.html       # template de caso (gerado na Fase 3)
assets/
  css/main.css
  js/main.js
  img/            # imagens por projeto
  cv/             # CV em PDF
dist/             # saída estática (Cloudflare publica isso)
docs/             # documentação de apoio — não é a saída do build
prints/           # screenshots antes de otimizar (privado)
```

## Deploy

Push na `main` publica automaticamente via Cloudflare Pages.
Output directory configurado como `dist`.
