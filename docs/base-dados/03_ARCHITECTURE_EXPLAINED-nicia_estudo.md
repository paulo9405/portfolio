# 03 — Arquitetura Explicada: do usuário ao banco

> Este documento explica a arquitetura final planejada para o deploy na AWS.
> Cada componente é explicado com o "o que é", "por que existe" e "qual problema resolve".

---

## Diagrama de fluxo

```
Usuário (navegador)
        │
        │ HTTPS (porta 443)
        ▼
   Domínio / DNS
   (Route 53 ou registrador externo)
        │
        │ aponta para o IP da EC2
        ▼
   ┌─────────────────────────────────────────┐
   │              EC2 (Ubuntu)               │
   │                                         │
   │   Nginx (porta 80/443)                  │
   │   ├── redireciona HTTP → HTTPS          │
   │   ├── serve certificado SSL             │
   │   └── proxy_pass → localhost:8000       │
   │                                         │
   │   Docker Container                      │
   │   └── Gunicorn (porta 8000)             │
   │       └── Django WSGI app               │
   │           ├── views → services → ORM   │
   │           └── WhiteNoise (opcional)     │
   └─────────────────────────────────────────┘
        │                          │
        │ TCP 5432                 │ HTTPS (S3 API)
        ▼                          ▼
   ┌──────────────┐      ┌──────────────────┐
   │  RDS          │      │       S3          │
   │  PostgreSQL   │      │  static/ media/  │
   └──────────────┘      └──────────────────┘
```

---

## Componentes — o que é cada um e por que existe

---

### EC2 (Elastic Compute Cloud)

**O que é:**
Uma máquina virtual rodando na infraestrutura AWS. É o "servidor" onde o código
executa. Você escolhe o sistema operacional (Ubuntu), o tamanho (CPU/RAM) e paga
por hora de uso.

**Por que usar:**
É o componente central: tudo roda nele (Nginx, Docker, Gunicorn, Django).
O EC2 é o ponto de entrada da aplicação e tem controle total sobre o ambiente.

**Diferença do Render/Heroku:**
PaaS como Render abstraem a infraestrutura — você não vê o servidor.
Na EC2, você acessa por SSH, instala pacotes, configura o sistema. Mais trabalho,
mais controle, mais aprendizado sobre como sistemas reais funcionam.

**Para este projeto:**
- Tipo sugerido: `t2.micro` (free tier, 1 vCPU, 1GB RAM)
- Sistema operacional: Ubuntu 22.04 LTS
- Storage: 20GB EBS (disco SSD gerenciado)

---

### Docker

**O que é:**
Uma tecnologia de containerização. Em vez de instalar Python, Django e dependências
diretamente no servidor, você empacota tudo num container isolado.

**Por que usar:**
- Paridade dev/produção: o mesmo container roda na sua máquina e na EC2
- Isolamento: o container não interfere com outros softwares no servidor
- Reprodutibilidade: `docker build` sempre produz a mesma imagem
- Já existe no projeto: o Dockerfile está pronto e testado

**Como funciona neste projeto:**
```
docker build -t nicia-track .      ← cria a imagem (inclui collectstatic)
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  nicia-track                      ← inicia o container
```

---

### Docker Compose

**O que é:**
Uma ferramenta para definir e rodar múltiplos containers como um serviço.
O arquivo `docker-compose.yml` descreve todos os serviços (web + db) e suas
dependências.

**Por que usar:**
Em desenvolvimento: um único `docker compose up` sobe o banco PostgreSQL e a
aplicação com as configurações corretas, sem instalar nada manualmente.

**Em produção AWS:**
Pode ser usado também, mas de forma mais simples — apenas o serviço `web`,
pois o banco fica no RDS (não no compose). Alternativamente, rodar `docker run`
direto também funciona para uma única instância.

---

### Nginx

**O que é:**
Um servidor web de alta performance. Atua como **proxy reverso** — fica na frente
da aplicação e direciona as requisições para ela.

**Por que não expor o Django diretamente:**
Gunicorn é um servidor WSGI — excelente para rodar código Python, mas não foi
feito para lidar diretamente com o tráfego da internet. Ele não tem:
- Rate limiting
- Compressão gzip
- Gerenciamento de TLS/HTTPS
- Cache de resposta
- Proteção contra conexões lentas (slowloris attack)

**O que Nginx faz neste projeto:**
```
Cliente → Nginx (443) → verifica certificado SSL → desencripta
        → passa requisição HTTP para Gunicorn (8000)
        → Gunicorn processa → retorna resposta
        → Nginx encripta e devolve ao cliente
```

Nginx também redireciona HTTP (80) para HTTPS (443) automaticamente.

**Nota:** WhiteNoise já serve static files via Django/Gunicorn. Em alta escala,
configuraria Nginx para servir static files diretamente (mais rápido). Para este
laboratório, WhiteNoise é suficiente.

---

### Gunicorn

**O que é:**
Green Unicorn — um servidor WSGI (Web Server Gateway Interface) para Python.
É o processo que recebe requisições HTTP do Nginx e chama o código Django.

**Por que não usar `manage.py runserver` em produção:**
O servidor de desenvolvimento do Django é single-threaded, não tem workers paralelos,
não é otimizado para performance e não deve ser exposto à internet.

**Como funciona:**
```
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120
```
- `--workers 2`: 2 processos paralelos (recomendação: 2 × CPUs + 1)
- `--timeout 120`: mata workers que não respondem em 2 min
- `--bind 0.0.0.0:8000`: aceita conexões de qualquer interface na porta 8000

---

### Django

**O que é:**
O framework web Python. Recebe a requisição do Gunicorn, processa via views e
services, consulta o banco via ORM e retorna HTML (templates).

**Stack Django deste projeto:**
```
Views (CBV) → Service Layer → Django ORM → PostgreSQL
                                         → S3 (via django-storages)
Templates (Bootstrap 5 + HTMX) ← responses
```

**Configurações-chave para produção:**
- `DEBUG = False` (sem stack traces para o usuário)
- `SECURE_SSL_REDIRECT = True` (força HTTPS)
- `SESSION_COOKIE_SECURE = True` (cookie só via HTTPS)
- `CSRF_COOKIE_SECURE = True` (CSRF só via HTTPS)
- `SECURE_PROXY_SSL_HEADER` (diz ao Django que o Nginx cuidou do SSL)

---

### PostgreSQL (via RDS)

**O que é:**
O banco de dados relacional. Armazena todos os dados: usuários, questões, respostas,
progresso de estudos, estatísticas.

**RDS (Relational Database Service):**
PostgreSQL gerenciado pela AWS. Você não instala nem configura o PostgreSQL —
a AWS cuida de:
- Instalação e patches de versão
- Backups automáticos (até 35 dias de retenção)
- Snapshots manuais
- Failover (Multi-AZ, se habilitado)
- Métricas (CPU, conexões, storage)

**Por que não rodar PostgreSQL na própria EC2:**
Você poderia rodar PostgreSQL como container Docker na EC2. Mas:
- Se a EC2 tiver problema, você perde o banco
- Gerenciar backups manualmente é trabalhoso
- RDS é mais confiável para dados persistentes
- Free tier inclui db.t3.micro com 20GB

**Conexão EC2 → RDS:**
- Via rede privada interna da AWS (não sai para a internet)
- Security Group do RDS: aceita TCP 5432 apenas do Security Group da EC2
- `sslmode=require` no Django (já configurado em production.py)

---

### S3 (Simple Storage Service)

**O que é:**
Armazenamento de objetos (arquivos) na AWS. Escalável, durável (99.999999999%),
barato por GB.

**Dois usos neste projeto:**

**1. Static files** (CSS, JS, imagens):
- Gerados por `collectstatic`
- Servidos por CloudFront (opcional) ou diretamente do S3
- Acessíveis publicamente (sem autenticação)

**2. Media files** (avatares):
- Gerados por uploads de usuários
- Podem ser públicos ou privados (via presigned URLs)
- Sobrevivem a redeploys — o container pode ser recriado sem perder os arquivos

**Integração com Django:**
```python
# requirements/production.txt
django-storages[s3]
boto3

# settings/production.py
STORAGES = {
    "default": {                             # media files
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"bucket_name": "nicia-media"},
    },
    "staticfiles": {                         # static files
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        "OPTIONS": {"bucket_name": "nicia-static"},
    },
}
```

---

### IAM (Identity and Access Management)

**O que é:**
O sistema de controle de acesso da AWS. Define quem pode fazer o quê com quais
recursos.

**Usos neste projeto:**

**IAM User para a aplicação (acesso ao S3):**
- Cria um usuário IAM com permissão mínima
- Apenas `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` nos buckets específicos
- Gera Access Key ID + Secret Access Key → variáveis de ambiente no .env

**IAM Role para a EC2 (alternativa mais segura):**
- Associa uma Role à instância EC2
- A EC2 assume a Role automaticamente (sem credenciais hardcoded)
- Preferido em produção real

**Princípio do menor privilégio:**
Nenhuma credencial deve ter mais permissões do que o necessário.
Um IAM User que só precisa de S3 não deve ter acesso ao RDS, EC2 ou billing.

---

### Security Groups

**O que é:**
Firewall virtual da AWS. Define quais conexões de entrada (inbound) e saída
(outbound) são permitidas para cada recurso (EC2, RDS).

**Security Group da EC2:**
```
Inbound:
  SSH   (22)   → apenas do seu IP (ou VPN)
  HTTP  (80)   → 0.0.0.0/0 (qualquer um)
  HTTPS (443)  → 0.0.0.0/0 (qualquer um)

Outbound:
  Tudo permitido (padrão)
```

**Security Group do RDS:**
```
Inbound:
  PostgreSQL (5432) → apenas do Security Group da EC2

Outbound:
  Nada (ou apenas respostas)
```

Isso garante que o banco **nunca** seja acessível diretamente da internet —
apenas a EC2 pode conectar a ele.

---

### Variáveis de ambiente

**O que são:**
Configurações que mudam entre ambientes (dev/staging/prod) sem alterar o código.
Armazenadas fora do repositório, injetadas no processo Django via `.env` ou
variáveis do sistema operacional.

**Variáveis necessárias para produção AWS:**
```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<chave-forte-gerada>
DEBUG=False
ALLOWED_HOSTS=<ip-ou-dominio-da-ec2>
CSRF_TRUSTED_ORIGINS=https://<dominio>

# Banco (RDS)
PGDATABASE=nicia_track
PGUSER=nicia_track
PGPASSWORD=<senha-forte>
PGHOST=<endpoint-do-rds>.rds.amazonaws.com
PGPORT=5432

# Admin
ADMIN_EMAIL=<email>
ADMIN_PASSWORD=<senha-forte>

# S3 (Fase 3)
AWS_ACCESS_KEY_ID=<chave>
AWS_SECRET_ACCESS_KEY=<segredo>
AWS_STORAGE_BUCKET_NAME=nicia-track-static
AWS_MEDIA_BUCKET_NAME=nicia-track-media

# Monitoramento (opcional)
SENTRY_DSN=<dsn-do-sentry>
```

**Como injetar na EC2:**
Opção A (simples): arquivo `.env` na EC2, não versionado.
Opção B (seguro): AWS SSM Parameter Store — parâmetros acessados em tempo de execução.
Opção C (mais seguro): AWS Secrets Manager — similar ao SSM, com rotação automática.

---

## Sequência de uma requisição HTTP

```
1. Usuário digita https://nicia-track.com no browser

2. DNS resolve o domínio → IP público da EC2

3. Nginx recebe na porta 443, valida o certificado SSL

4. Nginx desencripta a requisição e passa para Gunicorn na porta 8000
   (com header X-Forwarded-Proto: https)

5. Gunicorn recebe e chama Django WSGI

6. Django: middleware verifica sessão → URL router → view → service

7. Service consulta RDS via Django ORM (conexão TCP 5432, rede interna AWS)

8. RDS retorna os dados → ORM mapeia para objetos Python

9. View renderiza template → HTML

10. Gunicorn retorna o HTML para Nginx

11. Nginx encripta e devolve ao browser

Total: ~50-200ms (típico para uma app Django bem configurada)
```

---

## Arquitetura simplificada vs arquitetura real

Este laboratório usa a arquitetura simplificada:
- 1 EC2 (sem Auto Scaling)
- 1 RDS (sem Multi-AZ)
- 1 bucket S3

Uma aplicação de produção real poderia ter:
- Load Balancer (ALB) distribuindo entre múltiplas EC2
- Auto Scaling Group (escala automaticamente)
- RDS Multi-AZ (failover automático)
- ElastiCache Redis (cache de sessões e queries)
- CloudFront (CDN na frente do S3)

Para aprendizado, a arquitetura simplificada cobre todos os conceitos fundamentais.
