# CONTEXT_SUMMARY.md — Entendimento da Fase de Leitura

> Resumo do que entendi após ler o BRIEF, o ROADMAP, todo o `docs/base-dados/`
> (incl. o CV em PDF) e listar `prints/`. **O BRIEF é o contrato e vence qualquer
> conflito.** Este arquivo é só registro de entendimento — nenhuma fase foi iniciada.

## Regras inegociáveis que estou carregando
- **BRIEF > base-dados** em qualquer conflito; conflito eu reporto, não resolvo sozinho.
- **Não inventar** número, métrica, tecnologia ou resultado que não esteja no BRIEF.
- **O nome "mostqi"/"MOST" não pode aparecer** em nenhum lugar do site nem em
  arquivo, pasta, branch, commit, README ou path de imagem. O projeto se chama
  **"Automação e Web Scraping"**. A pasta `prints/mostqi/` precisa virar
  `prints/automacao-scraping/` (blocker de Fase 5). O portal consultado (Portal da
  Transparência) é público e pode ser citado; a empresa do desafio, não.
- **Nenhuma fase começa sem aprovação explícita do Paulo.**

## O que é o portfólio (em poucas linhas)
Site estático bilíngue (PT/EN) que prova, em <60s, que o Paulo **constrói e opera**
software real em produção — não que conhece muitas tecnologias. Dois públicos:
recrutador/RH lê a Home (30–60s: quem é, stack, prova, contato); tech lead/CTO lê as
páginas de caso (5–10 min: decisões técnicas justificadas, problemas de produção,
trade-offs). Direção visual "painel de operação" (mono com função real, status
"EM PRODUÇÃO", incidentes como registro). A seção "O que quebrou e como resolvi"
(§7 das páginas de caso) é o diferencial competitivo. Stack do site: build estático
Python + Jinja2 → `dist/`, hospedado no Cloudflare Pages em `portfolio.paulodev.net`.
Zero framework JS, mobile-first 360px, Lighthouse ≥95, `docs/` fica privado.

## Os quatro casos (números autorizados só pelo BRIEF)

### 1. Barber Cashflow — SaaS multi-tenant para barbearias
- Frase: SaaS multi-tenant que leva agendamento, venda, comissão, estoque e caixa de uma barbearia real à produção.
- Stack: Django, DRF, JWT, PostgreSQL, Docker, Nginx, Cloudflare, PWA, OpenAI Embeddings (`text-embedding-3-small`) + FAISS.
- Números (ref. **29/07/2026**, 25/11/2025→29/07/2026, ~8 meses): **+R$245 mil em volume transacionado pelo sistema**; **~7.000 vendas**; 5 barbeiros; **+4.000 linhas de testes**. Recorte: PIX R$143.335 · Cartão R$72.210 · Dinheiro R$30.150. Prova: vídeo youtube.com/watch?v=r9bsFbj2NdE.
- Produção (o que contar): **N+1 na listagem de vendas** — 20 vendas disparavam ~61 queries (1+20+20+20), corrigido com `select_related` + `prefetch_related`. Outras decisões: multi-tenancy shared-db com `tenant_id` via middleware; teste de isolamento retornando **404 (não 403)**; `transaction.atomic` no cancelamento de venda; soft delete; RAG real (chunking + embeddings + FAISS).
- Sensibilidade: nenhum print pode expor nome real da barbearia, URL, usuário logado ou **comissão nominal por barbeiro**. Volume agregado é publicável.

### 2. Sistema de Gestão para Delivery de Açaí
- Frase: gestão operacional/financeira (pedidos, fechamento, despesas, estoque, relatórios) em uso diário por funcionários de um estabelecimento real da família.
- Stack: Django, PostgreSQL (Neon), Render, GitHub Actions, Ruff, pytest, rclone, Google Drive API. (Sem DRF — confirmado no ROADMAP_PEDIDOS.)
- Números: fechamento de caixa **~1h → ~10min**; **~296 testes** contra PostgreSQL real na CI; **gate de cobertura 80%**; primeira semana do módulo de pedidos **+115 pedidos e +R$4,6 mil**.
- Produção (o que contar): **CI/CD com trava de deploy** (antes: push→deploy direto sem testes; depois: push/PR→Ruff→pytest em Postgres real→gate 80%→Deploy Hook do Render só com CI verde + branch protection); **Postgres real na CI, não SQLite**; **backup diário via GitHub Actions** (pg_dump no endpoint direto do Neon→gzip→rclone→Google Drive→rotação 15, validado **17/07/2026**); arquitetura em camadas (`PROJECT_RULES.md`). Incidentes reais do backup: pg_dump 16 vs Neon 18 (PGDG + `$GITHUB_PATH`), pooler/PgBouncer incompatível com pg_dump, secret multiline via `gh secret set`, ordem validar-upload-antes-de-rotacionar.

### 3. Nícia Track — plataforma de estudos + infraestrutura AWS
- Frase: plataforma de preparação para concurso construída pelo domínio (edital→curadoria→matérias) e usada como laboratório de infraestrutura AWS de ponta a ponta.
- Stack: Django, PostgreSQL, Docker, Gunicorn, Nginx, AWS (EC2, RDS, S3, IAM), Cloudflare.
- Números: **800 questões reais / 13 disciplinas**; **~3.171 linhas de testes**; **migração Render → AWS** validada em produção.
- Produção/decisões: camadas desde o dia 1 (View→Service→ORM), `BaseModel` UUID PK, settings por ambiente (testing = SQLite `:memory:` + MD5 hasher); deploy AWS em fases; **Security Group do RDS aceita só o SG da EC2** + `sslmode=require`; **media files perdidos a cada redeploy → S3** + django-storages; **migrations separadas do startup** do container. É o caso do "diagrama do DNS ao banco".

### 4. Serviço de Automação e Web Scraping Assíncrono
- Frase: serviço de automação (desafio técnico) que consulta um portal público (Portal da Transparência) e devolve dados estruturados + screenshot via API.
- Stack: FastAPI, Playwright (async), Pydantic, Docker, Nginx, AWS EC2. Status: concluído e implantado em EC2. **BRIEF não autoriza nenhuma métrica numérica para este caso.**
- Produção (a parte mais forte — contar como registro de incidente):
  - `networkidle` que nunca resolvia (scripts de analytics/telemetria não param) → esperar por seletor específico.
  - Timeout de 30s insuficiente na EC2 (latência do WAF da AWS para IP de servidor) → timeout configurável por env var.
  - Nginx cortando a requisição (`proxy_read_timeout` 120s) → ajustado para 300s.
  - Falso positivo "0 resultados" (substring de "10.000 resultados") → frase completa da página.
  - Clique travado pela label cobrindo o input → clicar na label.
  - Associar benefício à tabela certa sem seletor estável → `page.evaluate()` com TreeWalker.
  - Decisões: async porque I/O-bound (consultas de até ~3 min); Pydantic separando entrada/saída (+ Swagger); tratamento de erro em 3 camadas com `finally` fechando o browser.

## Inconsistências encontradas (listadas, não resolvidas — BRIEF vence)
1. **Números do Barber divergem entre BRIEF e CV.** CV: +5.300 vendas / +R$194 mil / ~7 meses. BRIEF §3.1 (ref. 29/07/2026): ~7.000 vendas / +R$245 mil / ~8 meses. O próprio BRIEF sinaliza que os números são vivos e o CV precisa ser atualizado (§3.1, §10).
2. **O 4º caso (Automação/Scraping) está no BRIEF mas não no CV.** O CV lista só 3 projetos. O BRIEF §7.7 exige que portfólio e CV tenham a mesma lista de projetos → contradição a resolver.
3. **Skills do CV omitem tecnologias que o BRIEF §2 manda exibir:** FastAPI, Neon, RDS, S3, RAG/Embeddings, Web Scraping assíncrono não aparecem no CV atual.
4. **Inconsistência interna do BRIEF:** os mockups de layout (§4 "+5.300 vendas" e §6 "EM PRODUÇÃO · 7 meses · 5.300 vendas") usam os números **antigos**, contradizendo os números canônicos de §3.1 (~7.000 / ~8 meses). São placeholders ilustrativos, mas conflitam com o dado oficial.
5. **ROADMAP × BRIEF sobre a saída do build:** BRIEF §5 é claro que `dist/` é a saída e `docs/` é só documentação; o ROADMAP Fase 0 (Critério de conclusão) diz "`python build.py` … gera `docs/`". Sigo o BRIEF: saída = `dist/`.
6. **Título/posicionamento:** BRIEF §1 = "Desenvolvedor Backend Python"; CV = "Desenvolvedor Full Stack — Python / Django".
7. **HTMX:** aparece na base-dados do Nícia Track (doc 03) mas não na stack do BRIEF (§2/§3.3) → não vai para o site (não inventar tecnologia fora do BRIEF).
8. **Largura mobile base:** BRIEF/ROADMAP = 360px; `PROJECT_RULES.md` (projeto Açaí) = 390px. São projetos diferentes; para o portfólio vale 360px.
9. **Nomes de pasta:** a árvore ilustrativa do BRIEF §5 usa `docs/base-de-dados/` e `docs/regras-de-negocio/`; o repo real usa `docs/base-dados/` e `docs/regras-negocio/`. Cosmético.

## Dados reais a anonimizar (aparecem na base-dados, não podem ir ao site)
- **"Açaí da Rose"** (Buritizeiro/MG) e o fato de a usuária ser mãe do Paulo — o BRIEF trata como "estabelecimento real da família".
- Nome real da barbearia, sua URL, usuários e comissão por barbeiro (Barber).
- Nícia Track pode manter o nome (o BRIEF o usa), mas os prints anonimizam dados pessoais (nome da usuária, edital, CPF/NIS etc.).
- Nos docs de scraping há CPF/NIS/nomes de exemplo do portal — anonimizar em qualquer print.

## Estado de `prints/` (só listado)
- `prints/barber-cashflow/` — vazia
- `prints/acai-gestao/` — vazia
- `prints/nicia-track/` — vazia
- `prints/mostqi/` — vazia **e com nome proibido; renomear para `automacao-scraping/`**
Ou seja: nenhum screenshot foi gerado ainda (pendência do Paulo, blocker de Fase 5).

## Lacunas para executar a Fase 0
Posso fazer localmente sem perguntar nada: `git init`; estrutura de pastas (§5);
`build.py` mínimo (lê `content.json` → renderiza `templates/` → escreve `dist/`);
`content.json` com esqueleto de chaves `pt`/`en` sem texto final; `templates/base.html`
+ `index.html` provisória ("em construção"); `requirements.txt` (jinja2); `README.md`;
`.gitignore`; e renomear `prints/mostqi/` → `prints/automacao-scraping/`. Também copiar
`assets/cv/PauloSouza-CV-2026-PT.pdf` a partir do CV existente.
**Depende do Paulo (contas externas):** criar o repositório GitHub `paulo-portfolio`,
conectar o Cloudflare Pages, apontar `portfolio.paulodev.net`, ligar Full (strict) +
Always Use HTTPS. Sem isso o "site vazio no ar" da Fase 0 não fecha, mas todo o
scaffold local fica pronto para o `git push`.

## Perguntas que bloqueiam (para o Paulo)
1. Confirmar que uso os números do BRIEF §3.1 no Barber (~7.000 vendas / +R$245 mil, ref. 29/07/2026) e ignoro os do CV — que você atualiza depois.
2. O caso de Automação/Scraping vai ao site já (você inclui no CV depois) ou só quando o CV incluir? (BRIEF §7.7 pede paridade portfólio↔CV.)
3. Na Fase 0, quem provisiona o repositório GitHub + Cloudflare Pages + DNS (contas suas)? Eu entrego o scaffold local pronto para o push.
