# PORTFOLIO_BRIEF.md

> Documento-fonte para construção do portfólio de **Paulo Souza** — Desenvolvedor Backend/Full Stack Python.
> Este arquivo é a especificação. O Claude Code deve tratá-lo como contrato: conteúdo, estrutura e
> restrições saem daqui. Onde houver dúvida, perguntar antes de inventar.

---

## 0. Objetivo e público

**Objetivo:** provar, em menos de 60 segundos, que Paulo constrói e **opera** software real em produção —
não que ele conhece muitas tecnologias.

**Dois públicos, duas profundidades:**

| Público | Onde lê | Tempo | O que precisa extrair |
|---|---|---|---|
| Recrutador / RH | Home | 30–60s | Quem é, stack, prova de que já entregou, como contatar |
| Tech lead / CTO | Páginas de caso | 5–10 min | Decisões técnicas justificadas, problemas de produção reais, trade-offs |

**Regra de ouro:** se um elemento não serve a um desses dois públicos, ele sai.

---

## 1. Identidade

- **Nome:** Paulo Souza
- **Posicionamento:** Desenvolvedor Backend Python (Django/DRF) que leva sistema do problema à produção sozinho
- **Localização:** Buritizeiro – MG · Disponível para presencial, híbrido ou remoto · Aberto a realocação
- **E-mail:** paulorgs.dev@gmail.com
- **Telefone:** (38) 9 9136-7737
- **Idiomas:** Português nativo · Inglês avançado (4 anos morando e trabalhando na Irlanda)
- **Formação:** Análise e Desenvolvimento de Sistemas (Tecnólogo, 2020–2022) · Ciência da Computação (BSc, cursado parcialmente, Irlanda, 2024–2026)
- **Experiência anterior:** Supervisor Operacional — Spar (Irlanda), Set/2022 – Fev/2026

**Linha de posicionamento sugerida para o hero (ajustar tom, não o conteúdo):**
> Construí e mantenho sozinho três sistemas em produção — incluindo um SaaS multi-tenant com cliente pagante.
> Da modelagem de dados ao deploy, com testes, CI/CD e infraestrutura na AWS.

---

## 1.1 Irlanda, 2022–2026 — seção obrigatória do site

Quatro anos morando na Irlanda. **Não tratar como emprego anterior genérico nem como item de
currículo.** É contexto que sustenta três coisas, e uma delas é a tese central do "Sobre".

**O que aconteceu lá**
- **Supervisor Operacional na Spar** (rede de conveniência) — Set/2022 a Fev/2026, sendo
  ~3 anos na função de supervisão: liderança e treinamento de equipe, controle operacional e
  responsabilidade financeira da loja, tudo em ambiente de língua inglesa.
- **Inglês avançado adquirido em imersão**, trabalhando e estudando em inglês — não em curso.
- **BSc em Ciência da Computação**, 2024–2026: dois dos três anos cursados. Faltou um ano para
  concluir. Declarar exatamente assim, sem eufemismo. Formação incompleta declarada com
  clareza gera confiança; formação incompleta disfarçada gera desconfiança.

**A ponte narrativa — é isto que precisa aparecer no site**

Os três sistemas dele são de gestão operacional e financeira: barbearia, açaiteria, loja.
Caixa, estoque, comissão, fechamento diário, relatório de venda por produto e horário de pico.
São exatamente os problemas que ele resolvia como supervisor de loja, no papel e na planilha,
durante três anos.

> Ele não escolheu construir sistemas de gestão por acaso. Ele já foi o usuário desse tipo de
> sistema — e sabe onde dói.

Isso explica por que o Barber tem conciliação por forma de pagamento e comissão por barbeiro em
vez de só um CRUD de agendamento. E por que a métrica que ele destaca no açaí é o tempo de
fechamento de caixa, não a quantidade de telas.

**Como escrever essa seção (evitar dois erros)**
- ❌ "Trabalhei em uma loja de conveniência na Irlanda." — some o que importa.
- ❌ Inflar como se fosse experiência em tecnologia. Não era, e o entrevistador percebe.
- ✅ Enquadrar como *domínio de negócio + liderança + inglês real*, ligando explicitamente ao
  tipo de software que ele constrói hoje.

**Onde entra:** seção "Sobre" da home, com peso próprio — não uma linha perdida.
Nas páginas de caso do Barber e do Açaí, uma frase curta pode referenciar essa origem.

---

## 2. Stack a exibir

Organizar em quatro blocos (essa é a agrupação que faz sentido para quem lê):

- **Linguagens & Frameworks:** Python, Django, Django REST Framework, FastAPI, JavaScript, HTML, CSS, Bootstrap
- **Banco de Dados:** PostgreSQL, SQL, SQLite, Neon
- **Infra & DevOps:** AWS (EC2, RDS, S3, IAM, Security Groups), Docker, Linux, Nginx, Gunicorn, Cloudflare, Git, GitHub Actions, pytest, Ruff, rclone
- **Conceitos:** APIs REST, Autenticação JWT, SaaS Multi-Tenant, PWA, RAG / Embeddings, CI/CD, Web Scraping assíncrono

Não inventar tecnologia fora desta lista. Não inflar nível de proficiência com barrinhas de porcentagem
(recrutador técnico desconfia; "Python 90%" não significa nada).

---

## 3. Os quatro casos

Cada projeto tem uma página própria. A ordem abaixo é a ordem de exibição.

### 3.1 Barber Cashflow — SaaS multi-tenant para barbearias

- **Status:** Em produção · 2025 – Atual · 1 cliente pagante
- **Papel:** Produto próprio. Desenvolvido, implantado e mantido integralmente por Paulo.
- **Stack:** Django, Django REST Framework, JWT, PostgreSQL, Docker, Nginx, Cloudflare, PWA, OpenAI Embeddings + FAISS
- **Prova externa:** vídeo de demonstração — https://www.youtube.com/watch?v=r9bsFbj2NdE

**Números-chave — atualizados em 29/07/2026 (usar o fraseado exato abaixo — ver §7):**
- **+R$ 245 mil em volume transacionado pelo sistema**, entre 25/11/2025 e 29/07/2026 (~8 meses)
- **~7.000 vendas registradas** no mesmo período
- 5 barbeiros operando diariamente
- +4.000 linhas de testes automatizados (pytest)

Recorte por forma de pagamento no período (usar se quiser sustentar a conciliação financeira):
PIX R$ 143.335 · Cartão R$ 72.210 · Dinheiro R$ 30.150.

> Confirmar o total de vendas com um `count()` no banco antes de publicar — o ID do último
> registro é auto-increment e pode ter buracos.
>
> **Estes números são vivos.** O sistema está em operação e eles crescem. Ao atualizar, alterar
> nos dois idiomas (§6.1) e no CV, e sempre com a data de referência junto — número sem data
> envelhece e vira passivo.

**Sensibilidade dos dados — vale para qualquer print deste projeto:**
Nenhuma imagem pode expor nome real da barbearia, URL do sistema, usuário logado ou **ganho de
comissão individual por barbeiro**. Volume agregado do negócio é publicável; remuneração
nominal de funcionário de um cliente, não. Substituir nomes por fictícios plausíveis e manter
a URL fora do enquadramento.

**Contexto e problema:**
Nasceu de um problema concreto de uma barbearia real — agendamentos, vendas, comissões e caixa
controlados de forma manual e dispersa. No meio do desenvolvimento veio a virada de produto: a arquitetura
comportava mais de uma barbearia, e o sistema virou SaaS. Essa decisão trouxe, de uma vez, isolamento de
dados, risco de LGPD e a necessidade de subir atualizações sem quebrar a operação de um cliente que já
usava o sistema todo dia.

**Decisões técnicas (blocos de caso — problema → alternativas → escolha → resultado):**

1. **Multi-tenancy: shared database com `tenant_id` + isolamento na aplicação**
   Alternativas descartadas: banco por tenant (custo e complexidade operacional), schema por tenant
   (migrations multiplicadas). Escolha: base compartilhada com filtro obrigatório por tenant,
   resolvido via middleware. Resultado: múltiplas barbearias na mesma instância sem vazamento entre elas.

2. **Testes de isolamento como prova, não como confiança**
   Suíte que tenta ativamente acessar dados de outro tenant e verifica que o acesso falha.
   Sutileza de segurança implementada: retorna **404, não 403** — 403 confirmaria que o recurso existe.

3. **`transaction.atomic` no cancelamento de venda**
   Cancelar uma venda toca estoque, comissão e caixa. Sem transação, uma falha no meio deixaria
   o financeiro inconsistente. Resultado: ou tudo é revertido, ou nada é.

4. **Soft delete para preservar histórico financeiro**
   O usuário "cancela" um registro sem que o histórico contábil desapareça.

5. **RAG completo para o assistente interno**
   Chunking semântico, embeddings (OpenAI `text-embedding-3-small`) e busca vetorial com FAISS —
   não keyword search disfarçada de IA. O usuário pergunta sobre o sistema em linguagem natural
   em vez de ler manual.

**Problema real de produção — N+1 na listagem de vendas:**
Cada venda referencia barbeiro, agendamento, cliente, serviços e produtos. Listar 20 vendas disparava
cerca de **61 queries** (1 + 20 + 20 + 20). Diagnóstico com inspeção das queries, correção com
`select_related` nas foreign keys (vira JOIN) e `prefetch_related` nas relações múltiplas.

**Aprendizado a destacar:**
> "Foi nesse momento que deixei de enxergar o software apenas como código e passei a enxergá-lo como um
> produto que precisa continuar funcionando enquanto evolui."

---

### 3.2 Sistema de Gestão para Delivery de Açaí

- **Status:** Em produção, uso diário por funcionários · 2026 – Atual
- **Papel:** Desenvolvido integralmente por Paulo, para um estabelecimento real da família.
- **Stack:** Django, PostgreSQL (Neon), Render, GitHub Actions, Ruff, pytest, rclone, Google Drive API

**Números-chave:**
- Fechamento de caixa diário reduzido de **~1 hora para ~10 minutos**
- ~296 testes automatizados rodando contra PostgreSQL real na CI
- Gate de cobertura de 80% — build falha abaixo disso
- Primeira semana do módulo de pedidos: +115 pedidos e +R$4,6 mil registrados

**Contexto e problema:**
Operação real, com usuária de baixa familiaridade técnica. Uma regressão em produção não é um bug
abstrato — atrapalha o dia da loja. Havia boa munição (testes + backup), mas **nenhuma trava** entre
o `git push` e a produção.

**Decisões técnicas:**

1. **Pipeline de CI/CD com trava de deploy**
   Antes: `git push` disparava deploy direto no Render, sem rodar nada.
   Depois: push/PR → GitHub Actions → Ruff (lint) → pytest contra Postgres real → coverage gate 80% →
   só com CI verde o job de deploy chama o Deploy Hook do Render. Branch protection na `main` fecha o
   push direto. **Regra central: deploy só acontece depois de CI verde.**

2. **Postgres real na CI, não SQLite**
   Service container de PostgreSQL no runner, espelhando produção — evita bugs de tipo, migration e
   SQL específico que só apareceriam em produção.

3. **Backup diário automatizado, independente da aplicação**
   O roadmap original (herdado do Nícia Track) assumia cron + rclone num servidor sempre ligado.
   Essa arquitetura não existia aqui: Render free hiberna, tem filesystem efêmero e não oferece cron.
   Decisão: rodar o backup como **workflow agendado no GitHub Actions** —
   `pg_dump` (endpoint direto do Neon, sem pooler) → `gzip` → validação de tamanho → `rclone` para o
   Google Drive → validação do upload → rotação mantendo os 15 mais recentes. Nada persiste no runner.
   Validado em produção em 17/07/2026.

4. **Arquitetura em camadas documentada (`PROJECT_RULES.md`)**
   Views não contêm regra de negócio. Fluxo: View → Service (escrita) / Selector (leitura) → Model.
   Convenções de nomeação, paginação obrigatória, índices e regras de segurança escritas antes do código.

---

### 3.3 Nícia Track — Plataforma de estudos + infraestrutura AWS

- **Status:** Em produção, uso diário por usuária ativa · 2026 – Atual
- **Papel:** Produto próprio, construído para uma usuária real, e usado como laboratório de infraestrutura.
- **Stack:** Django, PostgreSQL, Docker, Gunicorn, Nginx, AWS (EC2, RDS, S3, IAM), Cloudflare

**Números-chave:**
- 800 questões reais distribuídas em 13 disciplinas
- ~3.171 linhas de testes (unitários + integração)
- Migração completa Render → AWS, validada em produção

**Contexto e problema:**
O produto começou pelo **domínio**, não pelo código: pesquisa do edital, curadoria do material e
organização por matéria antes de qualquer linha escrita. Features desenhadas para o comportamento de quem
estuda — streak e metas diárias, simulados com distribuição proporcional fiel à prova, caderno de erros
com revisão espaçada.

**Decisões técnicas:**

1. **Arquitetura em camadas desde o dia um**
   View → Service Layer → ORM. Nenhuma regra de negócio em view. `BaseModel` com UUID como chave
   primária e timestamps. Settings separados por ambiente (base / development / production / testing),
   com `testing` usando SQLite em memória e MD5 hasher — testes ~100x mais rápidos.

2. **Deploy AWS montado peça por peça, em fases**
   Preparação e auditoria de secrets → EC2 com Docker → RDS PostgreSQL → S3 para static e media →
   Nginx com HTTPS → segurança, custos e monitoramento. Cada fase entregando algo funcionando
   de ponta a ponta antes da seguinte.

3. **Security Group do RDS aceita conexão apenas do Security Group da EC2**
   O banco nunca é acessível pela internet. `sslmode=require` no Django.

4. **Media files migrados para S3**
   Avatares salvos no disco do container eram perdidos a cada redeploy. S3 + `django-storages`
   resolve de forma definitiva e libera escala horizontal.

5. **Migrations separadas do startup do container**
   O `CMD` original rodava migrations e imports a cada restart. Idempotente, mas custoso em cold start
   e incompatível com múltiplas réplicas.

**Ângulo a vender:** este é o caso onde ele explica a requisição inteira, do DNS ao banco.
Vale um diagrama de arquitetura na página.

---

### 3.4 Serviço de Automação e Web Scraping Assíncrono

> **Restrição:** este projeto foi um desafio técnico. **Não citar o nome da empresa em nenhum lugar**
> (nem no texto, nem em URLs, nem em nomes de arquivo, nem em metadados). Descrever como
> "serviço de automação construído como desafio técnico". O portal consultado é público
> (Portal da Transparência) e pode ser mencionado.

- **Status:** Concluído e implantado em EC2
- **Stack:** FastAPI, Playwright (async), Pydantic, Docker, Nginx, AWS EC2

**Contexto e problema:**
Consultar um portal público de forma automatizada e devolver os dados estruturados via API, incluindo
screenshot da consulta. O mundo externo não coopera: o portal é instável, lento e não tem contrato de API.

**Decisões técnicas:**

1. **Async porque o problema é I/O-bound**
   Uma consulta pode levar até 3 minutos, quase toda em espera de rede. É exatamente o cenário onde
   async rende. Se o gargalo fosse CPU, a escolha seria multiprocessing — e isso deve estar dito na página.

2. **Pydantic separando entrada e saída**
   Validação automática do request, `response_model` garantindo o contrato de saída e documentação
   Swagger gerada sem esforço extra.

3. **Tratamento de erros em três camadas**
   Detecção de "sem resultado" por texto na página → timeout em operação específica →
   `except Exception` como rede de segurança, com `finally` sempre fechando o browser.

**Problemas reais de produção (a parte mais forte deste caso):**

- **`networkidle` que nunca resolvia.** `wait_for_load_state("networkidle")` espera zero requisições de
  rede por 500ms. O portal tem scripts de analytics e telemetria que nunca param — a espera nunca
  terminava. Solução: trocar por espera em seletor específico.
- **Timeout de 30s insuficiente na EC2.** O WAF da AWS adiciona latência para IPs de servidor;
  o que passava localmente falhava em produção. Timeout virou configurável por variável de ambiente.
- **Nginx cortando a requisição antes do robô terminar.** `proxy_read_timeout` padrão de 120s contra
  consultas que chegavam a ultrapassá-lo. Ajustado para 300s.
- **Falso positivo de "0 resultados".** A checagem procurava a substring `"0 resultados"` — que está
  contida em `"10.000 resultados"`. Corrigido usando a frase completa da página.
- **Clique que travava.** O input estava coberto pela própria label; a solução foi clicar na label,
  que encaminha o evento ao checkbox.
- **Associar benefício à tabela correta sem seletor CSS estável.** Resolvido com `page.evaluate()`
  percorrendo o DOM com TreeWalker a partir do nó de texto.

---

## 4. Arquitetura de informação

### Home (`index.html`)

```
┌──────────────────────────────────────────────────────────┐
│ HERO                                                     │
│  Nome · uma linha de posicionamento                      │
│  3 chips de prova:                                       │
│    [ SaaS em produção com cliente pagante ]              │
│    [ Infraestrutura AWS montada na mão ]                 │
│    [ CI/CD com gate de testes ]                          │
│  CTAs: Baixar CV · GitHub · LinkedIn · E-mail            │
├──────────────────────────────────────────────────────────┤
│ STACK — 4 blocos (ver §2)                                │
├──────────────────────────────────────────────────────────┤
│ CASOS — 4 cards                                          │
│  Cada card mostra:                                       │
│    status (EM PRODUÇÃO) · nome · uma frase               │
│    1 métrica em destaque                                 │
│    1 problema resolvido, em uma linha                    │
│    stack resumida (4 a 5 itens)                          │
│    → Ver o caso completo                                 │
├──────────────────────────────────────────────────────────┤
│ SOBRE — 3 parágrafos curtos (ver §1.1)                   │
│  P1: autodidata · 3 sistemas em produção, sozinho        │
│  P2: Irlanda 2022–2026 — supervisor de loja 3 anos,      │
│      inglês em imersão, 2 anos de BSc em CC.             │
│      A ponte: já foi o usuário do software que constrói  │
│  P3: o que procura agora — time, code review, base       │
│      grande que ele não escreveu                         │
├──────────────────────────────────────────────────────────┤
│ CONTATO — e-mail, telefone, LinkedIn, GitHub, localização│
└──────────────────────────────────────────────────────────┘
```

**O card não pode ser genérico.** "Sistema de gestão para barbearias" não diz nada.
"+5.300 vendas · isolamento multi-tenant validado por testes" diz.

### Página de caso (`casos/*.html`) — template fixo para os quatro

```
1. Cabeçalho     nome · status · período · papel (solo) · links (vídeo/repo)
2. Números       3 a 4 métricas em destaque
3. Stack         chips
4. O problema    contexto de negócio, 2 a 3 parágrafos
5. Arquitetura   diagrama + explicação do fluxo
6. Decisões      3 a 5 blocos: problema → alternativas → escolha → resultado
7. Produção      "O que quebrou e como resolvi" — os bugs reais
8. Resultado     o que mudou, em número quando houver
9. Aprendizado   1 parágrafo, primeira pessoa
10. Navegação    próximo caso · voltar
```

A seção 7 é o diferencial competitivo deste portfólio. Ela deve ter peso visual próprio,
não ser mais um parágrafo. Formato sugerido: cada incidente como um bloco com
**sintoma → investigação → causa → correção**.

---

## 5. Stack e infraestrutura do portfólio

**Decisão tomada: site estático hospedado no Cloudflare Pages.**

Justificativa: portfólio precisa carregar em menos de 1s, custar zero e nunca cair.
Django em plano free hiberna e entrega tela branca ao recrutador. A competência em Django
se prova nos casos, não no portfólio. Cloudflare já é usado nos outros projetos.

**Abordagem recomendada — build estático com Python + Jinja2:**

```
portfolio/
├── build.py                    # renderiza templates → dist/
├── data/
│   └── content.json            # fonte única de verdade do conteúdo
├── templates/
│   ├── base.html
│   ├── index.html
│   └── caso.html               # um template, quatro páginas geradas
├── assets/
│   ├── css/main.css
│   ├── js/main.js
│   ├── img/<projeto>/
│   └── cv/PauloSouza-CV-2026-PT.pdf
├── dist/                       # saída estática (o que o Cloudflare publica)
├── docs/                       # documentação de apoio — NÃO é a saída do build
│   ├── base-de-dados/          # histórico e documentação dos projetos
│   └── regras-de-negocio/      # PORTFOLIO_BRIEF.md + IMPLEMENTATION_ROADMAP.md
├── prints/                     # imagens de trabalho, antes da otimização
│   ├── barber-cashflow/  acai-gestao/  nicia-track/  automacao-scraping/
├── requirements.txt            # jinja2
└── README.md
```

Por que assim: sintaxe Jinja2 é praticamente a mesma do Django template — nada novo para aprender.
Conteúdo separado de layout, então editar um número não exige mexer em HTML.
A saída é 100% estática, sem JavaScript necessário para renderizar conteúdo.

**Alternativa aceitável se preferir simplicidade absoluta:** cinco arquivos HTML escritos à mão,
sem build. Custo: duplicação de header/footer e edição manual em cinco lugares.

**Domínio: `portfolio.paulodev.net`** — subdomínio do `paulodev.net`, já registrado e com DNS
no Cloudflare. Atenção à grafia: **portfolio**, sem "i" ("portifolio" é erro de português e o
link aparece no CV e no LinkedIn).

Setup de publicação:
- Cloudflare Pages → conectar ao repositório do GitHub
- Build command: `python build.py` · Output directory: `dist` · Build system: Python
  (se optar pela alternativa sem build: build command vazio, output directory `/`)
- Custom domain: `portfolio.paulodev.net` (o Cloudflare cria o CNAME automaticamente)
- Considerar redirecionar o apex `paulodev.net` para o portfólio enquanto não houver outro uso
  para a raiz — endereço curto é mais fácil de ditar e mais forte no currículo
- SSL/TLS em modo **Full (strict)** e "Always Use HTTPS" ligado
- Cada `git push` na `main` publica automaticamente — o próprio deploy do portfólio vira mais
  uma evidência de que ele opera o que constrói
- Usar o mesmo e-mail de contato no domínio se quiser (`paulo@paulodev.net`), mas o
  `paulorgs.dev@gmail.com` do CV precisa continuar batendo com o que está no site

**Repositório privado.** O site é público; o repositório, não. A pasta `docs/base-de-dados/`
guarda o histórico dos projetos — que contém o nome da empresa do desafio técnico, trechos de
código do sistema de um cliente pagante e o CV com telefone. O Cloudflare Pages publica
normalmente a partir de repositório privado. Os repositórios que ficam públicos são os dos
projetos (Nícia Track e automação), não o do portfólio.

**Regras técnicas obrigatórias:**
- Zero dependência de framework JS. CSS próprio (Bootstrap opcional, mas o layout não pode
  parecer template Bootstrap padrão).
- Mobile-first. O layout precisa funcionar em 360px de largura.
- Foco de teclado visível. `prefers-reduced-motion` respeitado.
- Imagens em `.webp`, com `loading="lazy"` e `width`/`height` declarados.
- Meta tags Open Graph (recrutador compartilha o link no Slack/WhatsApp — a prévia importa).
- Lighthouse: performance e acessibilidade acima de 95.
- Sem formulário de contato com backend. E-mail em `mailto:` e botão de copiar.

---

## 6. Direção visual

**Conceito: painel de operação.** A identidade não vem de "portfólio de dev" genérico — vem do mundo
real do Paulo: sistemas monitorados, status de deploy, logs, métricas de caixa, pipelines verdes.
A página se comporta como um painel de status de quem opera software, não como uma landing page de agência.

**Como isso se materializa:**
- Fonte monoespaçada usada com função real — métricas, status, nomes de tecnologia, contagens de query —
  nunca como decoração.
- Cada projeto carrega uma **linha de status** no formato de painel:
  `EM PRODUÇÃO · 7 meses · 5.300 vendas · 1 cliente pagante`
- Os bugs de produção apresentados como registro de incidente, com estrutura fixa e legível.

**Tokens iniciais (ponto de partida, refinar na execução):**
- Fundo: off-white levemente frio · Texto: quase-preto com toque de verde-azulado
- Primária: verde profundo, sóbrio (status "em produção")
- Sinal: âmbar, reservado exclusivamente para marcar incidentes e alertas
- Neutros: dois cinzas para divisórias e texto secundário

**O que evitar explicitamente:**
- Fundo creme com serifada de alto contraste e acento terracota (é o visual padrão de IA hoje)
- Fundo preto com acento verde-limão neon
- Gradientes decorativos, glassmorphism, partículas animadas
- Barras de proficiência em porcentagem
- Ícones de tecnologia coloridos em grade — usa-se texto em mono, é mais sóbrio e mais honesto
- Emojis
- Numeração `01 / 02 / 03` em seções que não são sequência de verdade
  (nas fases do deploy AWS, faz sentido — lá é sequência real)

**Idioma:** bilíngue português / inglês, com seletor visível. Especificação completa em §6.1.

---

## 6.1 Bilíngue PT / EN — especificação

O site é escrito em português e tem versão em inglês completa, com seletor de idioma.
O inglês não é acessório: é o que habilita vaga remota internacional, e o Paulo tem inglês
avançado adquirido em imersão — a versão EN é ela mesma uma evidência.

**Implementação — páginas reais, não troca de texto por JavaScript**

```
dist/
├── index.html                        PT (padrão)
├── casos/
│   ├── barber-cashflow.html
│   ├── gestao-acai.html
│   ├── nicia-track.html
│   └── automacao-scraping.html
└── en/
    ├── index.html                    EN
    └── cases/
        ├── barber-cashflow.html
        ├── acai-management.html
        ├── nicia-track.html
        └── automation-scraping.html
```

Por que não trocar o texto com JS:
- O Google indexa as duas versões separadamente — dobra a superfície de busca
- O link compartilhado preserva o idioma (recrutador manda no Slack e chega certo)
- Funciona com JavaScript desligado
- Não há flash de conteúdo no idioma errado ao carregar

**Como construir:** o `content.json` guarda cada string com as chaves `pt` e `en` lado a lado;
o `build.py` renderiza o mesmo template duas vezes, uma por idioma. Nenhum template duplicado.

```json
{
  "hero": {
    "posicionamento": {
      "pt": "Construí e mantenho sozinho três sistemas em produção.",
      "en": "I built and single-handedly maintain three systems in production."
    }
  }
}
```

**Seletor de idioma**
- Posição: canto superior direito do cabeçalho, em todas as páginas
- Formato: `PT | EN` em IBM Plex Mono, o idioma ativo em `--text`, o outro em `--muted`
- Cada opção é um `<a href>` para a **página equivalente** no outro idioma — nunca para a home.
  Quem está lendo o caso do Barber em português vai para o caso do Barber em inglês.
- Sem redirecionamento automático por `navigator.language`. Detectar idioma e redirecionar
  sozinho irrita quem quer a outra versão e atrapalha o rastreamento do Google.
- Sem bandeirinha. Bandeira representa país, não idioma.

**SEO obrigatório em toda página**
```html
<link rel="alternate" hreflang="pt-BR" href="https://portfolio.paulodev.net/...">
<link rel="alternate" hreflang="en"    href="https://portfolio.paulodev.net/en/...">
<link rel="alternate" hreflang="x-default" href="https://portfolio.paulodev.net/...">
```
Mais `<html lang="pt-BR">` / `<html lang="en">` correto em cada versão, e as duas versões
no `sitemap.xml`.

**Cuidados de conteúdo**
- A tradução precisa soar nativa. Termos técnicos ficam em inglês nos dois idiomas
  (multi-tenant, deploy, pipeline), mas o texto ao redor não pode ser tradução literal.
  O Paulo revisa o inglês — ele tem repertório para isso e é o diferencial dele.
- **Todo número aparece duas vezes.** Ao alterar uma métrica, alterar nos dois idiomas.
  Manter `pt` e `en` adjacentes no JSON justamente para tornar o esquecimento visível.
- Formato de moeda: manter `R$ 245 mil` nas duas versões (é a moeda real da operação),
  mas na versão EN escrever `R$245K in transaction volume` — não converter para dólar.
- **CV:** a versão EN precisa de um PDF em inglês. Recrutador em modo EN clicando em
  "Download CV" e recebendo um PDF em português é uma quebra de expectativa cara.
  Se o CV em inglês não estiver pronto, rotular o botão como "Download CV (Portuguese)".

**Escopo:** a versão EN cobre home e os quatro casos por inteiro. Não fazer versão parcial —
página que cai em português no meio da navegação em inglês passa impressão de inacabado.

---

## 7. Regras de redação (não negociáveis)

1. **"+R$245 mil movimentados" nunca aparece sozinho.** Sempre "volume transacionado pelo sistema"
   ou "processados pelo sistema". Sem isso, um leitor apressado entende faturamento pessoal.
2. **Primeira pessoa, verbo no passado, voz ativa.** "Reduzi o fechamento de caixa de 1 hora para
   10 minutos" — não "foi implementada uma redução".
3. **Número sempre acompanhado do que ele mede.** "296 testes" isolado não diz nada;
   "296 testes rodando contra PostgreSQL real a cada push" diz.
4. **Nada de superlativo.** Sem "robusto", "escalável", "de ponta", "inovador", "apaixonado por
   tecnologia". Se a frase sobrevive à remoção do adjetivo, o adjetivo sai.
5. **A lacuna de experiência em time não aparece no portfólio.** É assunto de entrevista, onde há
   espaço para enquadrar. Numa página web vira só um ponto fraco solto.
6. **Não usar "MOST" nem o nome da empresa do desafio técnico** em lugar nenhum.
7. **Sem contradição de status.** Se um projeto está no portfólio, ele está no CV, e vice-versa.

---

## 8. Especificação dos screenshots

**Regras gerais:**
- Largura mínima de 1600px, proporção 16:10, exportar em `.webp` (qualidade 82)
- Sem barra do navegador, sem barra de tarefas, sem abas
- Tema claro (contrasta melhor com o layout e imprime melhor)
- **Anonimizar todo dado pessoal real:** nomes de clientes, CPF, telefone, e-mail, endereço.
  Substituir por nomes fictícios plausíveis — desfoque fica amador. Valores financeiros podem ficar reais.
- Nomear os arquivos como `assets/img/<projeto>/01-<descricao>.webp`

**Mapeamento das pastas de trabalho → destino no site:**

| Pasta de origem (`prints/`) | Destino no site |
|---|---|
| `barber-cashflow/` | `assets/img/barber/` |
| `acai-gestao/` | `assets/img/acai/` |
| `nicia-track/` | `assets/img/nicia/` |
| `automacao-scraping/` | `assets/img/automacao/` |

> A pasta de origem do último caso **não pode** se chamar `mostqi`: o nome da empresa apareceria
> no caminho da imagem dentro do HTML, contrariando a decisão de não citá-la. Mesmo cuidado com
> o nome do repositório — nada de `mostqi` em path, branch, commit ou README.

**Barber Cashflow — 4 imagens:**
1. Dashboard financeiro (lucro líquido, conciliação por forma de pagamento)
2. Tela de venda com comissionamento por barbeiro
3. Agenda / calendário de agendamentos
4. PWA aberto no celular **ou** o assistente de IA respondendo uma pergunta — escolher o mais apresentável

**Açaí — 4 imagens:**
1. Tela de fechamento de caixa (é a que sustenta o "1 hora → 10 minutos")
2. Painel de pedidos do dia
3. Relatório de vendas por produto / litros / horário de pico
4. **Print do GitHub Actions com o pipeline verde**, mostrando os jobs de lint, testes e coverage —
   esta vale mais que qualquer tela de aplicação, é a prova visual do CI/CD
5. **Print da pasta no Google Drive com os backups datados** — provam a rotação e o agendamento
   funcionando de verdade. Junto com a de cima, são as duas imagens mais valiosas do site inteiro:
   qualquer um faz uma tela bonita, quase ninguém tem prova de que opera o sistema.

**Nícia Track — 4 imagens:**
1. Dashboard com streak e metas diárias
2. Simulado em andamento
3. Caderno de erros
4. Console AWS mostrando a instância EC2 e o RDS — prova da infraestrutura

**Automação/Scraping — 3 imagens:**
1. Swagger do FastAPI com o endpoint documentado
2. Resposta JSON de uma consulta bem-sucedida (dados pessoais anonimizados)
3. O screenshot capturado pelo próprio robô (anonimizado)

**Diagramas a produzir (SVG, não imagem raster):**
- Nícia Track: fluxo usuário → Cloudflare → Nginx → Gunicorn → Django → RDS / S3
- Açaí: fluxo do pipeline push → CI → gate → deploy, e o fluxo do backup agendado
- Barber: diagrama de isolamento multi-tenant (requisição → middleware → filtro por tenant)

---

## 9. Ordem de execução sugerida

1. Estrutura de pastas, `build.py`, `base.html` e o CSS base com os tokens
2. Página de caso do **Barber** completa — é a mais rica; ela valida o template
3. Home, já consumindo o `content.json`
4. As outras três páginas de caso
5. Diagramas SVG
6. Screenshots, otimização de imagem, Open Graph, favicon
7. Auditoria: Lighthouse, teclado, mobile 360px, leitura em voz alta do texto
8. Deploy no Cloudflare Pages + domínio próprio

---

## 10. Pendências do Paulo (bloqueiam a entrega final)

- [ ] Gerar os screenshots conforme §8, já anonimizados
- [ ] Decidir quais repositórios ficam públicos (Barber provavelmente permanece privado)
- [ ] Alinhar CV e portfólio: mesma lista de projetos, mesmos números, mesmo fraseado
- [x] ~~Definir o domínio~~ — `portfolio.paulodev.net`, DNS no Cloudflare
- [ ] Confirmar se há restrição contratual sobre publicar o desafio técnico, mesmo sem citar a empresa
