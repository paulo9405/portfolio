# Módulo 8 — Construção de Produto e Banco de Perguntas

> Tempo de estudo: ~45 min
> Objetivo: fechar o playbook com duas coisas. Primeiro, saber contar como você transforma um problema real em produto que funciona — a narrativa que mais distingue você de quem só resolve tarefas. Segundo, um banco de perguntas por tema, atravessando todos os módulos, para você simular a entrevista inteira.

---

## Como pensar este módulo

Os sete módulos anteriores prepararam você para perguntas técnicas específicas. Este fecha por cima, com dois ângulos que o técnico puro não cobre:

**Produto.** Boa parte das entrevistas — principalmente em startups e times de produto — quer saber se você entende *por que* está construindo algo, não só *como*. Um dev que só executa recebe a tarefa pronta. Um dev que pensa em produto entende o problema do usuário, prioriza, lança, ouve feedback e melhora. Você tem essa história de verdade, com o Barber e o Nícia Track, e a maioria dos candidatos júnior não tem.

**Simulação.** Conhecer as respostas isoladamente é diferente de sustentá-las numa sequência de perguntas. O banco no fim serve para você treinar a entrevista completa, pulando entre temas como um entrevistador faria.

---

# Parte 1 — Construção de Produto

## Por que produto importa numa entrevista técnica

O que o entrevistador quer descobrir quando pergunta sobre seus projetos do ângulo de produto:
- Você entende o **problema** que resolveu, ou só a solução técnica?
- Você sabe **priorizar** — fazer o que importa primeiro, em vez de tudo de uma vez?
- Você **lança e itera**, ou fica polindo para sempre sem entregar?
- Você ouve o **usuário**?

O que você precisa dominar: contar cada projeto como uma jornada de produto — problema → construção → lançamento → feedback → evolução —, não como uma lista de features.

---

## Barber Cashflow: de problema real a produto em produção

### O problema (de onde veio)

O Barber não nasceu de uma ideia abstrata. Nasceu de um problema concreto de uma barbearia real: controle de agendamentos, vendas, comissões e caixa feitos de forma manual ou dispersa. O ponto forte da sua narrativa é este — **você começou por um problema de alguém**, não por "quero fazer um SaaS".

### A virada: de sistema único a SaaS (a melhor história do playbook)

Esta é, provavelmente, a história mais forte que você tem para contar numa entrevista — e é totalmente verdadeira. O Barber **começou para atender uma única barbearia**. No meio do desenvolvimento, você percebeu que a arquitetura poderia atender várias empresas e decidiu transformá-lo num SaaS.

Por que essa história é tão boa: ela mostra o momento exato em que você **deixou de pensar como programador e passou a pensar como dono de produto**. A decisão de virar SaaS não foi uma escolha de código — foi uma escolha de produto que trouxe, de uma vez, um monte de problemas novos que não existiam antes:

- **Isolamento de dados**: cada barbearia precisava ver só os próprios dados (virou o multi-tenant do Módulo 5).
- **Segurança e LGPD**: vazamento entre clientes deixou de ser um bug e virou um risco legal e contratual.
- **Deploy sem quebrar produção**: já havia um cliente usando o sistema *todo dia*, então qualquer erro em produção teria impacto direto na operação da barbearia (a estratégia de deploy seguro está no Módulo 6).
- **Evolução contínua**: como fazer o sistema crescer com segurança conforme novos clientes entrassem.

O que amarra tudo é a frase que você mesmo formulou: *"foi nesse momento que deixei de enxergar o software apenas como código e passei a enxergá-lo como um produto que precisa continuar funcionando enquanto evolui."* Essa é a frase de um profissional, não de alguém que só faz tarefas.

### A construção (as decisões de produto)

A decisão de produto mais importante foi a virada multi-tenant no meio do caminho. Isso não é detalhe técnico — é uma aposta de produto: você reconheceu que a arquitetura comportava mais do que o escopo inicial e agiu. Essa escolha moldou toda a arquitetura (Módulo 5).

Outras decisões de produto que valem contar: soft delete para preservar histórico financeiro (o usuário pode "cancelar" sem perder o registro contábil), validação de conflito de horário (o produto impede o barbeiro de marcar dois clientes no mesmo horário), e o assistente de IA (o usuário tira dúvidas sobre o sistema em linguagem natural, sem ler manual).

### O lançamento e o feedback

O Barber está em produção, com uso real. Isso muda a natureza da conversa: você não fala de um projeto hipotético, fala de um sistema que alguém usa no dia a dia e do qual depende. Cada bug tem consequência, cada decisão foi testada pelo uso.

### A evolução

O produto cresceu por versões (chegou à v3.1 com PWA). A funcionalidade de IA/RAG foi uma evolução, não estava no dia um. Isso conta uma história de produto que amadurece — você entrega o núcleo, e adiciona com base no que o uso revela.

### Como contar isso em uma entrevista

**Objetiva:**
> "O Barber começou de um problema real de uma barbearia — controle de agendamento, vendas e comissões. No meio do desenvolvimento, percebi que a arquitetura dava pra atender várias barbearias e decidi transformar em SaaS. Essa virada mudou tudo: passei a ter que pensar em isolamento de dados, LGPD, e como subir atualizações sem quebrar a operação de um cliente que já usava o sistema todo dia. Foi aí que deixei de ver o software só como código e passei a ver como um produto que precisa continuar funcionando enquanto evolui."

**Aprofundada (quando puxarem a virada SaaS):**
> "Quando decidi virar SaaS, veio uma lista de problemas novos de uma vez. Isolamento: cada barbearia só pode ver os próprios dados — resolvi com multi-tenant, filtro obrigatório por tenant e testes que provam o isolamento. Segurança e LGPD: vazamento entre clientes deixou de ser bug e virou risco legal. E o mais delicado, deploy: já tinha um cliente usando todo dia, então erro em produção parava a barbearia. Pra isso montei um processo — desenvolvia e testava local, validava num ambiente de homologação o mais próximo possível da produção, e só então subia. Features grandes eu subia no fim de semana, com a barbearia fechada, pra ter tempo de corrigir sem impacto. E mantinha contato constante com o cliente, avisando de atualizações e possíveis indisponibilidades. Essa experiência foi meu primeiro contato com o que vai além de programar: arquitetura, segurança, gestão de risco e comunicação."

---

## Nícia Track: produto com propósito e a decisão de esperar

### O problema

Uma plataforma de estudo para um concurso específico, com necessidade real e usuária real — sua namorada, a Nícia, que vai prestar o concurso. O problema era claro: organizar a preparação — questões por disciplina, simulados, acompanhamento de desempenho, revisão de erros.

Um detalhe que fortalece muito a história: você não começou pelo código, começou pelo **domínio do problema**. Pesquisou o edital do concurso, baixou os materiais, e organizou o conteúdo por matéria específica antes de construir o sistema em cima disso. Isso é o que separa um desenvolvedor que "faz um app de questões" de alguém que entende o problema que está resolvendo. Você fez a curadoria que dá sentido ao produto — sem o conteúdo certo, a plataforma seria uma casca vazia.

### A construção e as decisões de produto

Features pensadas para o comportamento de quem estuda: streak e metas diárias (engajamento), simulados com distribuição proporcional (fidelidade à prova real), caderno de erros com revisão (aprender com o que errou). São decisões de produto, não técnicas — refletem entender como um estudante se comporta.

### A decisão de produto mais madura: esperar antes de divulgar

Aqui está o ponto que mais impressiona, e é contra-intuitivo. Você **decidiu não colocar o Nícia Track no currículo ainda**, preferindo acumular dados de uso real antes. Isso é uma decisão de produto sofisticada: você entende que "software com uso comprovado" vale mais que "software que existe", e teve a disciplina de esperar em vez de exibir cedo demais. Numa entrevista, contar essa decisão mostra maturidade de produto rara — você pensa em evidência, não em aparência.

### Como contar isso em uma entrevista

**Objetiva:**
> "O Nícia Track é uma plataforma de estudo pra concurso que fiz pra uma usuária real. Antes de programar, pesquisei o edital e organizei o conteúdo por matéria — o produto começou pelo problema, não pelo código. As features foram pensadas pro comportamento de quem estuda: streak, simulados fiéis à prova, caderno de erros. E como eu já tinha o produto, aproveitei pra subir ele na AWS e aprender a infraestrutura na prática. Uma decisão que gosto de contar: escolhi não colocar ele no currículo ainda, porque prefiro acumular dados de uso real primeiro — 'software usado' prova mais que 'software que existe'."

---

## O arco que conecta os dois (a sua identidade de produto)

Vale ter uma frase que amarra sua forma de construir:

> "Nos dois casos eu comecei por um problema real de alguém, entreguei o núcleo funcionando, e deixei o produto evoluir com base no uso — não tentei construir tudo de uma vez. É assim que eu penso produto: resolver algo concreto, lançar, e melhorar com o que o uso revela."

Isso comunica três coisas que os times valorizam: foco no problema, capacidade de entregar (não só planejar), e humildade de deixar o uso guiar a evolução.

---

## Como um CTO enxerga a conversa de produto

Quando um CTO puxa o assunto de produto, ele está avaliando se você vai ser um executor de tickets ou um parceiro que pensa. As respostas que impressionam:
- Mostram que você entende **o usuário** (por que streak? porque estudante precisa de constância).
- Mostram **priorização** (multi-tenant desde cedo foi uma aposta; IA veio depois).
- Mostram **disciplina** (esperar dados antes de divulgar o Nícia Track).
- Não inflam — você conta a jornada real, com suas decisões e o que aprendeu.

---

# Parte 2 — Banco de Perguntas por Tema

> Use isto para simular. Cubra a resposta, responda em voz alta, e confira. Cada bloco remete ao módulo onde o tema foi tratado a fundo. O formato: pergunta → o que o entrevistador busca → âncora da resposta (o projeto e o argumento a usar).

## Trajetória e apresentação (Módulo 1)

**"Me fala sobre você."**
Busca: onde te encaixar + clareza. → Pitch: stack + três projetos com ganchos + intenção. Parar depois.

**"Qual seu maior diferencial?"**
Busca: autoconsciência. → Sistema em produção com uso real + decisões conscientes (não tutorial) + amplitude (Django, AWS na mão, async).

**"E sua experiência em time?"**
Busca: honestidade + como você enquadra a lacuna. → Autonomia comprovada me deu disciplina técnica; o time é o próximo passo que busco. Sem me diminuir.

---

## Arquitetura (Módulo 2)

**"Como você estrutura um projeto Django?"**
Busca: se tem método. → Apps por domínio + Service Layer + settings por ambiente.

**"Onde fica a lógica de negócio?"**
Busca: consequências de Fat View/Model. → Camada de serviços. Exemplo `cancelar_venda`: reúso web+API + testabilidade.

**"Qual o custo da camada de serviços?"**
Busca: maturidade. → Indireção. Não vale num CRUD trivial; vale quando a regra é complexa/reutilizada.

---

## Python, Django, FastAPI (Módulo 3)

**"CBV ou FBV?"**
Busca: critério. → CBV para CRUD padrão, FBV para lógica única. Nunca "sempre X".

**"Signals são síncronos?"**
Busca: se conhece o custo. → Sim, no mesmo request. Por isso movo trabalho pesado pra background.

**"Por que o endpoint do MOST é async?"**
Busca: entendimento de concorrência. → I/O-bound, esperas longas, servidor não bloqueia. E: async ≠ mais rápido.

**"Como o FastAPI valida entrada?"**
Busca: modelo do framework. → Pydantic + type hints; rejeita com 422 antes do processamento.

---

## Banco de dados (Módulo 4)

**"O que é `transaction.atomic` e quando usar?"**
Busca: pensa em falha no meio. → Cancelamento (3 operações tudo-ou-nada); rollback automático; saga só pra sistema externo.

**"Explica o N+1."**
Busca: diagnóstico + correção certa. → 61→poucas queries; `select_related` (JOIN) vs `prefetch_related` (IN).

**"Quando um índice atrapalha?"**
Busca: conhece o custo. → Escrita mais lenta, espaço; índice não usado é só custo.

**"Validação no código ou no banco?"**
Busca: entende concorrência. → Os dois, em camadas; constraint fecha a race condition do caixa que o Python não fecha.

**"Soft delete e unique constraint?"**
Busca: se implementou de verdade. → Condição `deleted_at IS NULL` na constraint.

---

## Multi-tenancy (Módulo 5)

**"Que estratégias de multi-tenancy existem?"**
Busca: conhece o espectro. → Shared schema (a minha) / separate schema / separate DB. Isolamento ↑ = custo ↑.

**"Por que shared database?"**
Busca: escolha consciente. → Custo + operação simples; isolamento lógico rigoroso e testado.

**"Como garante que nenhuma query escapa do filtro?"**
Busca: conhece a fraqueza. → Filtro obrigatório + testes de isolamento; evolução é RLS.

**"Por que 404 e não 403 no acesso cross-tenant?"**
Busca: maturidade de segurança. → 403 revela que o recurso existe (vazamento); 404 não revela nada.

---

## Deploy e infraestrutura (Módulo 6)

**"Por que não expor o Django direto?"**
Busca: papel do Nginx. → Estáticos, rate limit, TLS, proteção; Gunicorn não faz isso.

**"Por que RDS e não Postgres na EC2?"**
Busca: confiabilidade. → Backup automático, sobrevive à EC2.

**"Como o banco fica protegido?"**
Busca: segurança de rede. → Security Group do RDS só aceita a EC2.

**"Me conta um problema de produção que você resolveu."**
Busca: experiência real. → O `networkidle` travando por analytics do portal; o 504 do timeout; o falso positivo do "0 resultados".

**"Como você faz deploy sem quebrar produção?"**
Busca: maturidade operacional. → Barber: cliente usava todo dia; homologação antes de produção, features grandes no fim de semana, comunicação com o cliente.

---

## APIs, automação, IA (Módulo 7)

**"detail=True ou False numa action?"**
Busca: entende o Router. → True opera sobre um item (ID); False sobre a coleção.

**"Como a API nunca retorna 500?"**
Busca: pensamento defensivo. → Três camadas de erro + `except Exception`, sempre JSON.

**"RAG ou fine-tuning?"**
Busca: entende o trade-off. → RAG: barato, atualiza na hora, rastreável, anti-alucinação.

**"Por que busca vetorial e não keyword?"**
Busca: entende embeddings. → Keyword não pega sinônimo; vetor captura significado.

---

## Produto (este módulo)

**"Como você decide o que construir primeiro?"**
Busca: priorização. → Núcleo que resolve o problema primeiro; extras (IA) depois, guiado pelo uso.

**"Como você usa feedback do usuário?"**
Busca: se ouve o usuário. → Barber evoluiu por versões com base no uso real; features do Nícia pensadas pro comportamento do estudante.

**"Por que o Nícia Track não está no seu currículo?"**
Busca: maturidade de produto. → Espero dados de uso real; "software usado" prova mais que "software que existe".

---

## Perguntas comportamentais (transversais)

Estas não são técnicas, mas caem sempre. A estrutura de resposta ideal é **STAR** (Situação, Tarefa, Ação, Resultado) — conte um caso concreto, não uma generalização.

**"Conte sobre um problema difícil que você resolveu."**
→ Escolha um com arco completo: o `networkidle` do MOST (situação: travava em produção; ação: investiguei, achei os analytics; resultado: troquei a estratégia de espera). Ou a race condition do caixa.

**"Conte sobre um erro que você cometeu."**
Busca: honestidade + aprendizado. → Um bug real com a lição. O falso positivo do "0 resultados" serve: assumi que o texto era único, não era; aprendi a instrumentar (screenshot) pra ver o que o robô vê.

**"Como você aprende algo novo?"**
Busca: autonomia. → Sua trajetória self-taught: aprendi async construindo o MOST, aprendi AWS montando o deploy em fases. Aprendo fazendo, em cima de um problema real.

---

## Erros gerais a evitar em qualquer resposta

Um resumo transversal dos alertas de todos os módulos:

- **Não inventar.** Se não usou, diga que não usou e explique o conceito. Um bom entrevistador cava onde você hesita.
- **Não vender solução como perfeita.** Toda decisão tem trade-off. Citar o custo da própria escolha é o que mais sinaliza senioridade.
- **Não empilhar números.** Um dado forte, uma vez, quando agrega.
- **Não recitar teoria.** Sempre ancorar num exemplo real dos projetos.
- **Não despejar tudo.** Responder o que foi perguntado, deixar ganchos, deixar o entrevistador puxar.

---

## Checklist de domínio deste módulo

- [ ] Contar Barber e Nícia Track como jornada de produto (problema → construção → lançamento → evolução).
- [ ] Explicar a decisão de esperar dados antes de divulgar o Nícia Track.
- [ ] Ter a frase que amarra sua identidade de produto.
- [ ] Responder pelo menos uma pergunta de cada módulo no banco, em voz alta, sem consultar.
- [ ] Ter dois casos STAR prontos (um problema difícil, um erro com aprendizado).

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- Conto meus projetos como jornada de produto: problema real → núcleo funcionando → evolução guiada pelo uso.
- **A virada SaaS do Barber**: começou pra uma barbearia, virei SaaS no meio do caminho. Foi quando deixei de ver software como código e passei a ver como produto que funciona enquanto evolui. Trouxe isolamento, LGPD e deploy seguro de uma vez.
- Deploy seguro com cliente real: local → homologação → produção; features grandes no fim de semana; comunicação constante.
- Nícia Track: features pro comportamento do estudante; decisão madura de esperar dados antes de divulgar.
- Minha identidade: resolver algo concreto, lançar, melhorar com o uso — não construir tudo de uma vez.

**Decisões técnicas mais importantes (síntese do playbook)**
- Service Layer (reúso + teste) · multi-tenant shared DB (custo + isolamento testado) · transação no cancelamento (consistência) · constraint no banco (race condition) · async no MOST (I/O-bound) · RAG do zero (controle + anti-alucinação) · deploy AWS em fases (entender cada peça).

**Erros que devo evitar ao responder**
- Inventar experiência; vender solução como perfeita; empilhar números; recitar teoria sem exemplo; despejar tudo em vez de deixar ganchos.

**Tecnologias principais abordadas (todo o playbook)**
- Django, DRF, FastAPI, PostgreSQL, Docker, Nginx, Gunicorn, AWS (EC2/RDS/S3), Playwright, RAG/FAISS.

**Palavras-chave que devem aparecer naturalmente**
- problema real, uso real, multi-tenant, priorização, lançar e iterar, feedback, evidência de uso, trade-off, decisão consciente, STAR, aprendizado.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Que construo a partir de um problema real, entrego o núcleo, e evoluo com o uso.
- ✓ Barber em produção e a aposta de nascer multi-tenant; Nícia Track e a decisão madura de esperar dados.
- ✓ Minha identidade de produto numa frase (resolver, lançar, melhorar).
- ✓ Dois casos STAR prontos: um problema difícil e um erro com aprendizado.
- ✓ Os erros a evitar em qualquer resposta: não inventar, não vender perfeição, ancorar em exemplo, deixar ganchos.
