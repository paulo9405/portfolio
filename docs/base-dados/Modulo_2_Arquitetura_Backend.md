# Módulo 2 — Arquitetura Backend

> Tempo de estudo: ~35–45 min
> Objetivo: saber defender como você organiza um projeto backend — por que separou o código do jeito que separou, o que cada camada faz, e como isso se sustenta sob perguntas de um CTO. O foco é o padrão que se repete nos seus três projetos: **View → Service Layer → ORM**.

---

## Por que este módulo importa mais do que parece

Perguntas de arquitetura são o divisor de águas entre júnior e pleno numa entrevista. Qualquer um sabe escrever uma view que consulta o banco. O que o entrevistador está medindo aqui é diferente: **você pensa sobre onde o código mora, ou só empilha lógica onde for mais rápido?**

O que o entrevistador quer descobrir com perguntas de arquitetura:
- Se você consegue justificar uma decisão de organização, não só executá-la.
- Se você entende os problemas que aparecem quando um projeto cresce (código duplicado, views gigantes, lógica impossível de testar).
- Se você tomou essas decisões você mesmo, ou herdou de um tutorial sem entender.

O que você precisa dominar neste módulo:
- Explicar o fluxo View → Service → ORM e por que cada camada existe.
- Defender a organização por apps de domínio.
- Justificar a separação de settings por ambiente.
- Reconhecer os trade-offs — porque toda decisão de arquitetura tem um custo, e admitir o custo é sinal de maturidade.

---

## A decisão central: Service Layer (View → Service → ORM)

Esta é a decisão de arquitetura mais importante dos seus projetos, e a que mais vai render perguntas. Barber Cashflow e Nícia Track seguem exatamente o mesmo padrão: **a view não contém regra de negócio**. Ela recebe a requisição, chama um serviço e devolve a resposta. Toda a lógica vive em `apps/<app>/services/`.

### O que é

Service Layer é uma camada intermediária entre as views (que lidam com HTTP) e os models/ORM (que lidam com dados). A regra de negócio — o "como as coisas funcionam" do sistema — fica isolada em funções ou classes de serviço, separada tanto da entrada HTTP quanto da persistência.

O fluxo:
```
View (recebe request, valida formato, devolve response)
   ↓ chama
Service (regra de negócio: o que precisa acontecer e em que ordem)
   ↓ usa
ORM / Models (persistência: ler e gravar no banco)
```

### Onde utilizei

Nos dois projetos Django. No Barber, `sales/services.py` tem o `cancelar_venda()`, e `agendas/services.py` tem o `AgendamentoService.verificar_conflito_horario()`. No Nícia Track, cada app de domínio tem seu diretório `services/` — a regra era explícita: nenhuma lógica nas views.

Um exemplo concreto do Barber: cancelar uma venda não é uma operação simples. Envolve reverter o agendamento vinculado, restaurar o estoque dos produtos e marcar a venda como deletada. Toda essa sequência vive no serviço `cancelar_venda()`. A view só faz isto:

```python
# sales/views.py
class SaleDeleteView(DeleteView):
    def delete(self, request, *args, **kwargs):
        venda = self.get_object()
        resultado = cancelar_venda(venda)   # toda a regra está aqui dentro
        messages.success(request, 'Venda cancelada.')
        return redirect('sales:list')
```

### Qual problema resolveu

Sem a camada de serviço, a lógica de cancelamento ficaria dentro da view. E aí surge um problema prático imediato: eu tenho a mesma operação sendo disparada de dois lugares — a interface web (view HTML) e a API (DRF). Se a regra mora na view, eu precisaria duplicá-la, e duas cópias divergem com o tempo. Com o serviço, os dois pontos de entrada chamam a mesma função.

O segundo problema que resolveu foi **testabilidade**. Um serviço é uma função que recebe dados e retorna resultado. Consigo testar `cancelar_venda(venda)` diretamente, sem simular uma requisição HTTP. No Nícia Track isso ficou visível na estrutura de testes: os testes unitários exercitam os serviços isoladamente, e só os testes de integração sobem o HTTP.

### Por que escolhi essa solução

Porque o Django, por padrão, empurra você para dois lugares ruins quando o projeto cresce: views que incham (Fat Views) ou models que viram um depósito de métodos de negócio (Fat Models). A Service Layer dá um terceiro lugar, com responsabilidade única: a regra de negócio.

Escolhi manter os serviços simples — funções e alguns `@staticmethod` — em vez de montar uma arquitetura pesada com repositories e injeção de dependência. Para o tamanho dos projetos, isso seria complexidade sem retorno.

### Alternativas

- **Fat Models** (lógica nos models): funciona para regras pequenas ligadas a uma entidade só. Mas o `cancelar_venda` toca venda, agendamento e estoque — três entidades. Colocar isso no model de venda o faria conhecer demais sobre os outros.
- **Fat Views** (lógica nas views): o caminho "natural" do Django, e o mais rápido no começo. Quebra assim que você precisa da mesma regra na API e na web.
- **Repository Pattern + Use Cases**: a versão "enterprise" da Service Layer, com abstração do ORM. Mais testável em teoria, mas adiciona muitas camadas. Overkill para o meu caso.

### Quais vantagens trouxe

- Uma regra, um lugar — web e API chamam o mesmo serviço.
- Views finas, fáceis de ler: dá para bater o olho e entender o que a rota faz.
- Testes de negócio sem mock de HTTP.
- Regra de negócio que se lê quase como português, separada dos detalhes de banco.

### Hoje eu faria igual?

Sim, para projetos deste porte. Se um serviço crescesse muito ou passasse a orquestrar sistemas externos (pagamento, e-mail, filas), aí eu consideraria quebrar cada operação em um use case próprio e retornar objetos tipados em vez de dicionários — que é, aliás, uma das melhorias que anotei. Mas introduzir isso desde o início seria resolver um problema que eu ainda não tenho.

### Qual foi o principal aprendizado

Que "onde o código mora" é uma decisão de engenharia, não um detalhe. A primeira vez que precisei da lógica de cancelamento na API e percebi que ela estava presa dentro de uma view foi o momento em que a Service Layer deixou de ser teoria e virou necessidade concreta.

### Como um CTO enxerga isso

Quando um CTO pergunta "por que você usa uma camada de serviços?", ele não quer a definição de Service Layer — ele quer saber:
- **Você sentiu a dor que ela resolve, ou copiou de um artigo?** A resposta que convence é a que tem um exemplo concreto de duplicação evitada (web + API).
- **Você conhece o custo?** Toda camada adiciona indireção. Um candidato maduro reconhece que Service Layer é overhead injustificado num CRUD trivial e faz sentido quando a regra é complexa ou reutilizada.
- **Você sabe onde ela NÃO cabe?** Saber quando *não* aplicar um padrão sinaliza mais senioridade do que saber aplicá-lo.

### O que um CTO provavelmente perguntaria

- O que é Service Layer e quando você usaria (e quando não)?
- Qual a diferença entre colocar a lógica no model (Fat Model) e num serviço?
- Como você testa a lógica de negócio isoladamente?
- Qual o custo de adicionar essa camada?

### Como responder em uma entrevista

**Resposta objetiva (30–60s):**
> "Nos meus projetos Django eu mantenho as views finas: elas só cuidam do HTTP. A regra de negócio fica numa camada de serviços. No Barber, por exemplo, cancelar uma venda envolve reverter o agendamento, restaurar o estoque e fazer soft delete — tudo isso mora no serviço `cancelar_venda`. Fiz assim porque a mesma operação é chamada da interface web e da API; se a lógica estivesse na view, eu teria que duplicar. E como o serviço é só uma função que recebe dados e retorna resultado, testo direto, sem simular requisição."

**Resposta aprofundada:**
> "O Django, sem disciplina, empurra a lógica para as views ou para os models. Os dois incham com o tempo. Optei por uma camada de serviços com responsabilidade única — a regra de negócio — entre a view e o ORM. Isso me deu três ganhos: reúso entre web e API, views legíveis, e testes de negócio sem mock de HTTP, que no Nícia Track ficou claro na separação entre testes unitários (services) e de integração (views). Mantive os serviços simples de propósito, sem repository nem injeção de dependência, porque para o porte do projeto isso seria complexidade sem retorno. Se um serviço passasse a orquestrar sistemas externos, aí eu quebraria em use cases e retornaria objetos tipados em vez de dicts."

---

## Organização por apps de domínio

### O que é

Em vez de agrupar arquivos por tipo técnico (todos os models juntos, todas as views juntas), o projeto é dividido em **apps que representam áreas do negócio** — cada app com seus próprios models, views, serviços e testes.

### Onde utilizei

Nos dois projetos Django. O Nícia Track é o exemplo mais limpo:

```
apps/
├── core/          ← BaseModel (UUID PK, timestamps), exceções de domínio
├── accounts/      ← autenticação, perfil (email como login)
├── questions/     ← Subject, Topic, Question, Alternative
├── exams/         ← Quiz, QuizQuestion, UserAnswer (treino e simulado)
├── performance/   ← estatísticas e pontos fracos
├── dashboard/     ← painel: streak, metas, atividade recente
└── study_plan/    ← plano de estudos, capítulos, caderno de erros
```

No Barber, a mesma ideia: `sales`, `agendas`, `tenants`, `cash_register`, `ai_chat`, `notifications` — cada domínio no seu app.

### Qual problema resolveu

Um único app gigante com dezenas de models fica impossível de navegar e cria acoplamento: tudo pode importar tudo. Separar por domínio dá fronteiras. Quando preciso mexer em agendamento, sei exatamente onde ir. E fica claro o que cada parte do sistema faz só de olhar a lista de apps.

### Por que escolhi essa solução

Porque acompanha a forma como o negócio realmente é dividido. "Questões", "simulados", "desempenho" são conceitos que existem na cabeça do usuário — refletir isso no código faz o sistema ser mais fácil de raciocinar. É o espírito do Django ("reusable apps"), levado a sério.

O app `core` merece destaque: ele guarda o `BaseModel` — a classe base com UUID como chave primária e timestamps (`created_at`, `updated_at`) — que todos os outros apps herdam. Isso centraliza uma decisão que, de outro modo, estaria repetida em cada model.

### Alternativas

- **Um app único**: mais simples no começo, vira um novelo depois.
- **Separação por camada técnica** (uma pasta `models/`, uma `views/` no topo): organiza por tipo, mas espalha cada domínio por várias pastas — o oposto do que eu queria.

### Quais vantagens trouxe

- Fronteiras claras entre domínios.
- Fácil localizar onde algo mora.
- Decisões comuns (PK, timestamps) centralizadas no `core`.
- Cada app tem seus próprios testes, próximos do código que exercitam.

### Hoje eu faria igual?

Sim. É uma decisão que envelhece bem. O único cuidado que aprendi é vigiar o acoplamento *entre* apps — quando um app importa demais de outro, é sinal de que a fronteira foi mal desenhada.

### Qual foi o principal aprendizado

Que a estrutura de pastas de um projeto conta uma história. Se alguém abre `apps/` e entende o que o sistema faz só pelos nomes, a organização está certa.

### O que um CTO provavelmente perguntaria

- Como você decide o que vira um app separado?
- Como você lida com dependência entre apps?
- O que você põe num app `core`/`common` e por quê?

### Como responder em uma entrevista

**Resposta objetiva:**
> "Organizo por domínio, não por tipo técnico. Cada área do negócio — questões, simulados, desempenho — é um app Django com seus models, serviços, views e testes. Isso dá fronteiras claras e faz o projeto ser fácil de navegar. Tenho também um app `core` com um `BaseModel` que padroniza UUID como PK e timestamps para todos os outros."

**Resposta aprofundada:**
> "A separação por domínio reflete como o negócio realmente é dividido, então o código fica mais fácil de raciocinar — abrir a pasta `apps` já conta o que o sistema faz. O cuidado que tenho é com acoplamento entre apps: quando um começa a importar muito de outro, geralmente a fronteira foi mal desenhada e vale reconsiderar. Decisões transversais, como PK e timestamps, ficam num `BaseModel` no app `core`, para não repetir a mesma escolha em cada model."

---

## Separação de settings por ambiente

### O que é

Em vez de um único `settings.py` com `if DEBUG:` espalhado, o projeto tem um pacote de configurações dividido por ambiente, todos herdando de uma base comum.

### Onde utilizei

Nícia Track:
```
config/settings/
├── base.py          ← configuração compartilhada
├── development.py   ← SQLite local, ou PostgreSQL se rodando via Docker
├── production.py    ← PostgreSQL, HTTPS forçado, cookies seguros, logging
└── testing.py       ← SQLite em memória, hasher MD5 (testes ~100x mais rápidos)
```

### Qual problema resolveu

Ambientes diferentes têm necessidades opostas. Em produção eu quero `DEBUG=False`, HTTPS obrigatório e SSL no banco. Em teste eu quero o contrário do que é seguro: banco em memória e o hasher de senha mais rápido possível, porque o que importa é velocidade da suíte. Amontoar isso num arquivo só com condicionais vira um campo minado — o risco real é subir `DEBUG=True` em produção por engano, que é uma falha de segurança séria.

### Por que escolhi essa solução

Porque cada arquivo passa a ter uma responsabilidade única e legível. `production.py` é a fonte da verdade sobre "como o sistema roda em produção" — sem ter que mentalmente filtrar condicionais. E o segredo nunca fica no código: `SECRET_KEY`, senhas e hosts vêm de variáveis de ambiente via `python-decouple`, lendo de um `.env` que nunca é versionado.

Um detalhe que mostra intenção: o `testing.py` usa MD5 para hash de senha. Isso seria absurdo em produção, mas em teste torna a suíte muito mais rápida, porque o custo do hashing seguro é justamente ser lento.

### Alternativas

- **settings.py único com condicionais**: funciona em projeto pequeno, fica perigoso ao crescer.
- **Variáveis de ambiente para absolutamente tudo, um arquivo só**: possível, mas você perde a legibilidade de ter cada ambiente descrito num lugar.

### Quais vantagens trouxe

- Cada ambiente é legível isoladamente.
- Menor risco de vazar configuração de dev para produção.
- Segredos fora do código, em `.env` não versionado.
- Testes rápidos por decisões específicas do ambiente de teste.

### Hoje eu faria igual?

Sim. Em produção real na AWS, o próximo passo seria trocar o `.env` em disco por um gerenciador de segredos (AWS SSM Parameter Store ou Secrets Manager) — que é exatamente o caminho que mapeei no roadmap de deploy. O padrão de settings em si permanece.

### Qual foi o principal aprendizado

Que configuração é parte da arquitetura, não um detalhe de setup. A separação por ambiente foi o que tornou o deploy AWS viável sem reescrever nada: o `production.py` já esperava as variáveis certas.

### Como um CTO provavelmente enxerga isso

Ele quer saber se você entende segurança de configuração: segredos fora do repositório, `DEBUG=False` garantido em produção, e consciência de que dev/teste/prod são mundos diferentes. É uma pergunta que separa quem já quebrou algo em produção de quem nunca fez deploy de verdade.

### Como responder em uma entrevista

**Resposta objetiva:**
> "Uso settings separados por ambiente, herdando de um `base.py`: development, production e testing. Cada um tem só o que faz sentido para ele — produção com HTTPS e SSL no banco, teste com SQLite em memória e hasher MD5 para a suíte voar. Segredos ficam sempre em variáveis de ambiente, num `.env` que não é versionado."

**Resposta aprofundada:**
> "Amontoar ambientes num arquivo só com condicionais é arriscado — o pior caso é subir `DEBUG=True` em produção. Separando, cada arquivo vira a fonte da verdade do seu ambiente. Isso teve um efeito prático no deploy AWS: como o `production.py` já esperava as variáveis certas, migrar do Render para EC2 não exigiu tocar em código de configuração. O próximo passo natural em produção séria seria trocar o `.env` por AWS Secrets Manager, mas a estrutura de settings continua a mesma."

---

## Checklist de domínio deste módulo

Você domina este módulo quando consegue, sem consultar nada:

- [ ] Desenhar o fluxo View → Service → ORM e explicar a responsabilidade de cada camada.
- [ ] Dar um exemplo concreto (cancelar venda) de por que a lógica saiu da view.
- [ ] Explicar quando a Service Layer NÃO vale a pena.
- [ ] Justificar a organização por apps de domínio e o papel do `core`/`BaseModel`.
- [ ] Defender a separação de settings por ambiente pelo ângulo de segurança.
- [ ] Reconhecer o trade-off de cada decisão (toda camada tem custo).

---

## Perguntas comuns

**"Como você estrutura um projeto Django?"**
Busca: se você tem um método ou improvisa.
→ Apps por domínio + Service Layer + settings por ambiente. Dê os três em uma frase e aprofunde no que ele puxar.

**"Onde você coloca a lógica de negócio?"**
Busca: se você entende as consequências de Fat View / Fat Model.
→ Numa camada de serviços. Exemplo do `cancelar_venda`, e o motivo: reúso entre web e API + testabilidade.

**"Qual o trade-off da camada de serviços?"**
Busca: maturidade — se você vê o custo, não só o benefício.
→ Indireção a mais. Não vale num CRUD trivial; vale quando a regra é complexa ou reutilizada.

**"Como você separa configuração de dev e produção?"**
Busca: consciência de segurança de configuração.
→ Settings por ambiente herdando de base, segredos em `.env` fora do versionamento, `DEBUG=False` garantido em produção.

**"Como você decide o que vira um app separado?"**
Busca: se sua modelagem acompanha o domínio.
→ Por área de negócio. Se é um conceito que existe na cabeça do usuário (questões, simulados), tende a virar app.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- O padrão dos meus projetos: **View → Service Layer → ORM**. View cuida de HTTP, serviço cuida de regra de negócio, ORM cuida de dados.
- Organização por **apps de domínio**, não por tipo técnico. App `core` guarda o `BaseModel` (UUID PK + timestamps).
- **Settings por ambiente** (base/dev/prod/testing), segredos em `.env` não versionado.

**Decisões técnicas mais importantes**
- Tirei a lógica da view porque a mesma operação roda na web e na API — serviço evita duplicação.
- Mantive serviços simples (funções, `@staticmethod`), sem repository/DI, porque seria complexidade sem retorno no porte atual.
- `production.py` já esperava variáveis de ambiente — foi o que tornou o deploy AWS possível sem reescrever config.

**Erros que devo evitar ao responder**
- Vender Service Layer como bala de prata; sempre citar o custo (indireção) e quando NÃO usar (CRUD trivial).
- Falar de arquitetura só na teoria — sempre ancorar num exemplo real (cancelar venda).
- Esquecer o ângulo de segurança na pergunta de settings (`DEBUG=False`, segredos fora do repo).

**Tecnologias principais abordadas**
- Django (apps, views, ORM), padrão Service Layer, `python-decouple` para configuração, estrutura de settings modular.

**Palavras-chave que devem aparecer naturalmente**
- separação de responsabilidades, view fina, camada de serviço, regra de negócio, reúso web/API, testabilidade, apps de domínio, BaseModel, settings por ambiente, segredos fora do versionamento, trade-off.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ O fluxo View → Service → ORM e a responsabilidade de cada camada.
- ✓ Um exemplo real de lógica que saiu da view (cancelar venda) e por quê (reúso web+API, testabilidade).
- ✓ Que organizo por domínio, com um `BaseModel` central no app `core`.
- ✓ Que separo settings por ambiente e mantenho segredos fora do código.
- ✓ O trade-off de cada decisão — toda camada tem um custo, e sei quando não aplicá-la.
