# IMPLEMENTATION_ROADMAP.md — Portfólio Paulo Souza

> Plano de execução por fases. O **conteúdo, os números e as regras** vêm do
> `PORTFOLIO_BRIEF.md` — este documento define apenas **em que ordem construir** e
> **quando uma fase está pronta**.
>
> Regra geral: cada fase entrega algo que funciona de ponta a ponta. Nenhuma fase pressupõe
> que a seguinte está feita. Não avançar com o critério de conclusão em aberto.

---

## Visão geral

```
Fase 0 — Repositório, esqueleto e deploy vazio no ar
Fase 1 — Design system (tokens, tipografia, componentes)
Fase 2 — Home em português
Fase 3 — Primeiro caso completo (Barber) — define o template
Fase 4 — Os outros três casos
Fase 5 — Diagramas e imagens
Fase 6 — Versão em inglês
Fase 7 — SEO, acessibilidade e auditoria final
```

**Princípio que vale para o roadmap inteiro:** o site vai ao ar na Fase 0, ainda vazio.
Deploy cedo elimina a categoria inteira de problema "funcionava local e quebrou ao publicar".

---

## Fase 0 — Repositório, esqueleto e deploy vazio

### Objetivo
Ter `portfolio.paulodev.net` respondendo com HTTPS antes de existir qualquer conteúdo.

### O que será feito
- Criar o repositório `paulo-portfolio` no GitHub (atenção à grafia)
- Montar a estrutura de pastas conforme §5 do brief
- Escrever o `build.py` mínimo: lê `content.json`, renderiza `templates/`, escreve em `dist/`
- **Repositório privado.** `docs/` já é documentação do Paulo e não pode ser a saída do build,
  nem ir a público — ver §5 do brief
- Criar `content.json` com o esqueleto de chaves `pt` / `en`, ainda sem texto final
- Uma `index.html` provisória com o nome e "em construção"
- Conectar ao Cloudflare Pages, apontar o custom domain, ligar Full (strict) e Always Use HTTPS
- `README.md` explicando como rodar o build localmente

### Critério de conclusão
- `https://portfolio.paulodev.net` abre com cadeado válido
- `git push` na `main` publica automaticamente
- `python build.py` roda local sem erro e gera `docs/`

### Riscos
- Custom domain propagando: pode levar alguns minutos, não é erro
- Output directory errado no Pages → build verde mas site 404
- Confundir `docs/` (documentação) com `dist/` (saída do build) e sobrescrever material de origem

---

## Fase 1 — Design system

### Objetivo
Fechar a linguagem visual antes de escrever página, para não redesenhar quatro vezes.

### O que será feito
- `main.css` com os tokens do §6 no `:root` (cores, escala tipográfica, escala de espaçamento)
- Carregar as fontes (Archivo, IBM Plex Sans, IBM Plex Mono) com `preconnect` e `font-display: swap`
- `base.html`: cabeçalho com navegação e seletor de idioma, rodapé, blocos de meta
- Componentes base: chip de stack, bloco de métrica, registro de decisão, bloco de incidente,
  card de caso, hairline de seção
- Uma página `styleguide.html` (fora do sitemap) exibindo todos os componentes juntos

### Critério de conclusão
- O styleguide renderiza todos os componentes em 360px e em desktop
- Foco de teclado visível em todo elemento interativo
- `prefers-reduced-motion` respeitado
- Nenhuma cor ou tamanho escrito direto no CSS — tudo via variável

### Riscos
- Especificidade de seletor se cancelando entre `.section` e elementos internos (§ do brief)
- Âmbar (`--signal`) usado demais e perdendo força — máximo 5 ocorrências por tela

---

## Fase 2 — Home em português

### Objetivo
A página que o recrutador vê primeiro, funcionando por inteiro.

### O que será feito
- Preencher `content.json` com o conteúdo em português da home
- Hero / painel de operação (elemento assinatura do §6)
- Bloco de stack em quatro grupos
- Quatro cards de caso — cada um com métrica e problema resolvido, nunca só o nome
- Seção "Sobre" nos três parágrafos do §1.1, com a Irlanda como ponte
- Contato com `mailto:`, LinkedIn, GitHub e download do CV
- Animação de entrada das linhas do painel

### Critério de conclusão
- Alguém que nunca ouviu falar do Paulo entende em 30 segundos o que ele faz e qual a prova
- Lighthouse ≥ 95 em performance e acessibilidade
- Funciona com JavaScript desligado
- Nenhum adjetivo de venda no texto (§7 do brief)

### Riscos
- Hero virar "nome grande + gradiente" genérico em vez do painel especificado
- Cards descrevendo o projeto em vez de provar resultado

---

## Fase 3 — Caso do Barber Cashflow (template de referência)

### Objetivo
Construir o caso mais rico primeiro. Ele define o template dos outros três.

### O que será feito
- Página completa seguindo as 10 seções do §4 do brief
- Registros de decisão: multi-tenancy, 404 vs 403, `transaction.atomic`, soft delete, RAG
- Bloco "em produção": o N+1 de 61 queries
- Números da §3.1 com data de referência
- Link para o vídeo de demonstração

### Critério de conclusão
- **Revisão do Paulo antes de replicar.** Esta fase tem um portão humano: nada de construir
  os outros três casos antes de o template estar aprovado.
- Um leitor técnico consegue explicar, só lendo a página, por que a escolha de multi-tenancy
  foi essa e não outra
- A seção de incidente tem peso visual próprio, não é mais um parágrafo

### Riscos
- Transformar decisão em lista de features — o formato problema → alternativa → escolha →
  resultado não é opcional
- Amenizar o incidente de produção. Ele é o diferencial do site.

---

## Fase 4 — Os outros três casos

### Objetivo
Replicar o template aprovado para Açaí, Nícia Track e Automação.

### O que será feito
- `gestao-acai.html` — CI/CD com gate de 80%, backup no Drive, e a decisão de reescrever o
  backup para GitHub Actions por não existir servidor sempre ligado
- `nicia-track.html` — service layer, settings por ambiente, e as decisões de AWS
  (por que RDS, por que S3, por que Nginx, Security Groups, IAM com menor privilégio)
- `automacao-scraping.html` — os quatro incidentes de produção, que são o ponto alto do site
- Navegação entre casos no rodapé de cada um

### Critério de conclusão
- Os quatro casos têm exatamente a mesma estrutura de seções
- Nenhuma menção ao nome da empresa no caso de automação — nem em texto, path, commit ou README
- Cada caso tem pelo menos um número e pelo menos um problema real resolvido

### Riscos
- Casos 2, 3 e 4 saírem mais fracos que o primeiro por cansaço de redação
- Repetir o mesmo fraseado nos quatro, deixando o texto mecânico

---

## Fase 5 — Diagramas e imagens

### Objetivo
Dar prova visual ao que o texto afirma.

### O que será feito
- Diagramas em SVG inline, no estilo de desenho técnico (§8 do brief):
  Nícia Track (fluxo AWS), Açaí (pipeline de CI e fluxo do backup), Barber (isolamento por tenant)
- Integrar os prints das pastas de trabalho nos destinos do §8
- Converter para `.webp`, declarar `width`/`height`, `loading="lazy"`, `alt` descritivo
- Conferir a anonimização de cada imagem antes de commitar

### Critério de conclusão
- Nenhuma imagem contém nome real de cliente, dado pessoal, credencial, endpoint ou account ID
- Diagramas legíveis em 360px (scroll horizontal no container, sem deformar)
- Nenhuma imagem acima de 200 KB

### Riscos
- Publicar dado sensível por descuido. Uma vez no Git, fica no histórico — conferir **antes**
  do commit, não depois.
- Imagem pesada derrubando o Lighthouse conquistado na Fase 2

---

## Fase 6 — Versão em inglês

### Objetivo
Gerar `/en/` completa, com seletor funcional e SEO correto.

### O que será feito
- Preencher as chaves `en` do `content.json` (home + quatro casos, por inteiro)
- `build.py` renderizando os dois idiomas a partir dos mesmos templates
- Seletor `PT | EN` apontando para a página equivalente, nunca para a home
- Tags `hreflang` (pt-BR, en, x-default) e `<html lang>` correto em cada versão
- CV em inglês, ou rótulo "Download CV (Portuguese)" enquanto não existir

### Critério de conclusão
- Toda página em português tem equivalente em inglês — nenhuma navegação cai no idioma errado
- Revisão do inglês feita pelo Paulo (é o diferencial dele; tradução literal derruba o efeito)
- Números idênticos nas duas versões

### Riscos
- Versão EN parcial, que passa impressão de inacabado
- Número atualizado só em um idioma

---

## Fase 7 — SEO, acessibilidade e auditoria final

### Objetivo
Fechar o que faz o site ser encontrado, compartilhado e usável por qualquer pessoa.

### O que será feito
- `<title>` e `<meta description>` únicos por página, nos dois idiomas
- Open Graph completo e imagem de compartilhamento (recrutador manda o link no WhatsApp)
- `favicon.svg`, `robots.txt`, `sitemap.xml` com as duas versões
- JSON-LD `Person` na home
- Auditoria: Lighthouse, navegação só por teclado, leitor de tela, mobile 360px
- Leitura em voz alta de todo o texto — o que soa estranho falado, está mal escrito

### Critério de conclusão
- Lighthouse ≥ 95 em performance e acessibilidade em todas as páginas, nos dois idiomas
- Prévia do link correta ao colar no WhatsApp e no LinkedIn
- Site inteiro navegável só com teclado
- Nenhum link quebrado

### Riscos
- Deixar o styleguide indexável
- OG image faltando → prévia sem imagem, que reduz o clique

---

## Portões humanos (não são do Claude Code)

| Depois da fase | O Paulo precisa |
|---|---|
| 1 | Aprovar a direção visual no styleguide |
| 3 | **Aprovar o template de caso antes de replicar** |
| 5 | Conferir imagem por imagem a anonimização |
| 6 | Revisar o inglês inteiro |
| 7 | Ler o site em voz alta, do começo ao fim |

---

## Pendências que bloqueiam fases

| Pendência | Bloqueia |
|---|---|
| Prints gerados e anonimizados | Fase 5 |
| Decisão de repositórios públicos (Nícia Track e Automação sim; Barber e Açaí não) | Fase 4 |
| Repositório público só de infraestrutura do Açaí, se for fazer | Fase 4 |
| CV em inglês | Fase 6 |
| CV em português atualizado com R$ 245 mil e ~7.000 vendas | Fase 2 |
| Renomear a pasta de prints `mostqi` → `automacao-scraping` | Fase 5 |
