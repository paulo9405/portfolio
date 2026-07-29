# 01 — Análise do Projeto: Nícia Track

> Documento gerado após leitura completa do repositório. Serve como ponto de partida
> para as decisões de deploy na AWS.

---

## O que é o projeto

**Nícia Track** é uma plataforma web de preparação para concursos públicos.
Permite que a usuária resolva questões por disciplina, faça simulados completos,
acompanhe seu desempenho e gerencie um plano de estudos personalizado.

- Banco de 800 questões reais, distribuídas em 13 disciplinas
- Simulados com distribuição proporcional por categoria (básica/específica)
- Dashboard com streak, metas diárias e pontos fracos
- Plano de estudos com capítulos, notas e reflexões guiadas
- Caderno de erros com revisão espaçada

Usuária inicial: Nícia (candidata — Concurso 003/2026, Prefeitura de Ponta Grossa/PR,
banca Instituto UniFil, cargo: Médico Veterinário).
Arquitetura: multiusuário desde o primeiro dia.

---

## Estrutura de pastas

```
aws-nicia/
├── apps/                    ← apps Django de domínio
│   ├── core/                ← BaseModel (UUID PK, timestamps), exceções
│   ├── accounts/            ← autenticação, perfil, avatar
│   ├── questions/           ← banco de questões (Subject, Topic, Question, Alternative)
│   ├── exams/               ← quizzes e simulados (Quiz, QuizQuestion, UserAnswer)
│   ├── performance/         ← estatísticas e pontos fracos
│   ├── dashboard/           ← painel principal (widgets, streak, metas)
│   └── study_plan/          ← plano de estudos, capítulos, caderno de erros
├── config/
│   ├── settings/
│   │   ├── base.py          ← settings compartilhadas
│   │   ├── development.py   ← SQLite (sem Docker) ou PostgreSQL (com Docker)
│   │   ├── production.py    ← PostgreSQL, HTTPS, logging
│   │   └── testing.py       ← SQLite :memory:, MD5 hasher
│   ├── urls.py
│   └── wsgi.py
├── templates/               ← templates globais + por app
├── static/                  ← CSS, JS, imagens de desenvolvimento
├── staticfiles/             ← gerado por collectstatic (não versionar)
├── media/                   ← uploads de usuário (avatars)
├── docs/                    ← documentação do domínio + banco de questões
├── tests/
│   ├── unit/                ← 10 arquivos, ~2.000 linhas
│   └── integration/         ← 14 arquivos, ~1.100 linhas
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── scripts/                 ← scripts utilitários (validate_parse.py)
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .env                     ← NUNCA versionar
├── render.yaml              ← blueprint de deploy original (Render.com)
├── DEPLOY.md
└── manage.py
```

---

## Apps Django

| App | Responsabilidade principal |
|---|---|
| `core` | `BaseModel` (UUID PK, `created_at`, `updated_at`), exceções de domínio |
| `accounts` | `User` (email como login), `Profile`, cadastro/login/perfil |
| `questions` | `Subject`, `Topic`, `Question`, `Alternative`; importador de questões |
| `exams` | `Quiz`, `QuizQuestion`, `UserAnswer`; lógica de treino e simulado |
| `performance` | `UserSubjectStat`, `StudySession`; analytics e pontos fracos |
| `dashboard` | painel: streak, metas, resumo de atividade recente |
| `study_plan` | `StudyModule`, `StudyChapter`, `LessonProgress`, `ErrorNotebookEntry` |

**Padrão arquitetural:** View → Service Layer → ORM (sem lógica nas views).
Todas as regras de negócio vivem em `apps/<app>/services/`.

---

## Configuração do Django

### settings/base.py
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` via `python-decouple` (`.env`)
- `AUTH_USER_MODEL = "accounts.User"` (email como USERNAME_FIELD)
- Middleware inclui `WhiteNoiseMiddleware` (static files sem servidor separado)
- `STATIC_ROOT = BASE_DIR / "staticfiles"` (destino do `collectstatic`)
- `STORAGES`: whitenoise CompressedManifest em produção, simples em dev/test
- `MEDIA_ROOT = BASE_DIR / "media"` — uploads de avatares via `FileSystemStorage`
- Localização: `pt-br`, `America/Sao_Paulo`

### settings/production.py
- PostgreSQL via variáveis `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`
- `CONN_MAX_AGE = 60` (connection pooling mínimo)
- `OPTIONS = {"sslmode": "require"}` — SSL obrigatório com o banco
- `SECURE_PROXY_SSL_HEADER` configurado para proxy reverso (X-Forwarded-Proto)
- `SECURE_SSL_REDIRECT = True`, HSTS ativado, cookies seguros
- `CSRF_TRUSTED_ORIGINS` via variável de ambiente
- Logging: WARNING+ para stdout/stderr

### settings/development.py
- Se `PGDATABASE` não está definido: usa SQLite local
- Se `PGDATABASE` está definido (ex.: via docker-compose): usa PostgreSQL

### settings/testing.py
- SQLite `:memory:` (zero I/O de disco)
- MD5 hasher (testes de senha ~100x mais rápidos)

---

## Banco de dados atual

**Desenvolvimento sem Docker:** SQLite (`db.sqlite3` na raiz).
- Arquivo de ~3MB com dados reais (questões importadas).
- `.gitignore` inclui `db.sqlite3` → não é versionado.

**Desenvolvimento com Docker:** PostgreSQL via `docker-compose.yml`.

**Produção atual (Render):** PostgreSQL gerenciado (Render managed DB).

**Para AWS:** o alvo é RDS PostgreSQL.

### Variáveis esperadas em produção
```
PGDATABASE=nicia_track
PGUSER=nicia_track
PGPASSWORD=<senha>
PGHOST=<host-do-rds>
PGPORT=5432
```

---

## Dependências (production)

```
Django==4.2.16
psycopg2-binary==2.9.9   ← driver PostgreSQL
python-decouple==3.8     ← lê variáveis do .env
Pillow==10.4.0           ← processamento de avatares
whitenoise==6.7.0        ← static files em produção
gunicorn==22.0.0         ← servidor WSGI de produção
Markdown==3.10.2         ← renderização de conteúdo
sentry-sdk==2.13.0       ← monitoramento de erros (production.txt)
```

Dependências de desenvolvimento adicionam: pytest, pytest-django, pytest-cov,
factory-boy, Faker, freezegun, black, isort.

---

## Configuração Docker

### Dockerfile
- Base: `python:3.12-slim`
- `DJANGO_SETTINGS_MODULE=config.settings.production` fixo na imagem
- Instala `libpq-dev`, `libjpeg-dev`, `zlib1g-dev` (deps de sistema)
- Cache de camadas: requirements copiados antes do código fonte
- `collectstatic` executado no build com `SECRET_KEY` dummy de build-time
- EXPOSE 8000
- CMD (runtime):
  1. `migrate --noinput`
  2. `import_study_plan`
  3. `populate_chapter_content`
  4. `import_questions docs/15_BANCO_MESTRE_DE_QUESTOES.md`
  5. `create_admin`
  6. `gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120`

> **Atenção AWS:** o CMD executa migrations e imports **a cada restart do container**.
> Todos os comandos são idempotentes, mas isso aumenta o tempo de cold start.
> Em produção com múltiplas réplicas, migrations devem rodar separadamente (ver Fase 1).

### docker-compose.yml
- Serviço `db`: postgres:16-alpine com healthcheck
- Serviço `web`: build local, instala `requirements/development.txt`, roda `runserver`
- Env do web: `DJANGO_SETTINGS_MODULE=config.settings.development`
- Volume: `.:/app` (live reload em dev)
- Porta: 8000:8000

---

## Static files

**Localização de origem:** `static/` (CSS, JS customizados) + Django admin + apps.

**Em produção:** WhiteNoise serve os arquivos comprimidos e com hash
(`CompressedManifestStaticFilesStorage`) diretamente do processo gunicorn.
`collectstatic` já é executado no build do Docker.

**Implicação AWS:** na Fase 1 (EC2 + Docker), os static files já funcionam sem S3.
Na Fase 3, a migração para S3 é necessária quando:
- Houver múltiplas instâncias EC2 (os arquivos precisam estar num lugar central)
- Quiser separar servir arquivos estáticos do processo Django (melhor performance)

---

## Media files

**Localização:** `media/avatars/` (uploads de foto de perfil).

**Backend atual:** `django.core.files.storage.FileSystemStorage` (disco local).

**Risco no Docker:** media files salvos dentro do container são **perdidos** a cada
redeploy (o container é recriado). Atualmente no Render, os avatares são efêmeros.

**Para AWS:** na Fase 3, migrar para S3 resolve este problema definitivamente.
Requer `django-storages` + `boto3` e mudança no `STORAGES` de `default`.

---

## Testes

**Framework:** pytest + pytest-django
**Configuração:** `pytest.ini` → `DJANGO_SETTINGS_MODULE = config.settings.testing`

```
tests/
├── unit/           ← testa services isoladamente (sem HTTP)
│   ├── test_user_service.py
│   ├── test_quiz_service.py
│   ├── test_parser.py
│   ├── test_performance_service.py
│   ├── test_dashboard_service.py
│   ├── test_simulated_service.py
│   ├── test_mini_quiz_service.py
│   ├── test_error_notebook_service.py
│   ├── test_plan_service.py
│   └── test_phase4_plan_service.py
└── integration/    ← testa views com banco real
    ├── test_auth_views.py
    ├── test_exam_views.py
    ├── test_dashboard_views.py
    ├── test_performance_views.py
    ├── test_study_plan_views.py
    ├── test_simulated_views.py
    ├── test_import_service.py
    ├── test_import_command.py
    ├── test_admin.py
    ├── test_quality.py
    ├── test_phase3_views.py
    └── test_phase4_views.py
```

Total: ~3.171 linhas de testes.
Banco: SQLite `:memory:` (sem PostgreSQL necessário para testes).

---

## Scripts e management commands

| Comando | O que faz |
|---|---|
| `import_questions <arquivo>` | Importa 800 questões do markdown (idempotente) |
| `import_study_plan` | Importa plano de estudos com módulos e capítulos |
| `populate_chapter_content` | Popula conteúdo dos capítulos |
| `create_admin` | Cria superusuário via `ADMIN_EMAIL` + `ADMIN_PASSWORD` |

Todos são **idempotentes**: rodar múltiplas vezes é seguro.

---

## Pontos que precisam ser adaptados para AWS

| Ponto | Situação atual | O que mudar para AWS |
|---|---|---|
| **Banco** | SQLite (dev) / Render Postgres (prod) | RDS PostgreSQL |
| **Media files** | FileSystemStorage (disco efêmero) | S3 + django-storages |
| **Static files** | WhiteNoise (já funciona) | Opcional: S3/CloudFront |
| **Env vars** | Render injetava automaticamente | AWS SSM / Secrets Manager ou `.env` na EC2 |
| **ALLOWED_HOSTS** | `.onrender.com` | IP/domínio da EC2 |
| **CSRF_TRUSTED_ORIGINS** | URL do Render | URL/domínio da EC2 |
| **SSL** | Render gerenciava | Nginx + Let's Encrypt (Fase 4) |
| **CMD do Dockerfile** | migrations no startup | Separar em `docker-compose` ou entrypoint dedicado |
| **Sentry** | Configurado em production.txt | `SENTRY_DSN` como env var opcional |
| **Gunicorn workers** | 2 workers (Render free) | Ajustar por tipo de instância EC2 |
| **Logs** | stdout/stderr (Render capturava) | CloudWatch Logs ou arquivo local |

---

## Resumo executivo

O projeto é um **monolito Django maduro** com arquitetura bem definida, Docker funcional,
testes abrangentes e separação clara entre ambientes. A migração para AWS é viável
incrementalmente: o Dockerfile já existe e funciona; os settings de produção já esperam
as variáveis de ambiente corretas. Os dois pontos de atenção principais são a persistência
de media files (precisa de S3) e a separação das migrations do startup do container
(necessário para escala horizontal).
