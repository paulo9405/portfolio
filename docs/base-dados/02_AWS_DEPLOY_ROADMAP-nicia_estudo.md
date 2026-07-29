# 02 — Roadmap de Deploy na AWS

> Plano incremental por fases. Cada fase entrega algo que funciona de ponta a ponta
> antes de avançar. Nenhuma fase pressupõe que a próxima está pronta.

---

## Visão geral

```
Fase 0 — Preparação do repositório e segurança
Fase 1 — Deploy inicial na EC2 com Docker
Fase 2 — Banco PostgreSQL no RDS
Fase 3 — Static e media files no S3
Fase 4 — Nginx, domínio e HTTPS
Fase 5 — Segurança, custos, logs e monitoramento
Fase 6 — Revisão final e documentação para portfólio
```

---

## Fase 0 — Preparação do repositório e segurança

### Objetivo
Garantir que o repositório está limpo, sem secrets, e pronto para ser clonado
numa instância EC2 sem expor informações sensíveis.

### O que será feito
- Auditar o `.gitignore` (`.env`, `db.sqlite3`, `media/`, `staticfiles/`)
- Confirmar que nenhum secret está versionado (`git log --all -S "PASSWORD"`)
- Criar `.env.aws` como template de variáveis para a AWS (sem valores reais)
- Decidir como injetar variáveis na EC2 (opções: arquivo `.env` manual, AWS SSM
  Parameter Store, ou AWS Secrets Manager)
- Documentar o processo de geração de `SECRET_KEY`
- Fazer push do branch `aws-lab` para ter histórico separado do projeto original

### Por que será feito
Subir com um `.env` hardcoded ou `DEBUG=True` em produção é uma vulnerabilidade séria.
Estabelecer boas práticas de segurança antes de qualquer infraestrutura evita retrabalho.

### Arquivos provavelmente alterados
- `.gitignore` (verificar, não deve mudar)
- `README_AWS.md` (novo — explicar o propósito deste repositório)
- `docs/aws_deploy/` (criação desta documentação)

### Riscos
- Secrets acidentalmente comitados no passado (verificar com `git log`)
- Confundir o `.env` local com o `.env` de produção

### Critério de conclusão
- `git status` e `git log` não mostram nenhuma linha com senha ou secret key real
- `.env.example` está completo com todas as variáveis necessárias para AWS
- README_AWS.md existe na raiz

### O que estudar depois
- AWS IAM (usuários, roles, policies)
- AWS SSM Parameter Store vs Secrets Manager
- `git secret` e `git-crypt` para gerenciar secrets em repositórios

---

## Fase 1 — Deploy inicial na EC2 com Docker

### Objetivo
Colocar a aplicação rodando numa instância EC2 usando Docker, acessível via HTTP
(sem HTTPS ainda). Banco ainda é SQLite ou o mesmo container para simplificar
a validação inicial.

### O que será feito
1. Criar instância EC2 (Ubuntu 22.04 LTS, t2.micro no free tier)
2. Configurar Security Group: portas 22 (SSH), 80 (HTTP), 443 (HTTPS futuro)
3. Instalar Docker e Docker Compose na EC2
4. Clonar o repositório na EC2
5. Criar `.env` na EC2 com as variáveis de produção
6. Build e run do Docker container
7. Verificar que gunicorn sobe na porta 8000
8. Testar acesso via IP público da EC2

### Por que será feito
Validar que o Dockerfile funciona num ambiente Linux real antes de adicionar
complexidade (RDS, S3, Nginx). É o caminho mais rápido para "funciona em produção".

### Arquivos provavelmente alterados
- `Dockerfile` (possível ajuste no CMD para separar migrations do gunicorn)
- `docker-compose.yml` (possível versão `production.yml` para EC2)

### Riscos
- CMD do Dockerfile roda migrations + imports a cada restart → lento
- `ALLOWED_HOSTS` incorreto → Django retorna 400
- `DEBUG=True` acidentalmente → nunca em produção
- Porta 8000 acessível diretamente (sem Nginx ainda) → OK para validação, não para produção

### Critério de conclusão
- `curl http://<IP-EC2>:8000/conta/login/` retorna HTTP 200
- Login com admin funciona
- Questões aparecem no banco

### O que estudar depois
- EC2 instance types e quando usar cada um
- AMIs (Amazon Machine Images)
- Key Pairs (SSH) e como gerenciar acesso seguro
- Elastic IP vs IP público temporário
- Docker build cache e estratégias de otimização

---

## Fase 2 — Banco PostgreSQL no RDS

### Objetivo
Substituir o banco de dados por um RDS PostgreSQL gerenciado, eliminando a dependência
de SQLite e garantindo persistência, backups automáticos e escalabilidade.

### O que será feito
1. Criar instância RDS PostgreSQL (db.t3.micro, free tier)
2. Configurar Security Group do RDS: aceita apenas conexões da EC2 (porta 5432)
3. Criar banco `nicia_track` e usuário com as permissões corretas
4. Atualizar as variáveis `PG*` no `.env` da EC2 apontando para o RDS
5. Rodar `migrate` contra o RDS
6. Rodar os management commands de importação de dados
7. Testar a aplicação completa com o novo banco

### Por que será feito
SQLite não é adequado para produção (sem concorrência, arquivo local = perde dados
no redeploy). RDS oferece backups automáticos, snapshots, Multi-AZ e métricas nativas
— é o padrão AWS para banco relacional.

### Arquivos provavelmente alterados
- `.env` na EC2 (apenas variáveis, não o arquivo no repositório)
- Nenhum arquivo de código deve mudar — os settings já esperam variáveis `PG*`

### Riscos
- Security Group mal configurado → EC2 não consegue conectar ao RDS
- `sslmode=require` no production.py → RDS deve ter SSL habilitado (padrão)
- Custo: RDS cobra por hora mesmo parado (diferente de EC2) → lembrar de deletar
- First migrate no RDS pode demorar alguns minutos

### Critério de conclusão
- `python manage.py dbshell` na EC2 conecta ao RDS sem erro
- `python manage.py migrate` roda com sucesso
- Aplicação funciona com dados no RDS
- Login, questões e dashboard funcionam

### O que estudar depois
- RDS Multi-AZ vs Single-AZ
- RDS Read Replicas
- Connection pooling (PgBouncer, RDS Proxy)
- RDS Automated Backups e Point-in-time Recovery
- Custo por hora do RDS vs custo de gerenciar PostgreSQL em EC2

---

## Fase 3 — Static e media files no S3

### Objetivo
Mover os static files e os media files (avatares) para S3, eliminando a dependência
do disco da EC2 e permitindo escala horizontal no futuro.

### O que será feito
1. Criar bucket S3 para static files (`nicia-track-static`)
2. Criar bucket S3 para media files (`nicia-track-media`) ou usar o mesmo com prefixos
3. Configurar políticas de acesso (public para static, privado para media via URLs pré-assinadas)
4. Instalar `django-storages` e `boto3` no projeto
5. Configurar `STORAGES` no `settings/production.py` para usar S3
6. Criar IAM User com permissão mínima (read/write apenas nos buckets necessários)
7. Adicionar `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`
   nas variáveis de ambiente da EC2
8. Rodar `collectstatic` → arquivos vão para S3
9. Testar upload de avatar → arquivo vai para S3
10. Verificar que static files carregam corretamente no browser

### Por que será feito
Media files no disco do container são perdidos a cada redeploy. Static files em S3
permitem múltiplas instâncias EC2 servindo os mesmos arquivos. S3 é mais barato e
mais confiável do que disco de VM para arquivos estáticos.

### Arquivos provavelmente alterados
- `requirements/production.txt` (adicionar `django-storages`, `boto3`)
- `config/settings/production.py` (mudar `STORAGES`)
- `.env` na EC2 (adicionar variáveis AWS)

### Riscos
- Bucket público acidental → expõe dados de usuário
- CORS mal configurado → browser bloqueia carregamento de assets
- IAM com permissões amplas demais (princípio de menor privilégio violado)
- Custo: S3 cobra por armazenamento + requests (muito baixo para este volume)
- `collectstatic` pode sobrescrever arquivos de produção se rodado localmente

### Critério de conclusão
- CSS e JS carregam de URLs `https://s3.amazonaws.com/...`
- Upload de avatar salva no S3 e aparece na página de perfil
- Nenhum arquivo estático está sendo servido pelo processo gunicorn

### O que estudar depois
- S3 Storage Classes (Standard, IA, Glacier)
- S3 Lifecycle Policies
- CloudFront (CDN na frente do S3)
- S3 Presigned URLs para acesso temporário a arquivos privados
- IAM Roles vs IAM Users para acesso EC2→S3

---

## Fase 4 — Nginx, domínio e HTTPS

### Objetivo
Colocar Nginx como proxy reverso na frente do Gunicorn, configurar um domínio
real e habilitar HTTPS com certificado SSL.

### O que será feito
1. Instalar Nginx na EC2 (ou rodar como container)
2. Configurar Nginx como proxy reverso: porta 80 → gunicorn:8000
3. Registrar ou apontar um domínio para o IP da EC2 (registro A)
4. Gerar certificado SSL com Let's Encrypt (Certbot)
5. Configurar Nginx para HTTPS (porta 443) e redirecionar HTTP → HTTPS
6. Atualizar `ALLOWED_HOSTS` com o domínio real
7. Atualizar `CSRF_TRUSTED_ORIGINS` com `https://seu-dominio.com`
8. Testar HTTPS completo

### Por que será feito
Gunicorn não deve ser exposto diretamente à internet: não é feito para isso (sem
rate limiting, sem compressão, sem TLS). Nginx é o ponto de entrada correto.
HTTPS é obrigatório em produção — sem ele, senhas trafegam em texto puro.

### Arquivos provavelmente alterados
- `/etc/nginx/sites-available/nicia-track` (arquivo de config Nginx na EC2)
- `.env` na EC2 (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`)
- Nenhum arquivo Python deve mudar (production.py já tem SECURE_PROXY_SSL_HEADER)

### Riscos
- `CSRF_TRUSTED_ORIGINS` incorreto → formulários retornam 403
- Certificado Let's Encrypt expira em 90 dias → configurar renovação automática
- `ALLOWED_HOSTS` não incluindo o domínio → Django retorna 400
- Redirect infinito se `SECURE_PROXY_SSL_HEADER` não estiver configurado
  (já está em production.py — mas verificar)

### Critério de conclusão
- `https://seu-dominio.com` abre a aplicação com cadeado verde
- HTTP redireciona automaticamente para HTTPS
- Formulários funcionam (sem erro 403)
- `curl -I https://seu-dominio.com` mostra `Strict-Transport-Security`

### O que estudar depois
- Nginx configuration (server blocks, upstream, proxy_pass)
- Let's Encrypt e Certbot
- AWS Certificate Manager (ACM) como alternativa ao Let's Encrypt
- AWS Route 53 para gerenciamento de DNS
- Application Load Balancer (ALB) como alternativa ao Nginx na EC2

---

## Fase 5 — Segurança, custos, logs e monitoramento

### Objetivo
Revisar e fortalecer a postura de segurança, configurar alertas de custo,
habilitar logs centralizados e estabelecer visibilidade do sistema em produção.

### O que será feito
**Segurança:**
- Revisar Security Groups (portas abertas ao mínimo necessário)
- Desativar acesso SSH por senha (apenas key pair)
- Verificar que `DEBUG=False` e `SECRET_KEY` é forte e única
- Configurar `fail2ban` para bloquear brute force SSH
- Revisar IAM (nenhuma credencial com `AdministratorAccess`)

**Custos:**
- Criar billing alert no AWS (ex.: alerta em USD 10)
- Habilitar AWS Cost Explorer
- Documentar como parar/deletar recursos sem perder dados

**Logs:**
- Configurar gunicorn para logar em arquivo ou stdout com formato estruturado
- Configurar Nginx para logar acessos
- Avaliar AWS CloudWatch Logs Agent para centralizar logs da EC2

**Monitoramento:**
- Habilitar CloudWatch métricas básicas da EC2 (CPU, disk, network)
- Configurar alarme de CPU alta
- Testar `SENTRY_DSN` (já presente no production.txt)

### Por que será feito
Uma aplicação em produção sem visibilidade é operada no escuro. Custos sem controle
podem surpreender. Segurança sem revisão cria brechas.

### Arquivos provavelmente alterados
- `.env` na EC2 (adicionar `SENTRY_DSN`)
- Configurações de sistema da EC2 (não no repositório)

### Riscos
- Billing alert não configurado → surpresa na fatura
- Logs sem rotação → disco da EC2 cheio
- CloudWatch Agent mal configurado → métricas não aparecem

### Critério de conclusão
- Billing alert ativo no AWS
- Logs de acesso Nginx acessíveis
- Sentry recebendo erros de teste
- Todas as portas desnecessárias fechadas no Security Group

### O que estudar depois
- AWS CloudWatch Logs Insights
- AWS GuardDuty
- AWS Config para compliance
- VPC (Virtual Private Cloud) e subnets privadas
- AWS WAF (Web Application Firewall)

---

## Fase 6 — Revisão final e documentação para portfólio

### Objetivo
Consolidar o laboratório como material de portfólio e referência para entrevistas.
Não adicionar funcionalidades — apenas documentar, limpar e organizar.

### O que será feito
- Atualizar `10_IMPLEMENTATION_LOG.md` com todas as decisões tomadas
- Fazer screenshots das telas AWS (EC2, RDS, S3, CloudWatch)
- Escrever um README_AWS.md completo com arquitetura final
- Gravar (opcional) um walkthrough em vídeo do deploy
- Preparar respostas para as perguntas do `09_INTERVIEW_STUDY_GUIDE.md`
- Testar um "destroy and rebuild" completo para validar que o processo é reproduzível

### Por que será feito
O valor do laboratório está na capacidade de **explicar cada decisão** numa entrevista.
Documentação viva durante a implementação é mais fiel do que escrever tudo depois.

### Arquivos provavelmente alterados
- `10_IMPLEMENTATION_LOG.md`
- `README_AWS.md`
- Arquivos de documentação em `docs/aws_deploy/`

### Critério de conclusão
- Outro desenvolvedor consegue replicar o deploy seguindo apenas este repositório
- Você consegue responder todas as perguntas do `09_INTERVIEW_STUDY_GUIDE.md`

---

## Resumo das fases

| Fase | Entregável | Pré-requisito |
|---|---|---|
| 0 | Repositório limpo e documentado | — |
| 1 | App rodando em EC2 via Docker | Fase 0 |
| 2 | Banco no RDS | Fase 1 |
| 3 | Static/media no S3 | Fase 2 |
| 4 | HTTPS com domínio próprio | Fase 3 |
| 5 | Segurança, custos, logs | Fase 4 |
| 6 | Portfólio e entrevista | Fase 5 |
