# Módulo 5 — Multi-Tenancy e Isolamento de Dados

> Tempo de estudo: ~40–45 min
> Objetivo: dominar a defesa da decisão de arquitetura mais sofisticada dos seus projetos. Multi-tenancy é o tema onde um CTO mais vai cavar fundo — e o que mais te distingue de um candidato júnior comum. Este módulo existe para você conduzir essa conversa com autoridade.

---

## Por que multi-tenancy merece um módulo só

Poucos candidatos júnior/pleno implementaram multi-tenancy de verdade. É um problema de arquitetura que mistura três coisas que assustam: **segurança** (um erro vaza dados de um cliente para outro), **compliance** (LGPD, contratos entre empresas concorrentes) e **design de dados** (como isolar sem duplicar infraestrutura). Ter feito isso, num sistema real e em produção, é o seu maior trunfo técnico.

O que o entrevistador quer descobrir quando toca no assunto:
- **Foi você quem decidiu a arquitetura?** Ou herdou pronta?
- **Você entende os impactos?** Principalmente de segurança e do que acontece se o isolamento falhar.
- **Considerou alternativas?** Existem três estratégias clássicas; você sabe por que escolheu a sua?
- **Consegue defender a escolha sob pressão?** Incluindo admitir suas fraquezas e como você as mitiga.

O que você precisa dominar:
- As três estratégias de multi-tenancy e o trade-off de cada uma.
- Como o seu isolamento funciona, camada por camada (model → middleware → filtro → teste).
- Por que testar o isolamento é parte da implementação, não um extra.
- As sutilezas de segurança (404 vs 403) e os pontos de fragilidade (o filtro que não pode ser esquecido).

---

## O panorama: as três estratégias de multi-tenancy

Antes de defender a sua escolha, você precisa saber contra o que a comparou. Existem três abordagens clássicas para isolar dados de múltiplos clientes (tenants) num SaaS:

**1. Shared database, shared schema** (a que você usou)
Todos os tenants no mesmo banco, nas mesmas tabelas, distinguidos por uma coluna `tenant_id`. O isolamento é *lógico* — garantido pela aplicação, que filtra toda query por tenant.

**2. Shared database, separate schemas**
Um banco só, mas cada tenant tem seu próprio schema (conjunto de tabelas). Isolamento mais forte, mas gerenciar migrations em muitos schemas fica pesado.

**3. Separate databases** (um banco por tenant)
Isolamento máximo — cada cliente num banco próprio. Mais caro, mais complexo de operar, mas às vezes exigido por clientes enterprise com requisitos rígidos.

O trade-off central: **quanto mais forte o isolamento, maior o custo e a complexidade de operação.** A abordagem 1 é a mais barata e simples de deployar; a 3 é a mais isolada e cara. Saber posicionar sua escolha nesse espectro é o coração da resposta.

---

## A decisão central: shared database com `tenant_id` + isolamento na aplicação

### O que é

Um único banco compartilhado onde cada tabela de domínio tem uma FK para `Tenant`, e o isolamento é garantido em camadas pela aplicação: um middleware descobre o tenant do request, e toda query filtra obrigatoriamente por ele.

### Onde utilizei

No Barber Cashflow, o SaaS de barbearias. Cada barbearia é um tenant. A implementação tem cinco camadas que trabalham juntas:

1. **Model `Tenant`** — representa a barbearia (nome, slug, `ativo`).
2. **FK `tenant` em todos os models de domínio** — Sale, Agendamento, CashRegister etc. carregam `tenant`.
3. **`TenantMiddleware`** — resolve o tenant do request (sessão → perfil → domínio) e o grava em `request.tenant`.
4. **Filtro obrigatório nas views** — todo `get_queryset` começa com `.filter(tenant=self.request.tenant)`.
5. **Testes de isolamento** — provam automaticamente que um tenant nunca vê dados de outro.

### Qual problema resolveu

O problema fundamental de um SaaS B2B: barbearias concorrentes usam a mesma aplicação, e nenhuma pode ver os dados da outra. Vazamento aqui não é um bug qualquer — é quebra de contrato, violação de LGPD e perda total de confiança no produto. O isolamento é o que torna o SaaS vendável.

### Por que escolhi essa solução

Porque, para o estágio do produto, ela dá o melhor equilíbrio entre isolamento e simplicidade operacional. Com shared database eu tenho:
- **Um deploy só, um banco só** — sem multiplicar infraestrutura por cliente.
- **Migrations aplicadas uma vez** — não uma vez por schema ou por banco.
- **Custo baixo** — essencial para um produto que está começando com poucos clientes.

O isolamento lógico é suficiente desde que seja rigoroso e testado — e é aí que entram as camadas de middleware, filtro obrigatório e testes.

### Alternativas

Já detalhadas acima. Em resumo: schema-per-tenant e database-per-tenant dão isolamento mais forte, mas com custo operacional que não se justifica no estágio atual. A escolha de shared database foi consciente, não default.

### Quais vantagens trouxe

- Operação simples: um deploy, um banco, migrations únicas.
- Custo de infraestrutura baixo.
- Isolamento garantido por camadas testadas.

### Hoje eu faria igual?

Para o estágio atual, sim. Mas tenho clareza do caminho de evolução: para um cliente enterprise que exija isolamento físico, migraria *aquele* tenant para um banco separado, mantendo os demais em shared. E, como reforço de segurança dentro do modelo atual, adicionaria **Row-Level Security (RLS) do PostgreSQL** — que empurra o filtro de tenant para o próprio banco, de modo que mesmo uma query que esquecesse o filtro na aplicação não vazaria dados. É a melhoria mais valiosa que tenho mapeada, porque ataca justamente a maior fraqueza da abordagem.

### Qual foi o principal aprendizado

Que isolamento lógico é tão forte quanto a disciplina que o sustenta. A abordagem shared database transfere a responsabilidade de segurança para a aplicação — e isso significa que uma única query sem o filtro de tenant é uma brecha. Aprender isso me levou a tratar os testes de isolamento como parte não-negociável da implementação, e a enxergar o RLS como a rede de segurança que remove a dependência da disciplina humana.

### Como um CTO enxerga isso

Quando um CTO pergunta sobre multi-tenancy, ele quase nunca quer a definição. Ele quer descobrir:
- **Se foi você quem tomou a decisão** — então fale em primeira pessoa, com o raciocínio da escolha.
- **Se você entende os impactos de segurança** — mencione o que acontece se o isolamento falha (vazamento entre concorrentes, LGPD).
- **Se considerou alternativas** — cite as três estratégias e por que a sua.
- **Se você conhece a fraqueza da sua própria escolha** — o filtro que não pode ser esquecido — e como mitiga (testes + RLS como evolução).

O candidato que impressiona não é o que diz "implementei multi-tenant e funciona". É o que diz "escolhi shared database por custo e simplicidade, sei que a fraqueza é depender do filtro na aplicação, por isso tenho testes de isolamento e o próximo passo seria RLS". Isso mostra que você pensa como dono do sistema, não como executor de tarefa.

### O que um CTO provavelmente perguntaria

- Quais estratégias de multi-tenancy existem e por que você escolheu a sua?
- Como você garante que nenhuma query escapa do filtro de tenant?
- O que acontece se alguém esquecer o filtro numa view nova?
- O que é Row-Level Security e como ela ajudaria aqui?
- Como você escalaria para um cliente que exige isolamento físico?

### Como responder em uma entrevista

**Objetiva (30–60s):**
> "No Barber implementei multi-tenancy com shared database: cada barbearia é um tenant, e todo model tem uma FK para tenant. Um middleware resolve qual tenant está ativo no request, e todas as views filtram por ele obrigatoriamente. Tenho testes de isolamento que provam que uma barbearia nunca vê dados de outra. Escolhi shared database por custo e simplicidade operacional — um deploy, um banco, migrations únicas."

**Aprofundada:**
> "Existem três estratégias: banco separado por tenant, schema separado por tenant, ou shared database com tenant_id. Escolhi a última porque no estágio do produto ela dá o melhor equilíbrio — isolamento suficiente com operação simples e custo baixo. O isolamento é lógico, garantido em camadas: FK de tenant nos models, middleware que resolve o tenant, filtro obrigatório nas queries, e testes que validam tudo. A fraqueza dessa abordagem é honesta: o isolamento depende de não esquecer o filtro numa view nova. Mitigo isso com testes de isolamento automatizados, e a evolução natural seria Row-Level Security no Postgres, que move o filtro para o banco e me protege mesmo de um esquecimento na aplicação. Pra um cliente enterprise que exigisse isolamento físico, eu migraria aquele tenant pra banco separado."

---

## O middleware de resolução de tenant

> Este componente foi coberto em detalhe no Módulo 3 (como exemplo de middleware). Aqui o ângulo é diferente: não *como* o middleware funciona, mas *por que ele é o coração do isolamento*.

O `TenantMiddleware` resolve o tenant uma vez por request, em ordem de prioridade (sessão → perfil do usuário → domínio), e o disponibiliza em `request.tenant`. Superusers passam sem tenant (modo global), e tenants suspensos são bloqueados ali mesmo.

O ponto para uma entrevista: **por que a resolução vive no middleware, e não em cada view?** Porque isolamento não pode depender de disciplina distribuída. Se cada view tivesse que resolver o tenant, bastaria uma esquecer para abrir uma brecha. O middleware centraliza a resolução num único ponto que cobre 100% dos requests. Ele resolve *quem* é o tenant; as views usam esse resultado para filtrar. Essa divisão — resolver no middleware, filtrar na view — é o que torna o sistema auditável.

---

## Testes de isolamento: prova, não confiança

### O que é

Testes automatizados cujo único objetivo é provar que um tenant não consegue, de nenhuma forma, acessar dados de outro. Eles não testam funcionalidade — testam *segurança*.

### Onde utilizei

No Barber, em `test_tenant_isolation.py`. Dois testes representam bem a ideia:
- **`test_listview_isolated_by_tenant`**: cria dados para o Tenant A e o Tenant B, simula um request do Tenant A, e verifica que o queryset retorna *só* a venda do A — a do B não aparece.
- **`test_detailview_cross_tenant_404`**: o Tenant A tenta acessar diretamente uma venda do Tenant B pelo ID, e o teste exige um **404** (não 403).

### Qual problema resolveu

O problema de que uma falha de isolamento é invisível até vazar em produção. Sem esses testes, um vazamento passaria despercebido no desenvolvimento e só apareceria quando um cliente visse dados de outro — o pior momento possível. Os testes transformam "eu acho que está isolado" em "está provado que está isolado", e travam regressões: se alguém adicionar uma view sem filtro, o teste quebra.

### Por que escolhi essa solução

Porque num sistema onde isolamento depende da aplicação, testá-lo é parte da implementação, não um luxo. E usei `RequestFactory` para simular os requests sem subir HTTP de verdade — injeto o tenant direto no request e chamo o `get_queryset()`/`get_object()` da view. Isso torna os testes rápidos e focados exatamente na camada que importa.

### A sutileza de segurança: 404, não 403

Este é o detalhe que impressiona. Quando o Tenant A tenta acessar um recurso do Tenant B, o sistema responde **404 (não existe)**, não **403 (proibido)**. A razão é sutil e importante: um 403 revelaria que o recurso *existe*, só que o usuário não pode vê-lo. Isso já é um vazamento de informação — o Tenant A descobriria que aquela venda existe. O 404 não revela nada: do ponto de vista do Tenant A, aquele recurso simplesmente não existe. É a resposta correta do ponto de vista de privacidade.

### Quais vantagens trouxe

- Isolamento provado, não presumido.
- Regressões travadas — uma view nova sem filtro quebra o teste.
- Testes rápidos via `RequestFactory`, sem overhead de HTTP.

### Hoje eu faria igual?

Sim, e reforçaria a cobertura: garantir que *todo* endpoint que expõe dados de tenant tenha um teste de isolamento correspondente. A fraqueza de testar isolamento view a view é que um endpoint novo pode escapar — que é, de novo, o argumento a favor de RLS como camada que não depende de lembrar de testar.

### O que um CTO provavelmente perguntaria

- Como você testa isolamento de tenant?
- Por que 404 e não 403 no acesso cross-tenant?
- O que é `RequestFactory` e por que usá-lo aqui?
- Como você garante que todos os endpoints estão cobertos?

### Como responder em uma entrevista

**Objetiva:**
> "Escrevi testes específicos de isolamento: eles criam dados de dois tenants e provam que um request do Tenant A só enxerga dados do A. Um dos testes verifica que acessar um recurso do outro tenant retorna 404. Uso `RequestFactory` pra simular o request sem subir HTTP, injetando o tenant direto."

**Aprofundada:**
> "Isolamento é segurança, então testo como segurança — provando que o vazamento é impossível, não confiando que está certo. Um detalhe que cuido é retornar 404, não 403, no acesso cross-tenant: um 403 revelaria que o recurso existe, o que já é um vazamento de informação; o 404 não revela nada. Esses testes também travam regressão — se alguém criar uma view sem o filtro de tenant, o teste quebra. A limitação é que testo view a view, então um endpoint novo pode escapar da cobertura; por isso enxergo RLS como a evolução que remove essa dependência."

---

## Como as peças se conectam (a visão de sistema)

Vale saber contar o isolamento como um sistema, não como partes soltas. O fluxo completo:

```
Request chega
   ↓
TenantMiddleware resolve o tenant (sessão → perfil → domínio)
   → grava em request.tenant   → bloqueia se o tenant estiver suspenso
   ↓
View filtra: .filter(tenant=request.tenant)   ← o isolamento acontece aqui
   ↓
ORM consulta o banco compartilhado, trazendo só as linhas daquele tenant
   ↓
Testes de isolamento garantem, em CI, que essa cadeia nunca é burlada
```

E a conexão com outros módulos: o `tenant` aparece nos **índices compostos** (Módulo 4) porque `(tenant, data)` é o padrão de filtro real, e nas **constraints** (Módulo 4) porque "um caixa aberto por tenant" é uma regra por-tenant. Multi-tenancy não é uma feature isolada — ela permeia a modelagem inteira.

---

## Checklist de domínio deste módulo

- [ ] Listar as três estratégias de multi-tenancy e o trade-off isolamento vs custo.
- [ ] Justificar shared database pela simplicidade operacional e custo, como escolha consciente.
- [ ] Explicar as cinco camadas do isolamento (Tenant model → FK → middleware → filtro → testes).
- [ ] Admitir a fraqueza (o filtro que não pode ser esquecido) e citar a mitigação (testes + RLS).
- [ ] Explicar por que 404 e não 403 no acesso cross-tenant.
- [ ] Descrever o caminho de evolução (RLS, e banco separado para enterprise).

---

## Perguntas comuns

**"Que estratégias de multi-tenancy existem?"** → Busca: se você conhece o espectro. Shared schema / separate schema / separate DB, com o trade-off isolamento vs custo.

**"Por que shared database?"** → Busca: se a escolha foi consciente. Custo e operação simples no estágio do produto; isolamento lógico rigoroso e testado.

**"Como garante que nenhuma query escapa do filtro?"** → Busca: se você conhece a fraqueza. Filtro obrigatório + testes de isolamento; e a honestidade de que a evolução é RLS.

**"Por que 404 e não 403?"** → Busca: maturidade de segurança. 403 revela que o recurso existe — já é vazamento; 404 não revela nada.

**"Como escalaria o isolamento?"** → Busca: visão de evolução. RLS como camada extra; banco separado para enterprise.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- Três estratégias: shared schema (a minha) / separate schema / separate DB. Trade-off: isolamento ↑ = custo ↑.
- Meu isolamento tem 5 camadas: model `Tenant` → FK em todo model → middleware resolve → filtro obrigatório na view → testes de isolamento.
- Isolamento é **lógico** (garantido pela aplicação) — a fraqueza é depender de não esquecer o filtro.
- Acesso cross-tenant retorna **404, não 403** (403 revelaria que o recurso existe).
- Evolução: Row-Level Security (RLS) move o filtro pro banco e remove a dependência da disciplina.

**Decisões técnicas mais importantes**
- Shared database por custo e simplicidade operacional (um deploy, um banco, migrations únicas).
- Resolução do tenant no middleware (um ponto), filtro na view — isolamento auditável.
- Testes de isolamento como parte da implementação, não extra.

**Erros que devo evitar ao responder**
- Dizer "implementei e funciona" sem citar a fraqueza e a mitigação.
- Não conhecer as alternativas (soa a quem herdou a arquitetura pronta).
- Esquecer o ângulo de segurança (LGPD, vazamento entre concorrentes).
- Não saber explicar o 404 vs 403.

**Tecnologias principais abordadas**
- Django (middleware, FK, managers, `get_queryset`), PostgreSQL (RLS como evolução), `RequestFactory` para testes, shared database multi-tenancy.

**Palavras-chave que devem aparecer naturalmente**
- tenant, isolamento lógico, shared database, tenant_id, filtro obrigatório, middleware, vazamento de dados, LGPD, 404 vs 403, Row-Level Security, teste de isolamento, RequestFactory.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ As três estratégias de multi-tenancy e por que escolhi shared database (custo + simplicidade).
- ✓ As cinco camadas do meu isolamento (Tenant → FK → middleware → filtro → testes).
- ✓ A fraqueza honesta (não esquecer o filtro) e a mitigação (testes + RLS como evolução).
- ✓ Por que acesso cross-tenant retorna 404, não 403 (não vazar existência do recurso).
- ✓ Que testo isolamento como segurança — provo o vazamento impossível, não confio que está certo.
