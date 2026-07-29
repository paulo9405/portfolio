# Módulo 4 — Banco de Dados e Performance

> Tempo de estudo: ~40–45 min
> Objetivo: defender suas decisões de banco de dados — consistência transacional, performance de queries, índices, constraints e soft delete — com exemplos concretos do Barber. Este é o módulo mais "denso de perguntas" numa entrevista backend séria.

---

## Como pensar este módulo

Banco de dados é onde um CTO descobre se você já operou um sistema real ou só estudou. A razão é simples: quase todos os problemas dolorosos de produção nascem no banco — dado que corrompe, query que trava a aplicação, corrida entre dois usuários fazendo a mesma coisa ao mesmo tempo. Quem já sentiu isso fala diferente de quem só leu.

O que o entrevistador quer descobrir aqui:
- Se você entende que o banco é a última linha de defesa da integridade dos dados.
- Se você sabe diagnosticar e resolver problemas de performance (o N+1 é o teste clássico).
- Se você conhece o trade-off de cada decisão — índice acelera leitura mas pesa na escrita, soft delete preserva histórico mas complica unicidade.

O que você precisa dominar:
- `transaction.atomic` e por que consistência não é opcional quando há dinheiro no sistema.
- N+1 e as ferramentas para resolvê-lo (`select_related` / `prefetch_related`).
- Índices: quando criar, qual tipo, e o custo.
- Constraints de banco vs validação em código.
- Soft delete e suas consequências.

Um fio condutor que vale carregar o módulo inteiro: várias dessas decisões se conectam. O `UniqueConstraint` do caixa só funciona porque tem uma `condition` que ignora registros soft-deleted. Saber amarrar esses pontos é o que faz a diferença.

---

## Transações atômicas (`transaction.atomic`)

### O que é

Um bloco onde ou *todas* as operações de banco acontecem, ou *nenhuma*. Se qualquer coisa falhar no meio, o banco desfaz tudo (rollback) e volta ao estado anterior.

### Onde utilizei

No Barber, no `cancelar_venda()`. Cancelar uma venda envolve três operações que precisam acontecer juntas: reverter o agendamento vinculado, restaurar o estoque dos produtos, e marcar a venda como deletada (soft delete). Tudo dentro de um `with transaction.atomic():`.

```python
with transaction.atomic():
    # 1. reverter agendamento
    # 2. restaurar estoque de cada produto
    # 3. soft delete da venda
```

### Qual problema resolveu

O problema de estado inconsistente. Sem a transação, imagine que o sistema reverte o agendamento, começa a restaurar o estoque e falha no meio: você fica com uma venda "meio cancelada" — estoque parcialmente restaurado, agendamento revertido, mas a venda ainda ativa. Num sistema que controla dinheiro e estoque, isso é um problema real, não teórico. Com a transação, ou o cancelamento inteiro acontece, ou nada muda.

### Por que escolhi essa solução

Porque a operação é atômica por natureza no domínio do negócio: "cancelar venda" é uma coisa só do ponto de vista do usuário, mesmo sendo três operações no banco. A transação faz o banco enxergar isso do mesmo jeito.

### Alternativas

- **Sem transação, tratando erros manualmente**: você teria que escrever código de "desfazer" para cada passo já executado quando algo falha. Frágil, verboso e fácil de errar. A transação dá isso de graça.
- **Saga pattern**: necessário quando as operações envolvem *sistemas externos* que não dá para dar rollback (um pagamento já cobrado, um e-mail já enviado). Não é o caso aqui — tudo está no mesmo banco —, então a transação simples basta. Saber quando a saga *seria* necessária é um bom ponto para mostrar.

### Quais vantagens trouxe

- Impossível ficar em estado parcial.
- Rollback automático — sem código manual de compensação.
- O usuário nunca vê uma venda "meio cancelada".

### Hoje eu faria igual?

Sim. Uma melhoria que anotei: em cenário de alta concorrência, adicionar `select_for_update()` para travar as linhas envolvidas e evitar condição de corrida entre dois cancelamentos simultâneos. No volume atual não é necessário, mas é o próximo passo natural.

### Como um CTO enxerga isso

Ele quer saber se você entende que consistência é inegociável quando há valor em jogo. A pergunta por trás é: "você já pensou no que acontece quando o código falha no meio de uma operação de várias etapas?" Quem nunca operou um sistema real tende a assumir que tudo sempre dá certo. Sua resposta prova o contrário com um exemplo onde a falha teria consequência concreta (estoque + agendamento + dinheiro).

### O que um CTO provavelmente perguntaria

- O que acontece se uma exceção ocorrer dentro do bloco `atomic()`?
- Qual a diferença entre `atomic()` como decorator e como context manager?
- O que é um deadlock e como você evitaria?
- O que o banco faz internamente num commit vs rollback?

### Como responder em uma entrevista

**Objetiva:**
> "Uso `transaction.atomic` sempre que uma operação de negócio envolve várias escritas que precisam ser tudo-ou-nada. No Barber, cancelar uma venda reverte o agendamento, restaura o estoque e faz soft delete — três operações. Se qualquer uma falha, o banco desfaz tudo automaticamente. Sem isso, eu poderia ter uma venda meio cancelada, com estoque restaurado pela metade."

**Aprofundada:**
> "A transação garante atomicidade: o banco abre um BEGIN, executa tudo, e faz COMMIT só no fim; qualquer exceção dispara ROLLBACK. Isso me poupa de escrever código de compensação manual para cada passo. Para alta concorrência, o próximo passo seria `select_for_update` para travar as linhas e evitar corrida entre dois cancelamentos. E se a operação tocasse um sistema externo não-reversível, como um pagamento já cobrado, aí a transação de banco não bastaria — seria caso de saga pattern, com passos de compensação explícitos."

---

## O problema N+1 e como resolvi (`select_related` / `prefetch_related`)

### O que é

N+1 é o problema de performance mais comum em ORM: você faz 1 query para buscar uma lista, e depois o ORM dispara 1 query adicional para *cada* item ao acessar um dado relacionado. Uma lista de 20 vendas onde você acessa o nome do barbeiro de cada uma vira 1 + 20 queries.

### Onde utilizei

Na listagem de vendas do Barber. Cada venda tem barbeiro, agendamento e cliente relacionados, além de serviços e produtos. Sem otimização, listar 20 vendas fazia por volta de 61 queries (1 + 20 barbeiros + 20 agendamentos + 20 clientes). Com `select_related` nas FKs e `prefetch_related` nas relações de muitos, caiu para poucas queries 3.

```python
Sale.objects.filter(tenant=self.request.tenant) \
    .select_related('barbeiro', 'agendamento', 'cliente_cadastrado') \
    .prefetch_related('servicos', 'produtos')
```

### Qual problema resolveu

Performance de listagem. 61 queries numa página é lento e escala mal — quanto mais vendas, mais round-trips ao banco. A otimização mantém o número de queries praticamente constante, independente de quantas vendas a página tem.

### Por que escolhi essa solução

Porque `select_related` e `prefetch_related` são as ferramentas certas para cada tipo de relação:
- **`select_related`** para ForeignKey e OneToOne — resolve com um JOIN, trazendo tudo numa query só.
- **`prefetch_related`** para ManyToMany e reverse FK — faz uma query separada com `IN (...)` e junta em memória, porque um JOIN aqui multiplicaria as linhas.

Usar o errado (prefetch numa FK, ou select_related numa relação de muitos) não resolve o N+1 ou piora. Saber qual usar é o cerne.

### Alternativas

- **Não otimizar**: aceitável só em telas de baixíssimo volume.
- **`Prefetch` object customizado**: para quando você precisa otimizar a query *de dentro* do prefetch — no Barber usei isso em `views_finance.py`, aninhando `select_related` dentro do prefetch dos serviços/produtos.

### Quais vantagens trouxe

- Queda de ~61 para poucas queries na listagem.
- Número de queries estável conforme a lista cresce.

### Hoje eu faria igual?

Sim. Complementos que anotei: `only()`/`defer()` para carregar só os campos necessários em telas pesadas, e cache (Redis) para queries muito frequentes. Mas a base — usar o método certo para cada relação — permanece.

### Como um CTO enxerga isso

O N+1 é quase um rito de passagem em entrevista backend. O CTO quer ver se você (1) reconhece o problema, (2) sabe diagnosticá-lo e (3) sabe corrigi-lo com a ferramenta certa. O detalhe que separa os candidatos é saber *por que* select_related e prefetch_related funcionam diferente — um usa JOIN, o outro faz query separada com IN. Quem só decora "use select_related" trava quando a relação é de muitos.

### O que um CTO provavelmente perguntaria

- O que é o problema N+1?
- Qual a diferença entre `select_related` e `prefetch_related`, e quando usar cada um?
- Como você descobre que tem um N+1 no código?
- O que é o `Prefetch` object?

### Como responder em uma entrevista

**Objetiva:**
> "N+1 é quando você faz uma query pra listar e o ORM dispara uma query extra por item ao acessar um relacionamento. Na listagem de vendas do Barber, isso dava por volta de 61 queries pra 20 vendas. Resolvi com `select_related` nas FKs — que vira JOIN — e `prefetch_related` nas relações de muitos — que faz uma query separada com IN. Caiu pra poucas queries."

**Aprofundada:**
> "A distinção é técnica: `select_related` faz JOIN e serve pra ForeignKey e OneToOne; `prefetch_related` faz uma segunda query com `IN` e junta em memória, e serve pra ManyToMany e reverse FK — porque um JOIN nessas relações multiplicaria as linhas. Usar o método errado não resolve. Pra diagnosticar, uso o Django Debug Toolbar em dev, que mostra a contagem de queries por request. Quando preciso otimizar a query de dentro do prefetch, uso o `Prefetch` object com um queryset customizado — fiz isso na parte financeira, aninhando select_related dentro do prefetch."

---

## Índices

### O que é

Uma estrutura auxiliar (por padrão uma B-Tree) que permite ao banco encontrar linhas sem varrer a tabela inteira. Transforma uma busca de O(n) (ler tudo) em O(log n) (busca em árvore).

### Onde utilizei

No Barber, no model `Agendamento`, com índices compostos para as queries mais frequentes — em especial `Index(fields=['tenant', 'data'])`, que otimiza a consulta mais comum do sistema: "os agendamentos de hoje desta barbearia". Também no `CashRegister`, com índice em `['tenant', '-referencia_data']`.

### Qual problema resolveu

Velocidade das queries quentes. A listagem de agendamentos do dia por tenant roda o tempo todo. Sem índice, o PostgreSQL faria full table scan — lê todas as linhas — a cada consulta. Com uma tabela grande, isso é a diferença entre milissegundos e segundos.

### Por que escolhi essa solução

Porque escolhi índices *compostos* alinhados às queries reais, não índices avulsos em cada coluna. Um índice em `(tenant, data)` serve exatamente a query que filtra por ambos, que é a que mais executo. Índice não é "quanto mais, melhor" — cada um só justifica seu custo se uma query real o usa.

### Alternativas / considerações

- **Sem índice**: só aceitável em tabelas pequenas.
- **Índice simples por coluna**: útil, mas não cobre bem uma query que filtra por dois campos juntos.
- **A ordem das colunas no índice composto importa**: `(tenant, data)` serve `WHERE tenant=X AND data=Y` e também `WHERE tenant=X` sozinho, mas *não* serve bem `WHERE data=Y` isolado. Alinhar a ordem ao padrão de acesso é a parte sutil.

### Quais vantagens trouxe

- Queries quentes rápidas mesmo com a tabela crescendo.
- Índices compostos servindo os filtros reais do multi-tenant.

### Hoje eu faria igual?

Sim, e monitoraria uso: melhorias que anotei incluem partial indexes (indexar só `status='aberto'`, por exemplo) e remover índices que nenhuma query usa — porque índice não usado só custa (mais lento pra escrever, mais espaço). O jeito de validar é `EXPLAIN ANALYZE`, que mostra se o índice está mesmo sendo usado.

### O que um CTO provavelmente perguntaria

- Quando um índice pode *prejudicar* a performance? (Escrita mais lenta, espaço; índice não usado é só custo.)
- Diferença entre índice simples e composto? A ordem das colunas importa?
- Como você valida que um índice está sendo usado? (`EXPLAIN ANALYZE`.)

### Como responder em uma entrevista

**Objetiva:**
> "Criei índices compostos alinhados às queries mais frequentes. O principal é `(tenant, data)` no agendamento, que otimiza a consulta mais comum do sistema — os agendamentos do dia de uma barbearia. Sem ele, seria full table scan a cada consulta. Valido com `EXPLAIN ANALYZE` que o índice está sendo usado."

**Aprofundada:**
> "Índice acelera leitura mas tem custo: cada INSERT/UPDATE precisa atualizar o índice também, e ele ocupa espaço. Por isso crio só os que uma query real usa, e monitoro — índice que ninguém usa é puro custo. Em índice composto, a ordem importa: `(tenant, data)` cobre filtro pelos dois campos e por `tenant` sozinho, mas não por `data` isolada. Melhorias que faria: partial index pra casos como caixa aberto, indexando só as linhas com aquele status."

---

## Constraints de banco (vs validação em código)

### O que é

Regras impostas pelo próprio banco, que ele verifica antes de gravar. Se a regra é violada, o banco rejeita com `IntegrityError`, não importa quem tentou gravar. Os dois tipos que usei: `UniqueConstraint` (unicidade, possivelmente condicional) e `CheckConstraint` (uma condição booleana).

### Onde utilizei

No Barber. Um `UniqueConstraint` condicional garante que só existe **um caixa aberto por tenant por dia**:

```python
models.UniqueConstraint(
    fields=['tenant', 'referencia_data'],
    condition=models.Q(status='aberto', deleted_at__isnull=True),
    name='unique_open_cash_per_tenant_date'
)
```

E um `CheckConstraint` no agendamento garante que `hora_fim > hora_inicio`, direto no banco.

### Qual problema resolveu

Garantias que validação em código *não consegue* dar sozinha. O caso do caixa é o exemplo perfeito: dois usuários clicam "Abrir Caixa" quase ao mesmo tempo. Ambos consultam, veem que não há caixa aberto, e ambos criam — resultado, dois caixas abertos. Validação em Python não fecha essa janela de corrida. O `UniqueConstraint` fecha, porque o banco decide atomicamente: o segundo INSERT falha.

### Por que escolhi essa solução

Porque constraint no banco é *inviolável* — vale mesmo se alguém acessar o banco por fora da aplicação, mesmo sob concorrência. Validação em código é a primeira linha (dá mensagens amigáveis, falha cedo), mas a constraint é a garantia final. Uso as duas em camadas.

Repare no detalhe que conecta com soft delete: a `condition` inclui `deleted_at__isnull=True`. Sem isso, um caixa soft-deleted contaria para a unicidade e bloquearia abrir um novo. Essa é a amarração entre os dois conceitos.

### Alternativas

- **Só validação em código**: falha sob concorrência (a race condition do caixa).
- **Trigger no banco**: mais poderosa, mas mais complexa de manter; para unicidade e checagem simples, constraint declarativa é mais limpa.

### Quais vantagens trouxe

- Regra à prova de concorrência e de acesso direto ao banco.
- Integridade garantida no nível mais baixo possível.

### Hoje eu faria igual?

Sim. Uma melhoria elegante que anotei: `ExclusionConstraint` do PostgreSQL para validar *não-sobreposição de intervalos* — que resolveria o conflito de horário de agendamento no próprio banco, em vez de na query do `clean()`. É a evolução natural daquela validação.

### Como um CTO enxerga isso

Esta é uma das perguntas mais reveladoras que existem: "validação no código ou constraint no banco?" A resposta fraca escolhe um lado. A resposta madura diz "os dois, em camadas, porque resolvem coisas diferentes" — e prova com o caso de race condition, que é onde a validação em código comprovadamente falha. Isso mostra que você entende concorrência, não só CRUD feliz.

### O que um CTO provavelmente perguntaria

- Validação no código ou constraint no banco — qual usar?
- Como uma constraint protege contra race condition que a validação em Python não protege?
- O que é constraint condicional (parcial)?
- Como você trata `IntegrityError` no Django?

### Como responder em uma entrevista

**Objetiva:**
> "Uso constraints de banco pra garantias que não podem ser burladas. O melhor exemplo é o caixa: um `UniqueConstraint` condicional garante só um caixa aberto por tenant por dia. Mesmo com dois usuários clicando 'abrir' ao mesmo tempo, o banco barra o segundo — coisa que validação em Python não faz, por causa da race condition. Uso as duas camadas: validação no código pra UX, constraint no banco pra garantia."

**Aprofundada:**
> "Validação em código falha sob concorrência: dois requests consultam, os dois veem 'não existe', os dois criam. A constraint resolve porque o banco decide atomicamente no INSERT. Um detalhe importante: a condição do meu UniqueConstraint inclui `deleted_at IS NULL`, senão um caixa soft-deleted contaria pra unicidade e travaria abrir um novo — é onde constraint e soft delete se conectam. A evolução que faria é usar `ExclusionConstraint` do Postgres pra garantir não-sobreposição de horários de agendamento direto no banco."

---

## Soft Delete

### O que é

"Deletar" um registro marcando um campo `deleted_at` com a data, em vez de removê-lo do banco. Um manager customizado filtra os deletados de todas as queries automaticamente, então eles somem da aplicação sem sumir do banco.

### Onde utilizei

No Barber, como classe base `SoftDeleteModel` que vários models herdam (Sale, Agendamento, CashRegister...). Ela sobrescreve `delete()` para marcar `deleted_at`, oferece `restore()` e `hard_delete()`, e expõe dois managers: `objects` (só não-deletados) e `all_objects` (todos, para acesso administrativo).

### Qual problema resolveu

Preservação de histórico e recuperação. Num sistema financeiro, apagar de verdade uma venda destruiria o histórico contábil e poderia quebrar integridade referencial. Soft delete permite "cancelar" mantendo o rastro para auditoria e permitindo desfazer uma exclusão acidental.

### Por que escolhi essa solução

Porque os dados do sistema têm valor de histórico — vendas, caixa, agendamentos compõem o registro financeiro da barbearia. A escolha de fazer isso numa classe base (com manager custom) garante que *todo* model que herda ganha o comportamento e que nenhuma query esquece de filtrar os deletados.

### Alternativas

- **Hard delete (deletar de verdade)**: mais simples, e correto para dados sem valor histórico. Mas perde auditoria e recuperação.
- **Archive table**: mover deletados para uma tabela separada. Mantém a tabela principal enxuta, ao custo de complexidade. Anotei como possível evolução.

### Quais vantagens trouxe

- Histórico preservado para auditoria.
- Recuperação de exclusões acidentais (`restore()`).
- Managers cuidam do filtro automaticamente — nenhuma view precisa lembrar.

### Hoje eu faria igual?

Sim, para dados com valor histórico. Mas com plena consciência dos custos: soft delete complica unicidade (resolvido pondo `deleted_at__isnull=True` nas constraints), a tabela cresce indefinidamente (melhoria: hard delete agendado após X dias), e cascata precisa de cuidado — deletar um pai não solta os filhos automaticamente. Reconhecer esses custos é parte de defender a escolha.

### Como um CTO enxerga isso

Ele quer ver se você entende as *consequências* de soft delete, não só o conceito. A pergunta-armadilha favorita é: "como soft delete interage com unique constraints?" — porque é aqui que quem só leu sobre o padrão tropeça. Você tem a resposta pronta e vivida: a condição `deleted_at IS NULL` na constraint. Isso prova que você implementou de verdade e sentiu o problema.

### O que um CTO provavelmente perguntaria

- O que é soft delete e quando você usaria (e quando não)?
- Como garantir que nenhuma query retorne registros deletados?
- Como soft delete interage com unique constraints?
- Quais os custos/problemas do soft delete?

### Como responder em uma entrevista

**Objetiva:**
> "Implementei soft delete como classe base: o `delete()` marca um `deleted_at` em vez de remover, e um manager customizado filtra os deletados de todas as queries. Uso pra dados com valor histórico, como vendas e caixa — permite auditoria e desfazer exclusão acidental. Um manager separado, `all_objects`, dá acesso a tudo quando preciso."

**Aprofundada:**
> "O manager custom adiciona `WHERE deleted_at IS NULL` automaticamente, então nenhuma view precisa lembrar de filtrar. Mas soft delete tem custos que eu assumo conscientemente: complica unicidade — por isso minhas constraints têm `deleted_at__isnull=True` na condição, senão um registro deletado bloquearia criar outro; a tabela cresce sem parar, então o passo seguinte seria hard delete agendado depois de um período; e cascata precisa de cuidado, porque deletar o pai não solta os filhos sozinho. Pra dados sem valor histórico, eu usaria hard delete mesmo — soft delete não é regra, é escolha por causa da auditoria."

---

## Checklist de domínio deste módulo

- [ ] Explicar `transaction.atomic` com o exemplo do cancelamento (3 operações tudo-ou-nada) e quando usar saga.
- [ ] Explicar o N+1 e a diferença técnica entre `select_related` (JOIN) e `prefetch_related` (IN).
- [ ] Justificar índices compostos alinhados às queries reais, com o trade-off leitura vs escrita.
- [ ] Defender constraint de banco pelo caso de race condition do caixa.
- [ ] Explicar soft delete E seus custos, com destaque para a interação com unique constraints.
- [ ] Amarrar constraint + soft delete (a condição `deleted_at IS NULL`).

---

## Perguntas comuns

**"O que é `transaction.atomic` e quando usar?"** → Busca: se você pensa em falha no meio da operação. Exemplo do cancelamento; rollback automático; saga só para sistemas externos.

**"Explica o N+1."** → Busca: diagnóstico + correção com a ferramenta certa. 61→poucas queries; select_related (JOIN) vs prefetch_related (IN).

**"Quando um índice atrapalha?"** → Busca: se você conhece o custo. Escrita mais lenta, espaço, índice não usado é só custo.

**"Validação no código ou no banco?"** → Busca: se você entende concorrência. Os dois, em camadas; constraint fecha a race condition que o Python não fecha.

**"Como soft delete interage com unique constraint?"** → Busca: se você implementou de verdade. Condição `deleted_at IS NULL` na constraint.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- `transaction.atomic` = tudo-ou-nada. Cancelar venda = reverter agendamento + restaurar estoque + soft delete, numa transação.
- N+1: 61 → poucas queries. `select_related` = JOIN (FK/OneToOne); `prefetch_related` = query com IN (M2M/reverse FK).
- Índice composto `(tenant, data)` para a query quente; ordem das colunas importa; valida com `EXPLAIN ANALYZE`.
- `UniqueConstraint` condicional resolve race condition do caixa que validação em Python não resolve.
- Soft delete = marca `deleted_at`; manager filtra automático; constraint precisa de `deleted_at IS NULL`.

**Decisões técnicas mais importantes**
- Consistência via transação porque há dinheiro e estoque em jogo.
- Método certo por tipo de relação (não confundir select_related com prefetch_related).
- Constraint no banco como garantia final, validação no código como primeira linha.
- Soft delete por valor histórico/auditoria — com consciência do custo.

**Erros que devo evitar ao responder**
- Escolher só um lado em "código vs banco" — a resposta é "os dois, em camadas".
- Dizer "quanto mais índice, melhor" — cada índice custa na escrita.
- Explicar N+1 sem saber por que select_related e prefetch_related diferem.
- Vender soft delete sem citar o custo (unicidade, crescimento da tabela, cascata).

**Tecnologias principais abordadas**
- PostgreSQL, Django ORM (`transaction.atomic`, `select_related`, `prefetch_related`, `Prefetch`), índices compostos, `UniqueConstraint`/`CheckConstraint`, managers customizados.

**Palavras-chave que devem aparecer naturalmente**
- atomicidade, rollback, tudo-ou-nada, N+1, JOIN, query com IN, full table scan, índice composto, EXPLAIN ANALYZE, race condition, IntegrityError, constraint condicional, soft delete, auditoria, `deleted_at`.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Por que cancelar venda usa `transaction.atomic` (3 operações tudo-ou-nada).
- ✓ O N+1 e como resolvi (61→poucas queries), com a diferença select_related vs prefetch_related.
- ✓ Por que índices compostos alinhados às queries quentes, e o trade-off leitura/escrita.
- ✓ Por que constraint de banco resolve a race condition do caixa que o código não resolve.
- ✓ Soft delete para histórico — e que sei seus custos, incluindo a interação com unicidade.
