# Módulo 3 — Python, Django e FastAPI

> Tempo de estudo: ~40–45 min
> Objetivo: dominar a explicação dos recursos de framework que você realmente usou — não uma varredura de tudo que Django e FastAPI oferecem, mas os poucos que aparecem no seu código e que um CTO vai explorar. Para cada um: onde usei, que problema resolveu, e como defender a escolha.

---

## Como pensar este módulo

Este é o módulo com maior risco de virar decoreba de teoria — e é exatamente o que queremos evitar. O entrevistador não quer que você recite a documentação do Django. Ele quer descobrir uma coisa: **você usa esses recursos porque entende o problema que eles resolvem, ou porque o tutorial mandou?**

Por isso, a régua aqui é implacável: só entra recurso que aparece nos seus projetos. Se você nunca usou um `pre_save`, não vamos estudar `pre_save` — vamos estudar o `post_save` que você usou de verdade, e você aprende a dizer com naturalidade "esse eu não usei, mas usei o `post_save`, que resolve X".

Dividi o módulo em dois blocos: o lado **Django** (recursos do ciclo de requisição) e o lado **FastAPI/async** (validação e concorrência). São mundos com filosofias diferentes, e saber contrastá-los já é meio caminho para uma boa resposta.

---

# Bloco A — Django

## Class-Based Views (CBV)

### O que é

Views escritas como classes que herdam de views genéricas do Django (`ListView`, `DetailView`, `DeleteView`...), em vez de funções. Cada view genérica já traz o esqueleto de uma operação comum (listar, detalhar, criar) e você sobrescreve só os pontos que precisa customizar.

### Onde utilizei

No Barber. A `SaleListView` herda de `ListView` e sobrescreve `get_queryset()` para aplicar o filtro por tenant, os filtros opcionais (período, barbeiro) e a ordenação:

```python
class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    paginate_by = 20

    def get_queryset(self):
        qs = Sale.objects.filter(tenant=self.request.tenant) \
            .select_related('barbeiro', 'agendamento', 'cliente_cadastrado') \
            .prefetch_related('servicos', 'produtos')
        # filtros opcionais via GET...
        return qs.order_by('-data')
```

### Qual problema resolveu

Listagem com paginação, filtro por tenant e ordenação é um padrão que se repete em várias telas. Escrever isso à mão em cada view geraria código repetido e propenso a erro — o mais perigoso sendo esquecer o filtro de tenant e vazar dados de uma barbearia para outra. A `ListView` cuida da paginação e da renderização; eu só descrevo o queryset.

### Por que escolhi essa solução

Para operações CRUD padrão, a CBV elimina boilerplate e me deixa focar no que é específico do meu caso — o `get_queryset()`. O `LoginRequiredMixin` adiciona autenticação por composição, sem eu escrever a checagem.

### Alternativas

- **Function-Based Views (FBV)**: mais explícitas e diretas de ler. Uso-as quando a lógica é única e não se encaixa num padrão genérico. Para um fluxo linear e específico, uma FBV costuma ser mais clara que sobrescrever métodos de uma CBV.

### Quais vantagens trouxe

- Menos código repetido em listagens.
- Paginação e renderização "de graça".
- Autenticação por mixin.

### Hoje eu faria igual?

Sim, com um ajuste: extrairia o filtro de tenant para um mixin próprio (`TenantFilterMixin`), para não repetir `filter(tenant=...)` em cada view e reduzir o risco de esquecer. É uma melhoria que anotei.

### O que um CTO provavelmente perguntaria

- Quando você usa CBV e quando usa FBV?
- O que é um mixin e como ele se relaciona com herança múltipla?
- Como você customiza o queryset de uma ListView?

### Como responder em uma entrevista

**Objetiva:**
> "Uso CBV para CRUD padrão porque elimina boilerplate — na listagem de vendas, herdo de `ListView` e só sobrescrevo o `get_queryset` para filtrar por tenant e aplicar filtros. Paginação e renderização vêm prontas. Para lógica única e não-padrão, prefiro FBV, que é mais explícita."

**Aprofundada:**
> "A vantagem da CBV é reúso via herança e mixins — o `LoginRequiredMixin` me dá autenticação por composição, sem escrever a checagem. O risco é a legibilidade: quando você sobrescreve muitos métodos, o fluxo fica espalhado e difícil de seguir. Por isso não é dogma pra mim — CBV para o que é padrão, FBV para o que é específico. Uma melhoria que faria é um `TenantFilterMixin` para centralizar o filtro obrigatório de tenant e não depender de lembrar dele em cada view."

---

## Middleware

### O que é

Um componente que intercepta toda requisição antes de chegar à view (e toda resposta depois dela). É o lugar para lógica transversal — que precisa rodar em *todo* request, independente da view.

### Onde utilizei

No Barber, o `TenantMiddleware` resolve qual barbearia (tenant) está ativa em cada request, tentando três fontes em ordem de prioridade: a sessão, o perfil do usuário e, por último, o domínio. O tenant resolvido é gravado em `request.tenant` e num thread-local, para ficar acessível em qualquer ponto do código durante aquele request.

### Qual problema resolveu

Num SaaS multi-tenant, *toda* requisição precisa saber a que tenant pertence — para filtrar dados e bloquear tenants suspensos. Isso não pode depender de cada view lembrar de resolver o tenant. O middleware garante que a resolução acontece uma vez, no começo, sempre.

### Por que escolhi essa solução

Porque é lógica genuinamente transversal. Colocá-la numa base view ou num decorator exigiria aplicá-la manualmente em cada ponto de entrada — e bastaria esquecer em um para abrir uma brecha de isolamento. O middleware é o único lugar que garante cobertura total.

### Alternativas

- **Resolver o tenant em cada view / base view**: repetitivo e falível.
- **Decorator por view**: melhor que nada, mas ainda exige lembrar de aplicar.

O middleware ganha porque cobre 100% dos requests sem depender de disciplina manual.

### Quais vantagens trouxe

- Resolução de tenant garantida em todo request.
- Bloqueio centralizado de tenant suspenso.
- `request.tenant` disponível em qualquer camada.

### Hoje eu faria igual?

Manteria a abordagem, mas com uma ressalva técnica importante: uso `threading.local` para guardar o tenant, o que funciona no modelo síncrono (WSGI). Para um servidor ASGI/async, o correto seria `contextvars`, porque thread-local não isola corretamente entre tarefas assíncronas. É a melhoria mais relevante que anotei.

### Como um CTO enxerga isso

Middleware de tenant é uma das perguntas favoritas de CTO num contexto de SaaS, e ele não quer a definição de middleware. Ele quer saber: você entende que isolamento não pode depender de lembrar de filtrar? Pensou na ordem dos middlewares (autenticação antes de tenant)? Sabe limpar o thread-local no fim do request para não vazar estado entre requisições? Cada um desses detalhes sinaliza que você pensou o problema a fundo, não só fez funcionar.

### O que um CTO provavelmente perguntaria

- Qual o ciclo de vida de um middleware?
- Por que thread-local? Que problema ele resolve aqui?
- Como você garante que o thread-local é limpo, mesmo com exceção?
- A ordem dos middlewares importa? Por quê?

### Como responder em uma entrevista

**Objetiva:**
> "Implementei um middleware de tenant que roda em todo request e resolve qual barbearia está ativa — pela sessão, pelo perfil do usuário ou pelo domínio, nessa ordem. Gravo o resultado em `request.tenant` para o resto do código usar. Fiz no middleware porque isolamento de dados não pode depender de cada view lembrar de resolver o tenant."

**Aprofundada:**
> "O middleware roda `process_request` antes da view e `process_response` depois. Guardo o tenant num thread-local além do request, para acessá-lo em camadas que não recebem o request diretamente, e limpo esse thread-local na resposta para não vazar estado entre requisições. Um ponto de atenção: thread-local funciona em WSGI síncrono; se eu migrasse para ASGI, trocaria por `contextvars`, que é o mecanismo correto para isolar valores entre tarefas async."

---

## Signals

### O que é

Um mecanismo de publish/subscribe do Django: certos eventos (como salvar um objeto) emitem um "sinal", e funções registradas como receivers reagem automaticamente.

### Onde utilizei

No Barber, `post_save` no model `Agendamento`: quando um agendamento é criado, o receiver `criar_notificacao_agendamento` dispara e cria notificações para o barbeiro e para o cliente. O registro é feito no `ready()` do `AppConfig`.

### Qual problema resolveu

Um agendamento pode ser criado de vários lugares — web, API, admin. Se a criação de notificações estivesse em cada um desses pontos, seria código duplicado e fácil de esquecer ao adicionar um novo ponto de entrada. O signal garante que "criou agendamento → gera notificação" acontece independentemente de onde a criação partiu.

### Por que escolhi essa solução

Para desacoplar a notificação do fluxo de criação. O código que cria o agendamento não precisa saber que notificações existem; o signal cuida disso à parte.

### Alternativas

- **Chamar a criação de notificação explicitamente** (idealmente dentro de um serviço): mais explícito e mais fácil de testar, ao custo de ter que lembrar de chamar em cada ponto.

Este é um caso interessante porque a alternativa tem mérito real. Signals brilham no desacoplamento, mas escondem o fluxo — quem lê a view não vê que uma notificação é criada. Por isso anotei como melhoria "considerar substituir por serviço explícito para melhor testabilidade". Saber apontar isso é o que mostra que a escolha foi consciente.

### Quais vantagens trouxe

- Notificação garantida, venha o agendamento de onde vier.
- Model de agendamento desacoplado da lógica de notificação.

### Hoje eu faria igual?

Depende do peso que eu daria à clareza do fluxo. Para efeitos colaterais leves e desacoplados, signal serve. Se a lógica crescesse ou eu quisesse rastreabilidade explícita, migraria para uma chamada de serviço. E notificações pesadas (e-mail, push) eu tiraria do request e jogaria para background (Celery), porque signals são síncronos e rodam no mesmo request — segurar o usuário esperando o envio é ruim.

### O que um CTO provavelmente perguntaria

- Signals são síncronos ou assíncronos? (Síncronos — rodam no mesmo thread do request.)
- Diferença entre `pre_save` e `post_save`?
- Qual a desvantagem de signals? Quando você evitaria?
- Como evitar loop infinito (um signal que salva e re-dispara)?

### Como responder em uma entrevista

**Objetiva:**
> "Uso `post_save` para criar notificações quando um agendamento é criado. Fiz com signal para desacoplar — como o agendamento pode ser criado pela web, API ou admin, o signal garante a notificação em todos os casos sem duplicar código."

**Aprofundada:**
> "Signals são ótimos para desacoplar efeitos colaterais, mas têm um custo de clareza: quem lê o código de criação não vê que uma notificação é disparada. Por isso trato como escolha, não regra — para lógica que precisa ser explícita e bem testada, prefiro chamar um serviço direto. E como signals são síncronos, rodam dentro do request; para algo pesado como e-mail, eu moveria para background com Celery, para não segurar a resposta ao usuário."

---

## Model Validation (`clean` / `full_clean`)

### O que é

Validação de regras de negócio no nível do model, sobrescrevendo o método `clean()` (validação cross-field) e garantindo que ele rode ao chamar `full_clean()` dentro do `save()`.

### Onde utilizei

No Barber, o model `Agendamento` valida no `clean()`: não permite agendamento no passado, exige hora de término após o início, e — a regra mais importante — verifica conflito de horário com outros agendamentos do mesmo barbeiro (delegando ao `AgendamentoService`). O `save()` chama `full_clean()` antes de persistir, garantindo que a validação sempre rode.

### Qual problema resolveu

Algumas regras precisam valer *sempre*, não importa de onde o dado venha — form, API ou admin. Se a validação estivesse só no form, criar um agendamento pela API escaparia dela, permitindo dois clientes no mesmo horário. Colocar no model e forçar via `save()` fecha essa porta.

### Por que escolhi essa solução

Porque o model é o último ponto antes do banco — validar ali é a garantia mais forte de que dado inválido não entra, independentemente do ponto de entrada.

### Alternativas

- **Validação no form/serializer**: adequada para regras ligadas à UI, mas não cobre outros pontos de entrada.
- **Constraint no banco**: a garantia mais forte de todas para regras simples (unicidade, checagem), e complementar. Mas conflito de horário é uma regra que envolve comparar intervalos com outras linhas — difícil de expressar como constraint simples, então vive melhor no `clean()`.

### Quais vantagens trouxe

- Regra de negócio garantida em qualquer ponto de entrada.
- Erros específicos por campo (via `ValidationError` com dict).

### Hoje eu faria igual?

Sim, para regras que precisam ser universais. O cuidado é performance: a checagem de conflito faz uma query a mais no save, o que é aceitável no volume atual. Em alta escala, eu reavaliaria.

### O que um CTO provavelmente perguntaria

- Diferença entre validação no `clean()` do model e no form/serializer?
- Por que sobrescrever `save()` para chamar `full_clean()`?
- Quando você usaria constraint de banco em vez de validação em código?

### Como responder em uma entrevista

**Objetiva:**
> "No model Agendamento uso `clean()` para regras de negócio, como não permitir conflito de horário do mesmo barbeiro. Chamo `full_clean()` no `save()` para garantir que a validação rode sempre — venha o agendamento do form, da API ou do admin. Isso evita, por exemplo, dois clientes no mesmo horário criados por caminhos diferentes."

**Aprofundada:**
> "Validação de form só cobre a UI; regra que precisa valer sempre tem que estar mais fundo. Ponho no `clean()` do model e forço via `save()`. Para regras simples como unicidade, eu complementaria com constraint no banco, que é a garantia mais forte. O conflito de horário fica no `clean()` porque envolve comparar intervalos com outras linhas — não dá pra expressar bem como constraint simples. O trade-off é uma query extra no save, aceitável no volume atual."

---

# Bloco B — FastAPI e Programação Assíncrona

> Contexto: o MOST é o único projeto onde saí do Django síncrono. Foi uma escolha deliberada — automação de navegador com Playwright é assíncrona por natureza, e FastAPI foi construído em torno de async. Saber contrastar as duas filosofias é o que torna esse bloco valioso numa entrevista.

## async / await (por que o serviço é assíncrono)

### O que é

`async`/`await` é o modelo de concorrência do Python para tarefas de espera (I/O): em vez de bloquear enquanto espera uma resposta externa, a função "cede" o controle e o servidor pode atender outra requisição nesse meio-tempo.

### Onde utilizei

No MOST inteiro. O Playwright é assíncrono, então a função `executar_consulta()` é `async`, e o endpoint FastAPI que a chama também precisa ser:

```python
@app.post("/consulta", response_model=ConsultaSaida)
async def consulta(dados: ConsultaEntrada) -> ConsultaSaida:
    return await executar_consulta(dados)
```

### Qual problema resolveu

O robô passa a maior parte do tempo *esperando* — o portal carregar, a página responder. Se o endpoint fosse síncrono, o servidor ficaria bloqueado durante toda a navegação de um robô, impedindo qualquer outra requisição simultânea. Com `async`, enquanto um robô espera o portal, o servidor pode aceitar e processar outras chamadas.

### Por que escolhi essa solução

Porque a natureza do problema é I/O-bound com esperas longas (uma consulta pode levar até 3 minutos no cenário com filtro social). Esse é exatamente o cenário onde async rende: muitas tarefas esperando ao mesmo tempo, poucas CPU-bound.

### Alternativas

- **Django síncrono + Celery/threads**: possível, mas Playwright já é async nativo e FastAPI abraça async sem fricção. Forçar o modelo síncrono seria remar contra a ferramenta.

### Quais vantagens trouxe

- Múltiplas consultas simultâneas sem bloquear o servidor.
- Alinhamento natural com o Playwright (que já é async).

### Hoje eu faria igual?

Sim — é o caso de uso onde async faz sentido. O aprendizado foi entender que async não deixa uma tarefa individual mais rápida; ele deixa o servidor *concorrente*. Se o gargalo fosse CPU e não espera, async não ajudaria — aí seria multiprocessing.

### Como um CTO enxerga isso

Ele quer saber se você entende *quando* async ajuda e quando não. A armadilha clássica é achar que "async é mais rápido". A resposta madura: async ajuda em I/O-bound (esperar rede, disco, outro serviço); para CPU-bound, não adianta. Demonstrar essa distinção vale mais que qualquer detalhe de sintaxe.

### O que um CTO provavelmente perguntaria

- Por que o endpoint precisa ser `async`?
- async torna o código mais rápido? (Não — torna o servidor concorrente em tarefas de I/O.)
- Diferença entre async e threads/multiprocessing?
- O que aconteceria se você chamasse uma função `async` sem `await`?

### Como responder em uma entrevista

**Objetiva:**
> "No MOST o endpoint é `async` porque o scraper usa Playwright, que é assíncrono. Como o robô passa a maior parte do tempo esperando o portal, async permite que o servidor atenda outras requisições nesse meio-tempo, em vez de ficar bloqueado durante toda a navegação de um robô."

**Aprofundada:**
> "async não acelera uma consulta individual — ela ainda leva o tempo que o portal demorar. O que ele muda é a concorrência: o servidor não fica preso numa requisição enquanto ela espera I/O. É o modelo certo para um problema I/O-bound como esse, com esperas de até 3 minutos. Se o gargalo fosse CPU, async não ajudaria e eu iria para multiprocessing. Escolhi FastAPI justamente porque ele foi feito em torno de async e casa com o Playwright sem fricção."

---

## Pydantic (validação e contrato de API)

### O que é

Biblioteca de validação de dados por type hints. No FastAPI, você declara a forma da entrada e da saída como classes Pydantic, e o framework valida automaticamente e gera a documentação (Swagger) a partir delas.

### Onde utilizei

No MOST, `ConsultaEntrada` (entrada) e `ConsultaSaida` (saída) são schemas Pydantic separados. O endpoint declara `response_model=ConsultaSaida`. O campo `tipo_busca` usa `Literal["CPF", "NIS", "Nome"]`, então qualquer valor fora disso é rejeitado com HTTP 422 *antes* do robô rodar.

### Qual problema resolveu

Duas coisas de uma vez: **validação** (garante que a entrada tem o formato certo antes de gastar recursos rodando o robô) e **contrato/documentação** (o Swagger em `/docs` mostra exatamente os campos, tipos e exemplos, sem eu escrever documentação à mão).

### Por que escolhi essa solução

Porque separar entrada e saída em schemas explícitos torna o contrato da API óbvio e à prova de erro. Se o cliente manda `tipo_busca: "email"`, o Pydantic barra com uma mensagem clara antes de qualquer processamento. Um exemplo concreto do porquê separar: a saída não deve expor campos internos; ter uma classe de saída dedicada me dá controle total do que sai.

### Alternativas

- **Receber `dict` e validar na mão**: possível, mas perde a validação automática e o Swagger, e espalha checagens pelo código.

### Quais vantagens trouxe

- Entrada inválida barrada cedo, com erro claro (422).
- Swagger gerado de graça a partir dos schemas.
- Contrato de API explícito e versionável.

### Hoje eu faria igual?

Sim. É um dos maiores ganhos do FastAPI e a razão de eu tê-lo escolhido para uma API. O aprendizado foi ver que os type hints deixam de ser documentação passiva e viram validação executável.

### O que um CTO provavelmente perguntaria

- Como a validação de entrada funciona no FastAPI?
- Por que separar schema de entrada e de saída?
- O que o `response_model` faz além de documentar? (Filtra campos que não deveriam sair.)
- Como o Swagger é gerado?

### Como responder em uma entrevista

**Objetiva:**
> "No MOST uso Pydantic para os schemas de entrada e saída. A entrada é validada automaticamente — se `tipo_busca` não for CPF, NIS ou Nome, o FastAPI rejeita com 422 antes de chamar o robô, porque uso `Literal`. E o `response_model` documenta a saída no Swagger e ainda filtra campos que não deveriam vazar."

**Aprofundada:**
> "O ganho do Pydantic é que os type hints viram validação executável e documentação ao mesmo tempo. Separo entrada e saída em classes distintas porque são contratos diferentes: a entrada eu valido, a saída eu controlo — não quero expor campos internos. Isso barra dado inválido cedo, antes de gastar o custo de rodar o Playwright, e me dá o Swagger sem escrever uma linha de doc. É basicamente o motivo de eu ter escolhido FastAPI para essa API em vez de montar validação na mão."

---

## Contraste rápido: Django vs FastAPI (sabendo defender os dois)

Uma pergunta que aparece quando você tem os dois no currículo: *"você usa Django e FastAPI — quando escolhe cada um?"* A resposta que convence:

> "Django quando eu quero um framework completo com bateria inclusa — ORM, admin, auth, forms — que é o caso de um produto CRUD com muitas telas, como o Barber e o Nícia Track. FastAPI quando o foco é uma API async e leve, sem precisar de todo o ecossistema Django — como o MOST, que é essencialmente um endpoint que orquestra um robô assíncrono. Não é um melhor que o outro; são ferramentas para formatos de problema diferentes."

---

## Checklist de domínio deste módulo

Você domina este módulo quando consegue, sem consultar:

- [ ] Explicar quando usa CBV vs FBV, com o exemplo da `SaleListView`.
- [ ] Justificar por que a resolução de tenant vive num middleware, e a ressalva thread-local vs contextvars.
- [ ] Defender signals E apontar honestamente sua desvantagem (esconde o fluxo).
- [ ] Explicar por que a validação de conflito de horário está no `clean()` do model.
- [ ] Explicar por que async ajuda no MOST — e deixar claro que async ≠ "mais rápido".
- [ ] Explicar o duplo papel do Pydantic (validação + contrato/Swagger) e por que separar entrada/saída.
- [ ] Contrastar Django e FastAPI sem dizer que um é melhor.

---

## Perguntas comuns

**"CBV ou FBV?"** → Busca: se você tem critério. CBV para CRUD padrão, FBV para lógica única. Nunca "sempre X".

**"O que é middleware e quando usar?"** → Busca: se você entende lógica transversal. Exemplo do tenant + o motivo (não pode depender de cada view lembrar).

**"Signals são síncronos?"** → Busca: se você conhece o custo. Sim, síncronos, no mesmo request; por isso movo trabalho pesado para background.

**"Por que o endpoint é async?"** → Busca: se você entende concorrência de verdade. I/O-bound, esperas longas, servidor não bloqueia. E o alerta: async não acelera a tarefa individual.

**"Como o FastAPI valida a entrada?"** → Busca: se você entende o modelo do framework. Pydantic + type hints, rejeição com 422 antes do processamento.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- CBV para CRUD padrão (sobrescrevo `get_queryset`), FBV para lógica específica.
- Middleware = lógica transversal; resolve o tenant em todo request. Thread-local hoje, `contextvars` se fosse async.
- Signal `post_save` cria notificações desacopladas — mas signal esconde o fluxo (custo).
- `clean()` + `full_clean()` no `save()` = regra válida em qualquer ponto de entrada.
- async = concorrência em I/O, **não** velocidade da tarefa individual.
- Pydantic = validação executável + contrato/Swagger; entrada e saída separadas.

**Decisões técnicas mais importantes**
- Tenant no middleware porque isolamento não pode depender de lembrar de filtrar.
- Conflito de horário no `clean()` do model porque precisa valer na web, API e admin.
- FastAPI async no MOST porque Playwright é async e o problema é I/O-bound.

**Erros que devo evitar ao responder**
- Dizer que "async é mais rápido" — é concorrência, não velocidade.
- Vender signal sem citar a desvantagem (fluxo implícito, difícil de testar).
- Falar de CBV como dogma; sempre apresentar o critério CBV vs FBV.
- Dizer que Django ou FastAPI é "melhor" — são para formatos de problema diferentes.

**Tecnologias principais abordadas**
- Django: CBV, middleware, signals, model validation. FastAPI: async/await, Pydantic, `response_model`, Swagger.

**Palavras-chave que devem aparecer naturalmente**
- get_queryset, mixin, lógica transversal, thread-local, contextvars, post_save, desacoplamento, full_clean, ponto de entrada, I/O-bound, concorrência, 422, response_model, contrato de API.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Quando uso CBV vs FBV, e por que o tenant vive num middleware.
- ✓ Que uso signal para desacoplar notificações — e conheço sua desvantagem.
- ✓ Por que a validação crítica está no `clean()` do model, não só no form.
- ✓ Por que o MOST é async (I/O-bound) — e que async é concorrência, não velocidade.
- ✓ O duplo papel do Pydantic (validar + documentar) e por que escolhi FastAPI para essa API.
