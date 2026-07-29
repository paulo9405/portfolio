# Módulo 1 — Sua Trajetória e Como se Apresentar

> Tempo de estudo: ~30–40 min
> Objetivo: sair deste módulo capaz de abrir qualquer entrevista com segurança, contar sua história de forma que puxe as perguntas para o seu terreno técnico, e defender por que sua trajetória — mesmo sem anos de time — te qualifica.

---

## Como usar este playbook

Este material não existe para te transformar em especialista em todas as tecnologias. Ele existe para uma coisa só: **fazer você explicar com clareza e segurança as decisões técnicas que você realmente tomou** ao construir seus projetos.

Por isso, o foco em todos os módulos é sempre o mesmo — experiência prática, raciocínio, justificativa e capacidade de defender uma decisão. Teoria de livro entra só o suficiente para sustentar a defesa, nunca como fim em si.

Cada módulo é escrito no formato mentor → aluno: primeiro o *porquê* daquela seção e o que o entrevistador está tentando descobrir, depois o raciocínio, e só então um exemplo de resposta. A ideia é que você aprenda a pensar a resposta, não a decorá-la — porque em entrevista real a pergunta nunca vem exatamente como você ensaiou.

---

## Por que este módulo vem primeiro

A primeira pergunta de quase toda entrevista é alguma variação de *"me fala um pouco sobre você"*. Ela parece informal, mas define o tom de tudo que vem depois.

**O que o entrevistador quer descobrir com essa pergunta:** ele não quer sua biografia. Ele quer, em poucos segundos, saber (1) onde te encaixar na stack dele, (2) se você tem experiência real ou só tutorial, e (3) se você comunica com clareza. Ele também está, sem dizer, decidindo **quais perguntas fazer a seguir** — e é aí que está sua chance.

**O que você precisa dominar nesta seção:**
- Contar sua história de forma curta e estruturada.
- Plantar "ganchos" — menções específicas que convidam a próxima pergunta para os temas onde você tem código real.
- Controlar o ritmo: dizer o suficiente para interessar, e parar.

A regra: você não está resumindo o currículo em voz alta. Você está escolhendo o terreno onde a conversa vai acontecer.

---

## Seu pitch de abertura

Estrutura em três blocos: quem você é → o que você construiu → o que você procura.

**Raciocínio antes do exemplo:** o pitch precisa abrir com a stack (para te posicionar), citar projetos com um gancho técnico distinto em cada um (para dar opções de aprofundamento ao entrevistador), e fechar com intenção (para mostrar direção). Números e conquistas entram com parcimônia — um dado forte bem colocado vale mais que três empilhados, que soam a autopromoção.

Exemplo de resposta:

> "Sou desenvolvedor backend Python, principalmente com Django e Django REST Framework. Meu projeto principal é o **Barber Cashflow**, um SaaS multi-tenant de gestão para barbearias que roda em produção com um cliente real usando no dia a dia. Também construí o **Nícia Track**, uma plataforma de estudos para concurso que fiz para uma usuária real — pesquisei o edital, organizei o conteúdo por matéria e montei os simulados — e que aproveitei para levar ao ar na AWS montando a infraestrutura peça por peça: EC2, RDS, S3, Nginx com HTTPS. E o **MOST**, um serviço de automação em FastAPI com Playwright que faz scraping de um portal público de forma assíncrona. O que me move é pegar um problema real e transformar em software que roda em produção. Estou procurando uma posição backend Python onde eu contribua com isso e cresça dentro de um time."

Por que funciona:
- **Abre com a stack** — o entrevistador já sabe onde te encaixar.
- **Cada projeto carrega um gancho técnico diferente** — multi-tenant, deploy AWS na mão, automação async. São três direções que ele pode escolher explorar, e todas são terreno seu.
- **O dado de negócio aparece uma vez** ("cliente real usando no dia a dia") e sem número inflado — o suficiente para separar você de quem só tem projeto de tutorial, sem soar a vendedor.
- **Fecha com intenção.**

Treine em voz alta até sair natural. O objetivo não é recitar — é ter os pontos tão internalizados que você improvisa a redação na hora e soa como conversa, não como texto decorado.

---

## Seus três projetos em uma frase cada

**Por que treinar isso:** entrevistadores frequentemente pedem "me dá um resumo rápido desse projeto". Se você começa a divagar, perde o controle. Uma frase densa e ensaiada te dá um ponto de partida firme, do qual você expande só quando pedirem.

O padrão de cada frase é sempre **o quê + a stack + o diferencial**. Nunca descreva um projeto só pelo "o quê" — sem a tecnologia e o diferencial, some o que te distingue.

**Barber Cashflow**
> "SaaS multi-tenant de gestão para barbearias, em Django + DRF + PostgreSQL, em produção — controla agendamentos, vendas, comissões, estoque e caixa, com isolamento total de dados entre barbearias e um assistente de IA baseado em RAG."

**Nícia Track**
> "Plataforma web de preparação para concurso, monolito Django com banco de questões, simulados e caderno de erros — construída para uma usuária real e que aproveitei para aprender deploy AWS de ponta a ponta."

**MOST**
> "Serviço de automação e web scraping em FastAPI + Playwright que consulta um portal público de forma assíncrona, com validação via Pydantic e tratamento de erros em camadas."

---

## Seu diferencial: a trajetória como decisão técnica

Aqui aplicamos, pela primeira vez, a estrutura padrão que vai se repetir no playbook inteiro sempre que houver uma decisão importante a defender. Sua própria trajetória é uma decisão que você precisa saber justificar.

### O que eu preciso saber explicar

**Por que essa trajetória (e não outra)?**
Porque cada projeto foi uma escolha consciente de descer um degrau na stack. Comecei resolvendo um problema de negócio real e colocando em produção (Barber). Depois quis entender a camada de infraestrutura que um PaaS esconde — e usei um produto que eu já estava construindo para uma usuária real, o Nícia Track, como oportunidade de montar um deploy AWS inteiro na mão. E aí fui para automação assíncrona com FastAPI, num problema onde o mundo externo — um portal instável — não coopera (MOST).

**Qual problema essa trajetória resolveu?**
O problema de quem é self-taught: provar competência sem um crachá de empresa grande. Em vez de acumular certificados, acumulei sistemas que funcionam, cada um forçando uma habilidade nova.

**Quais alternativas existiam?**
Poderia ter ficado só no Django, aprofundando o Barber indefinidamente. Teria mais profundidade num framework só, mas nenhuma vivência de infraestrutura nem de async. Escolhi amplitude com uma âncora sólida (Django/produção) em vez de especialização estreita.

**Quais vantagens isso trouxe?**
Consigo conversar sobre a requisição inteira — do DNS ao banco — e não só sobre a camada de aplicação. E tenho repertório para vagas diferentes: Django, FastAPI, infra AWS.

**Hoje eu faria igual?**
Em linhas gerais sim. Se mudasse algo, teria buscado mais cedo alguma forma de trabalho colaborativo — code review, contribuição a open source — porque é a lacuna que sinto hoje. Mas a ordem "produção primeiro, teoria depois" eu manteria.

**Qual foi o principal aprendizado?**
Que software real é sobre o que acontece quando as coisas dão errado — dados que não podem ser perdidos, um portal que fica instável, um deploy que quebra em produção mas não localmente. Tutorial nenhum ensina isso; só entra construindo algo que alguém usa.

### Como um CTO enxerga isso

Quando um CTO ouve sua trajetória, ele não está avaliando se você conhece muitas tecnologias. Ele está tentando descobrir:

- **Você toma decisões ou só segue tutoriais?** Uma trajetória com escolhas conscientes (e justificadas) sinaliza autonomia — o que ele mais precisa de alguém que vai trabalhar com pouca supervisão no começo.
- **Você aprende sozinho?** Self-taught que levou três projetos distintos à produção responde essa pergunta sem você precisar afirmar.
- **Você tem noção das suas lacunas?** Admitir a falta de vivência em time, sem se diminuir, é sinal de maturidade. Candidato que finge não ter lacuna nenhuma assusta mais do que tranquiliza.

Saber ler essa intenção muda sua resposta: em vez de listar tecnologias, você narra *decisões*.

---

## Como enquadrar a lacuna de experiência em time

**O que o entrevistador quer descobrir:** se você vai conseguir trabalhar em código de outras pessoas, aceitar review, seguir convenções de um time — coisas que trabalhar sozinho não exercita. É uma preocupação legítima, não uma armadilha.

**O que você precisa dominar:** transformar a lacuna em ponto de partida honesto, mostrando o que a autonomia te deu de bom e o que você espera ganhar no time.

Exemplo de resposta:

> "Trabalhei sozinho num sistema em produção, então desenvolvi a disciplina de quem não tem uma rede de segurança embaixo — escrevi testes de isolamento, usei transações atômicas onde a consistência importava, documentei o deploy para conseguir reproduzir. O que me falta é a parte de colaboração: review de código dos outros, trabalhar numa base grande que eu não escrevi, alinhar convenções com um time. É justamente o que me atrai nessa vaga."

Por que funciona: você não nega a lacuna nem se desculpa por ela. Você mostra que a ausência de time te forçou a desenvolver **disciplina técnica real**, e posiciona o time como o próximo passo natural, não como um buraco a tapar.

---

## Como conduzir a abertura da entrevista

Alguns princípios práticos para os primeiros minutos:

**Deixe ganchos e espere.** Depois do pitch, pare. Não despeje tudo. O entrevistador vai puxar um gancho ("me conta mais desse multi-tenant") e aí você aprofunda. Controlar o ritmo é, por si só, sinal de senioridade.

**Puxe para o Barber quando a pergunta for aberta.** É seu projeto mais completo. Para "me dá um exemplo de um problema difícil", ele quase sempre tem a melhor resposta.

**Seja preciso sobre o que você não usou.** Se a vaga cita Celery, Kubernetes ou qualquer coisa fora do seu repertório, diga que não usou, mas explique o conceito e por que a ferramenta existe. Isso mostra que você entende o problema que ela resolve — muito mais valioso do que fingir experiência. Inventar é o jeito mais rápido de perder credibilidade, porque um bom entrevistador cava exatamente onde você hesita.

---

## Checklist de domínio deste módulo

Você domina este módulo quando consegue, sem consultar nada:

- [ ] Falar seu pitch de abertura de forma natural, com um único dado de negócio bem colocado.
- [ ] Descrever cada projeto em uma frase densa (o quê + stack + diferencial).
- [ ] Defender sua trajetória usando a estrutura das seis perguntas (por quê / problema / alternativas / vantagens / faria igual / aprendizado).
- [ ] Explicar o que um CTO está de fato tentando descobrir na abertura.
- [ ] Enquadrar a lacuna de experiência em time sem se diminuir.

---

## Perguntas de abertura mais comuns

Para cada uma, o que o entrevistador busca e a direção da sua resposta.

**"Me fala sobre você."**
Busca: onde te encaixar + clareza de comunicação.
→ Seu pitch de abertura. Nada mais. Pare e deixe ele puxar o gancho.

**"Qual projeto você mais gostou de construir?"**
Busca: o que te motiva e onde você tem profundidade.
→ Barber, pela combinação problema real + desafio de arquitetura (multi-tenant). Ou MOST, se quiser sinalizar gosto por problemas técnicos difíceis.

**"Qual foi o problema mais difícil que você resolveu?"**
Busca: como você raciocina sob dificuldade, não a dificuldade em si.
→ Escolha um com história completa: consistência no cancelamento de venda (transação atômica), isolamento entre tenants, ou os bugs de produção do MOST (o `networkidle` que nunca terminava por causa de scripts de analytics do portal). Conte o problema, a hipótese, como investigou, a solução.

**"Por que você para essa vaga?"**
Busca: se você entende a vaga e se sua experiência conecta.
→ Amarre seu repertório ao que a vaga pede. Vaga Django → produção + multi-tenant. Cita AWS → deploy na mão. Remota/internacional → inglês fluente + autonomia comprovada.

**"Suas maiores forças e fraquezas?"**
Busca: autoconhecimento e honestidade.
→ Força: autonomia para levar algo do problema à produção. Fraqueza (honesta, sem armadilha disfarçada): pouca vivência em times grandes e em bases legadas de outras pessoas — exatamente o que você quer desenvolver agora.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- O pitch abre a stack, planta ganchos e fecha com intenção — nada mais.
- Meus três projetos formam uma narrativa de descida na stack: produção (Barber) → infra AWS na mão (Nícia Track) → automação async (MOST).
- Meu diferencial não é "muitas tecnologias", é "decisões conscientes e sistema em produção".

**Decisões técnicas mais importantes**
- Escolhi amplitude com âncora sólida (Django/produção) em vez de especialização estreita.
- Cada projeto foi escolhido para forçar uma habilidade nova (isolamento de dados, infraestrutura, async).

**Erros que devo evitar ao responder**
- Despejar tudo depois do pitch em vez de parar e deixar puxarem o gancho.
- Empilhar números e conquistas (soa a autopromoção) — um dado forte, uma vez.
- Fingir experiência que não tenho; explicar o conceito é melhor que inventar vivência.
- Pedir desculpa pela lacuna de time em vez de enquadrá-la como próximo passo.

**Tecnologias principais abordadas**
- Django + DRF + PostgreSQL (Barber); Django + AWS (Nícia Track); FastAPI + Playwright (MOST).

**Palavras-chave que devem aparecer naturalmente**
- backend Python, produção, multi-tenant, deploy AWS de ponta a ponta, assíncrono, autonomia, cliente real.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Quem sou em uma frase: dev backend Python (Django/DRF) com sistema em produção.
- ✓ Meus três projetos, cada um com seu gancho: multi-tenant, deploy AWS na mão, automação async.
- ✓ Minha trajetória como escolha consciente de descer degraus na stack.
- ✓ Meu diferencial: autonomia comprovada — do problema à produção, sozinho.
- ✓ Minha lacuna (time/colaboração) enquadrada como o que busco agora, sem me diminuir.
