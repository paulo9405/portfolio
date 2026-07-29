# Módulo 7 — APIs, Integrações e Automação

> Tempo de estudo: ~45 min (o módulo mais amplo — pode ser dividido em duas sessões)
> Objetivo: defender três frentes que mostram amplitude — construção de APIs REST com DRF, automação resiliente com Playwright (MOST), e integração de IA com RAG (Barber). O fio comum: são todos "código que conversa com o mundo externo", e cada um exige defender decisões diferentes.

---

## Como pensar este módulo

Este módulo é onde você mostra que não é um dev de uma coisa só. Três frentes bem distintas: uma API REST clássica, um robô de automação assíncrono, e uma integração com LLM. Um CTO que vê isso no seu currículo vai querer confirmar que você entende cada uma de verdade — não que apenas encostou nelas.

Como é amplo, vale estudá-lo em duas sessões: **Bloco A (DRF)** numa, **Blocos B e C (MOST + RAG)** noutra.

O que o entrevistador quer descobrir, em cada frente:
- **DRF**: você sabe construir uma API que não vaza dados e que segue convenções REST?
- **Automação**: você sabe lidar com um mundo externo que não coopera (um site instável)?
- **RAG**: você entende o que está fazendo, ou só plugou uma API de IA e chamou de "inteligência"?

O maior valor deste módulo está em duas coisas: o **tratamento de erros em camadas** do MOST (que prova pensamento defensivo) e a **decisão de construir RAG do zero, sem framework** (que prova entendimento real, não uso de caixa-preta).

---

# Bloco A — APIs REST com Django REST Framework

## Serializers (validação e contrato)

### O que é

Serializers convertem entre objetos Django e JSON, validando a entrada e controlando o que sai. São o contrato da API: definem o que entra, o que é validado, e o que é exposto.

### Onde utilizei

No Barber, o `SaleSerializer`. Ele faz três coisas que valem destacar: nested write (cria a venda e seus itens de serviço juntos, dentro do `create()`), campos calculados (`SerializerMethodField` para o nome formatado do cliente), e validação cross-field que checa o tenant — garantindo que o barbeiro informado pertence ao tenant do request.

### Qual problema resolveu

Controle do que a API aceita e do que expõe. Sem serializer, eu exporia campos internos (como `deleted_at` ou o `tenant_id`) e teria validação espalhada. O serializer centraliza: valida a entrada num lugar, e a saída expõe só o que deve.

### Por que escolhi essa solução

Usei `ModelSerializer` para mapear os campos do model automaticamente, mas customizei o `create()` para o nested write — criar a venda e os itens numa operação. E acesso o tenant via `self.context['request'].tenant` dentro da validação, para reforçar o isolamento multi-tenant também na camada de API.

### Alternativas

- **`Serializer` puro** (declarar cada campo à mão): mais controle, mais verboso. `ModelSerializer` economiza boilerplate quando os campos espelham o model.
- **Validar na view**: espalha a lógica e não dá o contrato/documentação de graça.

### Hoje eu faria igual?

Sim. Melhorias anotadas: `bulk_create` para os itens quando houver muitos (performance) e versionamento do serializer se a API precisar evoluir sem quebrar clientes.

### O que um CTO provavelmente perguntaria

- Diferença entre `Serializer` e `ModelSerializer`?
- Como você faz nested write (criar objeto e filhos juntos)?
- Diferença entre `validate()` e `validate_<campo>()`?
- Como o serializer acessa o request?

### Como responder em uma entrevista

**Objetiva:**
> "Uso `ModelSerializer` pra mapear os campos do model, mas customizo o `create()` quando preciso de nested write — no Barber, criar a venda e os itens de serviço numa operação só. Uso `SerializerMethodField` pra campos calculados, e acesso o tenant pelo `context['request']` pra validar que o barbeiro pertence ao tenant certo. O serializer é o contrato: valida a entrada e controla o que sai, então não vazo campo interno."

---

## ViewSets, Routers e Custom Actions

### O que é

`ViewSet` agrupa todas as operações de um recurso (list, create, retrieve, update, delete) numa classe. O `Router` gera as URLs REST automaticamente. E `@action` adiciona operações que fogem do CRUD padrão.

### Onde utilizei

No Barber, o `SaleViewSet` (um `ModelViewSet`) com duas custom actions: `POST /vendas/{id}/cancelar/` (que chama o serviço `cancelar_venda`) e `GET /vendas/resumo_dia/` (agregação do dia). O `get_queryset` filtra por tenant, e o `perform_create` seta o tenant automaticamente ao criar.

### Qual problema resolveu

CRUD completo sem escrever URL por URL nem duplicar código entre views parecidas. O router segue as convenções REST, então as URLs ficam consistentes. E as custom actions me deixam expor operações de negócio (cancelar, resumo) dentro do mesmo recurso, sem criar views soltas.

### Por que escolhi essa solução

Porque para um recurso com CRUD + algumas operações específicas, o `ModelViewSet` + `@action` é o formato mais enxuto. O detalhe importante: `detail=True` é para actions que operam sobre um item (precisam de ID, como cancelar), e `detail=False` para actions sobre a coleção (como o resumo do dia). Saber essa distinção é o que a pergunta costuma testar.

### Alternativas

- **`APIView` / views separadas**: mais controle e clareza para lógica única e não-CRUD. Uso quando o recurso não se encaixa no padrão do ViewSet.

### Hoje eu faria igual?

Sim. Melhorias anotadas: throttling por tenant (rate limit na API) e cursor pagination para datasets grandes.

### O que um CTO provavelmente perguntaria

- Diferença entre `APIView`, `ViewSet` e `GenericViewSet`?
- O que o Router gera automaticamente?
- `detail=True` vs `detail=False`?
- Quando usar ViewSet vs views separadas?

### Como responder em uma entrevista

**Objetiva:**
> "Uso `ModelViewSet` pra ter o CRUD completo numa classe, e o Router gera as URLs REST automaticamente. Pra operações que fogem do CRUD, uso `@action` — no Barber tenho `/vendas/{id}/cancelar/` com `detail=True`, porque opera sobre uma venda específica, e `/vendas/resumo_dia/` com `detail=False`, porque é sobre a coleção. O `get_queryset` filtra por tenant e o `perform_create` seta o tenant automaticamente."

---

## Permissions

### O que é

Camada do DRF que decide se uma requisição pode acessar um recurso, avaliada antes da view executar.

### Onde utilizei

No Barber, `permission_classes = [IsAuthenticated]` nos ViewSets garante que só usuários autenticados acessam a API. Combinado com o filtro de tenant no `get_queryset`, isso dá duas camadas: autenticação (quem é você) + isolamento (você só vê o seu tenant).

### Qual problema resolveu

Impedir acesso não autenticado e, junto com o filtro de tenant, garantir que a API respeita o mesmo isolamento das views web. A API não pode ser uma porta dos fundos que escapa do multi-tenant.

### Por que escolhi essa solução

Porque permission é o lugar certo para autenticação/autorização no DRF — roda antes da view, de forma declarativa. Separo os dois conceitos: **authentication** (verificar identidade) e **authorization/permission** (verificar o que essa identidade pode fazer).

### O que um CTO provavelmente perguntaria

- Diferença entre authentication e authorization?
- Como criar uma permission customizada?
- Onde a permission roda no ciclo do request?

### Como responder em uma entrevista

**Objetiva:**
> "Uso `IsAuthenticated` nos ViewSets pra barrar acesso não autenticado, e isso se combina com o filtro de tenant no queryset — autenticação diz quem você é, o filtro garante que você só vê o seu tenant. A API tem que respeitar o mesmo isolamento das views web, senão vira uma porta dos fundos."

---

# Bloco B — Automação e Web Scraping (MOST)

> Contexto: o MOST é um robô que consulta um portal público. O que o torna interessante numa entrevista não é o scraping em si — é lidar com um mundo externo que não coopera: um site instável, com layout imprevisível e comportamento diferente em produção. As decisões aqui são sobre resiliência.

## Playwright e navegação resiliente

### O que é

Playwright é uma ferramenta de automação de navegador. No MOST, ele abre o Chromium em headless, navega no portal, preenche o formulário, extrai os dados e tira screenshot como evidência.

### Onde utilizei e as decisões que valem defender

**Contexto isolado por requisição** (`browser.new_context()`): cada requisição cria seu próprio contexto de navegação — cookies, sessão e histórico separados, como uma janela anônima. Isso permite execuções simultâneas sem uma requisição contaminar a outra. Sem isso, dois robôs no mesmo navegador poderiam sobrescrever cookies um do outro ou retornar dados misturados.

**`try/finally` para nunca vazar navegador**: toda a navegação está num `try`, com `context.close()` e `browser.close()` no `finally`. Se qualquer passo falhar no meio, o `finally` fecha o navegador mesmo assim. Sem isso, um erro deixaria o navegador aberto na memória — e com várias requisições, isso vaza memória até derrubar o servidor. Detalhe fino que eu sei explicar: o `finally` roda até quando há um `return` no meio do `try` — o Python "agenda" o retorno, executa o `finally`, e só então devolve.

**Espera correta, não `sleep` fixo**: em vez de `time.sleep()`, uso as esperas do Playwright — esperar um seletor aparecer, ou um estado de carregamento. Isso é mais robusto: reage ao que a página faz, não a um chute de tempo.

### Qual problema resolveu

Automatizar consultas num portal instável de forma que aguente concorrência e falhas sem quebrar. Os três pontos acima — contexto isolado, cleanup garantido, espera reativa — são o que separa um script frágil de um serviço confiável.

### A lição de produção (o `networkidle`)

Localmente, eu esperava a rede ficar ociosa (`networkidle`). Em produção travava para sempre, porque o portal tem analytics rodando em background sem parar — a rede nunca ficava ociosa. Troquei por esperar o carregamento do DOM + um seletor específico. É o exemplo perfeito de decisão de resiliência aprendida no ambiente real. (Detalhado no Módulo 6.)

### O que um CTO provavelmente perguntaria

- Por que contexto isolado por requisição?
- Por que o cleanup fica no `finally`?
- Por que não usar `sleep` fixo entre ações?
- Como você lida com um site que muda de comportamento?

### Como responder em uma entrevista

**Objetiva:**
> "Cada requisição no MOST cria um contexto de navegação isolado — como uma aba anônima própria — pra suportar execuções simultâneas sem uma contaminar a outra. Toda a navegação fica num `try/finally`, então o navegador é fechado mesmo se algo falha no meio, senão vazaria memória. E em vez de `sleep` fixo, uso as esperas do Playwright, que reagem ao que a página faz. Isso torna o robô resiliente à instabilidade do portal."

---

## Tratamento de erros em camadas (o ponto alto do MOST)

### O que é

Uma estratégia de tratamento de erros em três categorias, garantindo que a API **nunca** quebre com um 500 sem resposta estruturada — sempre devolve um JSON, seja de sucesso ou de erro.

### Onde utilizei e as três camadas

**Categoria A — erros esperados do portal**: quando o portal mostra "0 resultados", detecto e retorno a mensagem correta. Aqui houve uma sutileza real: o portal usa "0 resultados" para *qualquer* busca sem resultado, seja CPF ou Nome, mas o desafio exigia mensagens diferentes. Resolvi usando o `tipo_busca` como critério — se a busca era por Nome, retorno a mensagem de Nome; se CPF, a de CPF.

**Categoria B — timeout sem resultado**: se o portal não mostra "0 resultados" mas também não aparece nenhum resultado clicável no tempo esperado, retorno erro como fallback.

**Categoria C — erros inesperados**: um `except Exception` no fim captura qualquer coisa não prevista e devolve um JSON de erro. É a rede de segurança que garante que a API nunca responde 500 cru.

E o `finally` fecha o navegador em todos os três casos — sucesso, erro esperado ou exceção.

### Qual problema resolveu

Uma API que consome um sistema externo instável precisa ser previsível para *quem a consome*. Se o portal falha de um jeito estranho, o cliente da minha API não pode receber um 500 sem explicação. As três camadas garantem que toda saída é um JSON com `status` e, quando é erro, uma `mensagem_erro` clara.

### Por que escolhi essa solução

Porque erros de um scraper têm naturezas diferentes — o portal dizendo "não achei" é diferente de uma exceção no meu código — e tratá-los na mesma vala perderia informação. Separar em categorias me deixa devolver a mensagem certa para cada situação, e o `except Exception` final garante que nada escapa.

### A lição de debugging (o falso positivo)

O seletor de texto do Playwright busca por substring, então "10.000 resultados" continha "0 resultados" e o robô achava que não havia resultado. Descobri **salvando um screenshot de debug** que mostrava 10.000 resultados enquanto a API retornava erro. Corrigi usando o texto completo. A lição: instrumentar (o screenshot) para enxergar o que o robô vê.

### O que um CTO provavelmente perguntaria

- Como você garante que a API nunca retorna 500 sem tratamento?
- Como você diferencia um erro do sistema externo de um erro do seu código?
- Como você garante que o recurso (navegador) é liberado mesmo com erro?

### Como responder em uma entrevista

**Objetiva:**
> "O tratamento de erros do MOST tem três camadas. A primeira trata erros esperados do portal, como '0 resultados' — e aí uso o tipo de busca pra devolver a mensagem certa, porque o portal usa o mesmo texto pra CPF e Nome. A segunda é um timeout sem resultado. A terceira é um `except Exception` que captura qualquer coisa inesperada e ainda devolve um JSON de erro — a API nunca responde 500 cru. E o `finally` fecha o navegador em todos os casos."

**Aprofundada:**
> "A ideia é que quem consome minha API tenha uma resposta previsível mesmo quando o portal se comporta mal. Erros têm naturezas diferentes — 'o portal não achou' não é o mesmo que 'meu código quebrou' —, então separo em categorias pra devolver a informação certa. Um bug que ilustra o cuidado: o Playwright busca texto por substring, e '10.000 resultados' contém '0 resultados', então o robô achava que não havia resultado. Descobri salvando um screenshot de debug. Corrigi comparando com o texto completo. Instrumentar pra ver o que o robô vê foi o que resolveu."

---

# Bloco C — Integração de IA com RAG (Barber)

> Contexto: o assistente do Barber responde perguntas sobre o sistema com base no manual oficial. A decisão que define este bloco: implementei o RAG **do zero, sem framework** (sem LangChain). Isso é o que torna a conversa valiosa — prova que entendo cada peça, em vez de plugar uma caixa-preta.

## O que é RAG e por que usei

### O que é

RAG (Retrieval-Augmented Generation) é uma técnica onde, antes de o LLM responder, você **busca** trechos relevantes de uma base de conhecimento e os injeta como contexto. O LLM responde baseado nesse contexto, não só no que aprendeu no treino.

### Onde utilizei

No Barber, para o chatbot de ajuda. O usuário pergunta "como agendar um horário?", o sistema busca os trechos mais relevantes do manual e o Claude responde com base neles.

### Qual problema resolveu

Alucinação. Sem RAG, o LLM inventaria funcionalidades que o sistema não tem. Com RAG, ele responde só com base no manual real — se a informação não está lá, ele não inventa. Para um assistente de produto, isso é a diferença entre útil e perigoso.

### Por que RAG e não fine-tuning

Esta é a pergunta clássica. Fine-tuning treina o modelo com seus dados — caro, lento de atualizar, e o modelo ainda pode alucinar. RAG é mais barato, atualiza na hora (muda o manual, muda a resposta, sem re-treinar) e é rastreável (dá para mostrar de qual trecho veio a resposta). Para uma base que muda e onde a precisão importa, RAG é a escolha certa.

### O pipeline (as peças que eu construí)

1. **Chunking semântico**: quebro o manual em pedaços de ~800 caracteres, respeitando a hierarquia (seção > subseção) e com overlap para não perder contexto nas bordas. Não corto no meio de frase.
2. **Embeddings**: cada chunk vira um vetor que representa seu significado. Uso o mesmo modelo para os chunks e para a pergunta, senão a comparação não faz sentido.
3. **FAISS (vector store)**: indexo os vetores no FAISS para busca por similaridade rápida. Uso inner product com vetores normalizados, que equivale a cosine similarity.
4. **Retrieval**: na pergunta, gero o embedding dela, busco os top-5 chunks mais similares e monto o contexto (limitado a um teto de caracteres para caber na janela do LLM).
5. **Geração com anti-alucinação**: o prompt tem regras rígidas — "responda APENAS com base no contexto". Se não está no manual, o modelo não inventa.

### Por que busca vetorial e não por keyword

Porque keyword não pega sinônimo. O usuário pergunta "marcar horário", o manual diz "agendar" — busca literal não conecta. Embeddings capturam significado, então "marcar horário" encontra "agendar" porque os vetores são próximos.

### Por que FAISS

Busca linear (comparar a query com cada chunk) é O(n) — lenta conforme a base cresce. O FAISS indexa para busca eficiente. É local e sem custo de serviço, o que para o volume do manual é suficiente. Alternativas como Pinecone ou Weaviate seriam para escala muito maior.

### Hoje eu faria igual?

Sim, e a decisão de não usar framework foi consciente — queria controle e menos overhead. Melhorias que mapeei: hybrid search (combinar vetorial com keyword/BM25), re-ranking com cross-encoder, e um pipeline de avaliação medindo recall@k. Mas o núcleo — chunking, embeddings, FAISS, anti-alucinação — permanece.

### Como um CTO enxerga isso

Se ele trabalha com IA, ele quer saber se você entende o que está por baixo ou se só chamou uma API. Construir o RAG do zero e saber explicar cada peça (por que chunking com overlap, por que cosine similarity, por que o mesmo modelo de embedding para query e chunks) prova entendimento real. E mencionar as regras anti-alucinação mostra que você pensou no risco principal de LLM em produto. A honestidade sobre as melhorias (hybrid search, re-ranking) mostra que você conhece o estado da arte, mesmo sem ter implementado tudo.

### O que um CTO provavelmente perguntaria

- O que é RAG e por que usar em vez de fine-tuning?
- Por que busca vetorial em vez de keyword?
- Por que FAISS? Quando usaria uma alternativa?
- Como você evita que o LLM alucine?
- Como você mediria a qualidade das respostas?

### Como responder em uma entrevista

**Objetiva:**
> "Implementei um RAG do zero pro assistente do Barber, sem framework, pra ter controle. O manual é quebrado em chunks de ~800 caracteres com overlap, viram embeddings indexados no FAISS. Quando o usuário pergunta, gero o embedding da pergunta, busco os 5 trechos mais similares e mando como contexto pro Claude, com a regra de responder só com base nisso. Evita alucinação, porque o modelo não inventa o que não está no manual."

**Aprofundada:**
> "Escolhi RAG em vez de fine-tuning porque é mais barato, atualiza na hora — muda o manual, muda a resposta, sem re-treinar — e é rastreável. Uso busca vetorial porque keyword não pega sinônimo: 'marcar horário' precisa encontrar 'agendar', e embeddings capturam esse significado. O FAISS resolve a busca eficiente sem custo de serviço, o que basta pro volume do manual. O ponto mais importante é o anti-alucinação no prompt: 'responda apenas com base no contexto'. As evoluções seriam hybrid search combinando vetorial com BM25, re-ranking com cross-encoder, e um pipeline medindo recall@k."

---

## Checklist de domínio deste módulo

- [ ] DRF: explicar serializer como contrato, ViewSet + Router + `@action` (detail True/False), e permission (authn vs authz).
- [ ] MOST: justificar contexto isolado, cleanup no `finally`, e espera reativa vs sleep.
- [ ] MOST: explicar as três camadas de erro e por que a API nunca retorna 500 cru.
- [ ] RAG: explicar o pipeline (chunking → embeddings → FAISS → retrieval → anti-alucinação).
- [ ] RAG: defender RAG vs fine-tuning, e busca vetorial vs keyword.
- [ ] Contar pelo menos um bug de produção do MOST com causa e solução.

---

## Perguntas comuns

**"Serializer vs ModelSerializer?"** → Busca: se você sabe quando cada um. ModelSerializer pra campos que espelham o model; Serializer puro pra controle total.

**"detail=True ou False?"** → Busca: se você entende o Router. True opera sobre um item (precisa de ID), False sobre a coleção.

**"Como a API não retorna 500?"** → Busca: pensamento defensivo. Três camadas de erro + `except Exception` final, sempre JSON.

**"RAG ou fine-tuning?"** → Busca: se você entende o trade-off. RAG: barato, atualiza na hora, rastreável, anti-alucinação.

**"Por que busca vetorial?"** → Busca: se você entende embeddings. Keyword não pega sinônimo; vetor captura significado.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- **DRF**: serializer = contrato (valida entrada, controla saída, nested write no `create`); `ModelViewSet` + Router = CRUD e URLs REST; `@action` detail=True (item) vs False (coleção); `IsAuthenticated` + filtro de tenant = duas camadas.
- **MOST**: contexto isolado por request; `try/finally` fecha o navegador sempre (senão vaza memória); espera reativa, não sleep; erros em 3 camadas → nunca 500 cru.
- **RAG**: chunking (~800 chars, overlap, respeita hierarquia) → embeddings (mesmo modelo pra query e chunk) → FAISS (cosine) → top-5 → contexto → prompt anti-alucinação.

**Decisões técnicas mais importantes**
- Serializer acessa o tenant pelo context pra reforçar isolamento na API.
- Erros em camadas porque "portal não achou" ≠ "meu código quebrou".
- RAG do zero, sem framework, por controle. RAG > fine-tuning (barato, atualiza na hora, rastreável).
- Busca vetorial porque keyword não pega sinônimo.

**Erros que devo evitar ao responder**
- Descrever RAG como "usei uma API de IA" — a força está em ter construído cada peça.
- Não saber o detail=True/False no ViewSet.
- Esquecer que a API precisa respeitar o mesmo isolamento multi-tenant.
- Falar de scraping sem citar resiliência (contexto isolado, cleanup, espera reativa).

**Tecnologias principais abordadas**
- DRF (serializers, ModelViewSet, Router, `@action`, permissions), Playwright (headless, contexto, esperas), FastAPI/Pydantic (Bloco B conecta com Módulo 3), RAG (chunking, embeddings, FAISS, prompt engineering), Claude/LLM API.

**Palavras-chave que devem aparecer naturalmente**
- serializer, contrato de API, nested write, ViewSet, Router, custom action, detail=True/False, IsAuthenticated, contexto isolado, try/finally, cleanup, espera reativa, erros em camadas, RAG, chunking, embedding, FAISS, cosine similarity, alucinação, hybrid search.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Serializer como contrato + ViewSet/Router para CRUD, respeitando o isolamento de tenant na API.
- ✓ Como o MOST é resiliente: contexto isolado, cleanup garantido no `finally`, espera reativa.
- ✓ As três camadas de erro do MOST — a API nunca retorna 500 cru.
- ✓ O pipeline RAG completo (chunking → embeddings → FAISS → anti-alucinação), construído do zero.
- ✓ RAG vs fine-tuning e busca vetorial vs keyword — com o raciocínio de cada escolha.
