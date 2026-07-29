# Módulo 6 — Deploy e Infraestrutura

> Tempo de estudo: ~40–45 min
> Objetivo: defender suas decisões de infraestrutura — Docker, Nginx, Gunicorn, o caminho AWS, SSL — com foco no que te distingue: você não usou um PaaS que esconde tudo. Você montou o deploy na mão, entende a requisição do DNS ao banco, e resolveu problemas reais que só aparecem em produção.

---

## Como pensar este módulo

Infraestrutura é o tema onde a diferença entre "usei" e "entendo" fica mais visível. Muita gente diz que "faz deploy" clicando em botões de um PaaS. Você fez diferente: subiu numa EC2 crua, instalou o que precisava, configurou Nginx, emitiu SSL, e — o que mais conta — resolveu problemas que não existiam localmente. Essa é a sua vantagem aqui, e o módulo é construído em torno dela.

O que o entrevistador quer descobrir:
- Você entende o **caminho completo de uma requisição** (DNS → Nginx → Gunicorn → Django → banco)?
- Você sabe **por que** cada peça existe, ou só copiou um tutorial?
- Você já **debugou produção**? Problemas que só aparecem no ambiente real são a prova de fogo.

O que você precisa dominar:
- Docker: por que containerizar, cache de layers, o entrypoint.
- O trio Nginx + Gunicorn + Django e por que os três existem.
- O caminho AWS pensado em fases (EC2 → RDS → S3 → HTTPS).
- SSL/Certbot e a mecânica do HTTPS.
- Os obstáculos reais de produção que você resolveu no MOST — o material mais valioso do módulo.

Um enquadramento honesto que ajuda: você tem **dois níveis de experiência de deploy**. No Barber, um deploy conteinerizado com Nginx próprio, rate limiting, entrypoint flexível. No Nícia Track e no MOST, deploy na AWS EC2 com o fluxo completo montado à mão. Saber navegar entre os dois mostra amplitude.

---

## Docker

### O que é

Uma tecnologia de containerização: em vez de instalar Python, dependências e o app direto no servidor, você empacota tudo num container isolado que roda igual em qualquer lugar.

### Onde utilizei

Nos três projetos. O caso mais interessante de defender é o **MOST**, onde o Docker resolveu um problema concreto: eu já tinha o Nícia Track rodando numa EC2, na porta 8000. O MOST precisa de Playwright + Chromium, um conjunto pesado de dependências de sistema. Instalar isso direto na EC2 criaria conflito com o outro projeto. Com Docker, cada projeto tem seu container, suas versões, sua porta (o MOST foi para a 8001) e seu `.env` — total isolamento, zero conflito.

### Qual problema resolveu

Dois problemas: **paridade dev/produção** ("funciona na minha máquina" deixa de existir, porque o container é o mesmo) e **isolamento entre projetos** no mesmo servidor. O segundo foi o motivador real no MOST — dois projetos convivendo numa EC2 sem pisar um no outro.

### Por que escolhi essa solução

Porque containerizar dá reprodutibilidade e isolamento sem o custo de uma VM completa por projeto. E no caso do MOST, o Playwright em headless dentro do container se comporta idêntico ao local — validei isso antes do deploy rodando os testes com `HEADLESS=true`, o que me deu confiança de que o ambiente conteinerizado não traria surpresas.

### Detalhe técnico que vale saber: cache de layers

No Dockerfile eu copio o `requirements.txt` e instalo as dependências **antes** de copiar o código-fonte. A razão é o cache de layers do Docker: cada instrução vira uma camada cacheada. Como o código muda muito mais do que as dependências, colocar o `pip install` antes do `COPY . .` faz o Docker reaproveitar a camada de dependências quando só o código mudou — build muito mais rápido. Inverter essa ordem reinstalaria tudo a cada mudança de código.

### Alternativas

- **Instalar direto no servidor (sem Docker)**: mais simples para um projeto só, mas gera conflito quando há vários, e reintroduz o "funciona na minha máquina".
- **VM por projeto**: isolamento total, mas pesado e caro — Docker dá quase o mesmo isolamento com fração do custo.

### Quais vantagens trouxe

- Ambiente idêntico em dev e produção.
- Isolamento entre projetos na mesma EC2.
- Build rápido via cache de layers.

### Hoje eu faria igual?

Sim. Melhorias que anotei: **multi-stage build** (compilar numa imagem grande e rodar numa mínima, reduzindo o tamanho final), rodar como **usuário não-root** (segurança) e **healthchecks**. No MOST já usei healthcheck via Python no compose; estenderia isso.

### O que um CTO provavelmente perguntaria

- Por que Docker em vez de instalar direto?
- Por que copiar requirements antes do código? (Cache de layers.)
- Diferença entre `CMD` e `ENTRYPOINT`?
- O que é multi-stage build?

### Como responder em uma entrevista

**Objetiva:**
> "Uso Docker pra ter o mesmo ambiente em dev e produção e pra isolar projetos. No MOST isso foi decisivo: eu já tinha outro projeto na mesma EC2, e o MOST precisa de Playwright e Chromium, que são pesados. Com container, cada projeto tem sua porta, suas dependências e seu `.env`, sem conflito. No Dockerfile copio o requirements antes do código pra aproveitar o cache de layers — se só o código muda, não reinstala as dependências."

**Aprofundada:**
> "O ganho central é reprodutibilidade e isolamento sem o custo de uma VM por projeto. Validei que o Playwright headless dentro do container se comporta igual ao local antes de subir, rodando os testes com `HEADLESS=true`. As evoluções que faria são multi-stage build pra reduzir a imagem, usuário não-root por segurança e healthchecks — esse último já usei no compose do MOST."

---

## Nginx + Gunicorn + Django (por que os três)

Esta é a pergunta de infra mais comum, e a que melhor separa quem entende de quem repete. "Por que você não expõe o Django direto na internet?"

### Gunicorn — o que é e por que existe

Gunicorn é um servidor WSGI: o processo que recebe a requisição HTTP e chama o código Django. Ele existe porque o servidor de desenvolvimento do Django (`runserver`) **não é feito para produção** — é single-threaded, sem workers paralelos, não otimizado. Gunicorn roda múltiplos workers em paralelo (a recomendação é ~2×CPUs+1), o que permite atender várias requisições ao mesmo tempo.

### Nginx — o que é e por que existe

Nginx é um servidor web de alta performance que fica **na frente** do Gunicorn, como proxy reverso. A pergunta-chave: por que não deixar o Gunicorn direto na internet? Porque o Gunicorn é ótimo rodando código Python, mas não foi feito para lidar com o tráfego bruto da internet. Ele não tem, de fábrica:
- Servir arquivos estáticos com eficiência (isso não deve gastar um worker Python).
- Rate limiting.
- Terminação TLS/HTTPS.
- Proteção contra conexões lentas (slowloris).

O Nginx cuida disso tudo e passa para o Gunicorn só o que é dinâmico.

### Onde utilizei e como

No Barber, um `nginx.conf` próprio que faz bastante coisa além de proxy: serve estáticos com cache de 30 dias (sem passar pelo Python), aplica **rate limiting** diferenciado (5 req/min no login para conter brute force, 10 req/s na API), e bloqueia bots. O entrypoint sobe o Gunicorn com 3 workers.

No MOST, o Nginx na EC2 faz o proxy reverso `mostqi.paulodev.net` → `127.0.0.1:8001`, decidindo o destino pelo `server_name` — é isso que permite dois projetos (Nícia Track na 8000, MOST na 8001) coexistirem atrás do mesmo Nginx, cada um no seu domínio.

### O fluxo completo (saber desenhar isto vale ouro)

```
Cliente → DNS resolve o domínio → IP da EC2
   ↓ HTTPS (443)
Nginx → termina o SSL, aplica rate limit, serve estáticos direto
   ↓ HTTP (proxy_pass para a porta do container)
Gunicorn → distribui entre workers
   ↓
Django → view → service → ORM
   ↓ TCP 5432 (rede interna)
PostgreSQL (RDS)
```

### Dois detalhes que impressionam

**`proxy_read_timeout`**: o timeout padrão do Nginx é 60s. No MOST, o robô pode levar até 90s (ou mais no cenário com filtro social). Sem ajustar o timeout, o Nginx cancelava a requisição e devolvia **504** antes de o robô terminar. Aumentei para 120s (e depois 300s no cenário pesado). Esse é um problema que *só aparece em produção* — localmente, sem a latência da EC2 ao portal, nunca acontecia.

**Headers de proxy** (`X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`): sem eles, o Django veria toda requisição como vinda de `127.0.0.1` (o próprio Nginx), perdendo o IP real do cliente. O `X-Forwarded-Proto` também é o que diz ao Django que o Nginx já cuidou do HTTPS — sem ele, dá para cair em loop de redirecionamento.

### O que um CTO provavelmente perguntaria

- Por que não expor o Django (Gunicorn) direto na internet?
- Qual a diferença entre `runserver` e Gunicorn?
- Rate limiting no Nginx ou na aplicação — onde e por quê?
- O que os headers `X-Forwarded-*` fazem?

### Como responder em uma entrevista

**Objetiva:**
> "O Django com Gunicorn roda o código, mas não foi feito pra encarar a internet direto. O Nginx fica na frente como proxy reverso: termina o SSL, serve estáticos sem gastar worker Python, faz rate limiting e proteção contra conexão lenta, e passa pro Gunicorn só o que é dinâmico. No Barber, por exemplo, limito o login a 5 requisições por minuto no Nginx pra conter brute force. O Gunicorn roda vários workers em paralelo, coisa que o `runserver` não faz."

**Aprofundada:**
> "Um detalhe que aprendi na prática: no MOST o robô pode levar 90 segundos, e o timeout padrão do Nginx é 60 — então ele cortava a requisição e devolvia 504. Ajustei o `proxy_read_timeout`. Esse tipo de problema só aparece em produção, com a latência real. Também configuro os headers `X-Forwarded-*` pro Django enxergar o IP real do cliente e saber que o Nginx já tratou o HTTPS — sem o `X-Forwarded-Proto`, dá pra cair em loop de redirect. E o mesmo Nginx serve dois projetos na EC2, roteando por `server_name` pra portas de container diferentes."

---

## O caminho AWS pensado em fases

### O que é

Em vez de tentar montar toda a infraestrutura de uma vez, planejei o deploy AWS do Nícia Track em fases incrementais, cada uma entregando algo que funciona de ponta a ponta antes de adicionar a próxima camada de complexidade.

### Onde utilizei

No roadmap do Nícia Track:

```
Fase 1 — App rodando na EC2 via Docker (HTTP simples)
Fase 2 — Banco no RDS PostgreSQL
Fase 3 — Static e media files no S3
Fase 4 — Nginx + domínio + HTTPS
Fase 5 — Segurança, custos, logs, monitoramento
```

### Qual problema resolveu

O risco de montar tudo de uma vez e não saber o que quebrou. Se eu subisse EC2 + RDS + S3 + Nginx + SSL simultaneamente e a aplicação não respondesse, teria cinco suspeitos. Fazendo em fases, cada etapa valida uma peça: primeiro o container sobe na EC2 e responde por HTTP; só então troco o banco pelo RDS; só então movo arquivos para o S3; e assim por diante. Cada fase tem um critério de conclusão objetivo.

### Por que escolhi essa solução

Porque é a forma de aprender e depurar ao mesmo tempo. Cada componente da AWS — EC2, RDS, S3, Security Groups, IAM — é um conceito novo. Introduzi-los um por vez me deixou entender cada um de verdade, em vez de ter um sistema-caixa-preta que "funciona" sem eu saber por quê.

### Peças da AWS e o "por quê" de cada uma

- **EC2**: a máquina virtual onde tudo roda. Escolhi ela (em vez de um PaaS) justamente para ter controle e aprender o que roda embaixo.
- **RDS**: PostgreSQL gerenciado. Por que não rodar o Postgres na própria EC2? Porque o RDS dá backups automáticos, snapshots e métricas — e se a EC2 tiver problema, o banco não vai junto. Dados persistentes pedem essa confiabilidade.
- **S3**: armazenamento de arquivos. Resolve um problema real do Docker: media files (avatares) salvos no container **somem a cada redeploy**, porque o container é recriado. No S3, sobrevivem. E permite múltiplas instâncias servindo os mesmos arquivos.
- **Security Groups**: firewall virtual. O ponto de segurança que impressiona: o Security Group do RDS aceita conexão **só** do Security Group da EC2, na porta 5432. O banco nunca fica acessível pela internet — só a EC2 chega nele.
- **IAM**: controle de acesso, com princípio do menor privilégio — um usuário que só precisa de S3 não recebe acesso a mais nada.

### Hoje eu faria igual?

O modelo em fases, sim — é o que torna o deploy compreensível. Numa evolução para produção séria, os próximos passos seriam trocar o `.env` em disco por AWS Secrets Manager, separar as migrations do startup do container (para escalar horizontalmente sem rodar migration em cada réplica) e adicionar um load balancer. Mas para o estágio de laboratório, a arquitetura simplificada cobre todos os conceitos fundamentais.

### Como um CTO enxerga isso

Ele quer saber se você entende infraestrutura como sistema, não como receita. Descrever o caminho em fases mostra pensamento incremental (uma habilidade de engenharia em si), e explicar por que o RDS é separado da EC2, ou por que o Security Group do banco só aceita a EC2, prova que você pensa em confiabilidade e segurança — não só em "fazer funcionar".

### O que um CTO provavelmente perguntaria

- Por que RDS em vez de rodar Postgres na EC2?
- Por que os media files precisam do S3 num deploy conteinerizado?
- Como você garante que o banco não é acessível pela internet?
- O que é o princípio do menor privilégio no IAM?

### Como responder em uma entrevista

**Objetiva:**
> "Montei o deploy AWS do Nícia Track em fases: primeiro o container rodando na EC2 por HTTP, depois o banco no RDS, depois os arquivos no S3, e por fim Nginx com HTTPS. Fiz incremental pra validar cada peça isoladamente e pra entender cada serviço de verdade, em vez de subir tudo de uma vez e não saber o que quebrou."

**Aprofundada:**
> "Cada peça resolve um problema específico. O RDS eu uso em vez de Postgres na EC2 porque dá backup automático e sobrevive a um problema na EC2 — dados persistentes pedem isso. O S3 resolve um problema concreto do container: avatar salvo no disco do container some no redeploy, no S3 não. E a segurança fica no Security Group: o do RDS só aceita conexão do Security Group da EC2, então o banco nunca é acessível pela internet. No IAM sigo o menor privilégio — cada credencial só tem o que precisa. Pra produção séria, os próximos passos seriam Secrets Manager e separar as migrations do startup pra escalar horizontal."

---

## SSL / HTTPS com Certbot

### O que é

Certbot é a ferramenta que emite certificados SSL gratuitos da Let's Encrypt, habilitando HTTPS. Sem HTTPS, senhas e dados trafegam em texto puro — inaceitável em produção.

### Onde utilizei

No MOST (e no Nícia Track, mesmo padrão na mesma EC2). O Certbot emitiu o certificado para `mostqi.paulodev.net` e configurou o Nginx para HTTPS automaticamente.

### O detalhe que mostra entendimento: o HTTP-01 challenge

Para emitir o certificado, a Let's Encrypt precisa provar que você controla o domínio. O método HTTP-01 funciona assim: o Certbot cria um arquivo temporário na EC2, e a Let's Encrypt tenta acessá-lo via `http://seu-dominio/.well-known/...`. Se conseguir ler, o domínio está validado.

Aqui está a sutileza que eu vivi: o domínio estava no Cloudflare com proxy ativado. Com o proxy ligado, o Cloudflare intercepta a requisição e a Let's Encrypt não chega direto na EC2 — a validação falha. A solução foi colocar o Cloudflare em modo **"DNS only"** durante a emissão, para o desafio HTTP chegar direto à porta 80 da EC2. Entender *por que* o proxy precisa sair é o que separa quem seguiu um tutorial de quem entende o mecanismo.

### Renovação automática

Certificados Let's Encrypt expiram em 90 dias. O Certbot agenda uma tarefa que renova automaticamente antes do vencimento — sem intervenção manual. Dá para validar com `certbot renew --dry-run`.

### O que um CTO provavelmente perguntaria

- Como funciona a emissão de um certificado SSL?
- O que é o HTTP-01 challenge?
- Por que o proxy do Cloudflare atrapalha a validação?
- Como você lida com a expiração do certificado?

### Como responder em uma entrevista

**Objetiva:**
> "Uso Certbot com Let's Encrypt pra provisionar o HTTPS. Ele valida o domínio via HTTP-01 challenge — cria um arquivo na EC2 que a Let's Encrypt tenta acessar. Um detalhe: o domínio estava no Cloudflare com proxy, e eu tive que pôr em 'DNS only' durante a emissão, senão o Cloudflare interceptava e a validação falhava. Depois de emitir, o Certbot configura o Nginx pra HTTPS e agenda renovação automática a cada 90 dias."

---

## Os obstáculos reais de produção (o material mais valioso)

> Se houver uma coisa deste módulo para levar para a entrevista, é esta. Contar um bug de produção que você diagnosticou e resolveu vale mais que qualquer definição, porque prova que você já operou um sistema real. Todos estes são do MOST.

**O `networkidle` que nunca terminava.** Localmente, eu esperava a página carregar com `wait_for_load_state("networkidle")` — que aguarda a rede ficar ociosa. Em produção, a requisição travava indefinidamente. Causa: o portal tem scripts de analytics rodando em background *sem parar*, então a rede nunca ficava ociosa e o `networkidle` nunca disparava. Solução: troquei por `domcontentloaded` + espera por um seletor específico. **Lição:** uma estratégia de espera que funciona num site simples pode travar num site com telemetria contínua.

**O 504 no cenário pesado.** Já contado acima — o robô ultrapassava o `proxy_read_timeout` do Nginx no fluxo com filtro social. Resolvido aumentando o timeout, sem rebuildar o container.

**O falso positivo do "0 resultados".** O seletor de texto do Playwright faz busca por substring. Quando o portal exibia "10.000 resultados", o texto continha "0 resultados" dentro, e o robô achava que não havia resultado. Descobri salvando um screenshot em disco, que mostrou 10.000 resultados enquanto a API retornava erro. Solução: usar o texto completo que só aparece quando *de fato* não há resultado. **Lição:** o valor de instrumentar (screenshot de debug) para enxergar o que o robô "vê".

**O timeout de 30s vs o WAF da AWS.** Localmente 30s bastavam. Na EC2, o WAF da AWS adiciona latência para IPs de servidor, e 30s não davam. Aumentei para 90s via `.env`. **Lição:** o ambiente de produção tem características de rede que o local não tem.

O padrão que une todos: **problemas que não existem localmente e só aparecem em produção.** Saber contar um desses, com causa e solução, é a prova mais convincente de senioridade prática que você pode dar.

---

## Deploy seguro com cliente em produção (a estratégia do Barber)

> Esta é uma das respostas mais valiosas do módulo, porque responde direto a uma pergunta que cai muito: *"como você faz deploy sem quebrar produção?"* — e você tem uma resposta vivida, não teórica.

### O contexto

O Barber tinha uma característica que muda tudo: **já havia um cliente usando o sistema todo dia**. Quando o projeto virou SaaS no meio do desenvolvimento (a história de produto está no Módulo 8), qualquer erro em produção deixou de ser um inconveniente e passou a ter impacto direto na operação da barbearia. Isso me obrigou a criar um processo de deploy que protegesse o cliente.

### A estratégia (três camadas de proteção)

**1. Pipeline de ambientes: local → homologação → produção.**
Toda funcionalidade era desenvolvida e testada primeiro **localmente**, na minha máquina. Antes de publicar qualquer alteração, eu validava num **ambiente de homologação o mais próximo possível da produção** — para pegar problemas que só apareceriam num ambiente realista. Só depois dessa validação a atualização ia para **produção**. Essa separação é o que evita o clássico "funcionou no meu computador" chegar ao cliente.

**2. Deploy de features grandes em janela de baixo risco.**
Quando a alteração era maior ou mais sensível, eu subia **no fim de semana ou fora do horário de funcionamento da barbearia**. A lógica é de gestão de risco: se algo desse errado, eu teria tempo de identificar, corrigir e validar a solução antes do próximo expediente — minimizando qualquer impacto para o cliente. É um deploy pensado em torno do calendário do negócio, não só do código.

**3. Comunicação constante com o cliente.**
Durante todo o desenvolvimento, mantive contato frequente com o cliente: avisando sobre atualizações, sobre possíveis indisponibilidades momentâneas, e coletando feedback. Isso teve dois efeitos — reduziu o atrito quando algo precisava de manutenção (o cliente sabia o que esperar) e me ajudou a priorizar melhorias que realmente resolviam o dia a dia da barbearia.

### Por que isso impressiona numa entrevista

Porque é raro um candidato júnior/pleno ter operado um sistema com um cliente real dependendo dele. Essa resposta mostra que você entende que deploy não é só `git push` — é gestão de risco, timing e comunicação. Um CTO ouve isso e pensa "essa pessoa não vai derrubar minha produção na sexta à noite".

E é honesto sobre a escala: você não tinha um pipeline de CI/CD automatizado com blue-green deployment — tinha um processo manual, disciplinado e adequado ao contexto (um cliente, uma barbearia). Reconhecer isso, e saber qual seria a evolução, é o que fecha a resposta com maturidade.

### Como um CTO enxerga isso

A pergunta "como você faz deploy sem quebrar produção?" é um teste de maturidade operacional. O CTO quer saber se você pensa nas consequências de um deploy ruim. A resposta fraca é técnica demais ("uso Docker"). A resposta forte mostra que você pensa no *cliente*: ambiente de validação antes de produção, timing de baixo risco, e comunicação. Você tem as três.

### Como responder em uma entrevista

**Objetiva:**
> "No Barber eu já tinha um cliente usando todo dia, então erro em produção parava a barbearia. Meu processo tinha três camadas: desenvolvia e testava local, validava num ambiente de homologação próximo da produção, e só então subia. Features grandes eu subia no fim de semana, com a barbearia fechada, pra ter tempo de corrigir sem impacto. E mantinha contato constante com o cliente sobre atualizações e possíveis indisponibilidades."

**Aprofundada (evolução):**
> "Era um processo manual e disciplinado, adequado ao contexto de um cliente. Numa escala maior, a evolução natural seria automatizar isso: um pipeline de CI/CD rodando os testes automaticamente, deploy com estratégia de zero-downtime, e separar as migrations do startup pra poder escalar horizontal. Mas o princípio — validar num ambiente realista antes de produção e minimizar o risco pro usuário — seria o mesmo."

### O que evitar ao contar

- Não diga "mesmo banco de produção" para o ambiente de homologação — testar direto no banco de produção é um antipadrão, e um entrevistador atento vai questionar. Diga "ambiente próximo da produção".
- Não venda como um pipeline sofisticado. A força da história está na disciplina e no cuidado com o cliente, não em ferramentas.

---

## Checklist de domínio deste módulo

- [ ] Explicar por que Docker (paridade + isolamento) e o truque do cache de layers.
- [ ] Justificar o trio Nginx + Gunicorn + Django — por que não expor o Django direto.
- [ ] Desenhar o fluxo completo DNS → Nginx → Gunicorn → Django → RDS.
- [ ] Explicar o caminho AWS em fases e o porquê de cada serviço (RDS, S3, Security Group, IAM).
- [ ] Explicar o HTTP-01 challenge e por que o proxy do Cloudflare precisa sair.
- [ ] Contar pelo menos um obstáculo real de produção com causa e solução.
- [ ] Explicar a estratégia de deploy seguro do Barber (homologação → produção, janela de baixo risco, comunicação).

---

## Perguntas comuns

**"Por que Docker?"** → Busca: paridade + isolamento. Exemplo dos dois projetos na mesma EC2.

**"Por que não expor o Django direto?"** → Busca: se você entende o papel do Nginx. Estáticos, rate limit, TLS, proteção — Gunicorn não faz isso.

**"Por que RDS e não Postgres na EC2?"** → Busca: se você pensa em confiabilidade. Backup automático, sobrevive à EC2.

**"Como o banco fica protegido?"** → Busca: consciência de segurança de rede. Security Group do RDS só aceita a EC2.

**"Me conta um problema de produção que você resolveu."** → Busca: experiência real. O `networkidle`, o 504, o falso positivo do "0 resultados".

**"Como você faz deploy sem quebrar produção?"** → Busca: maturidade operacional. Ambiente de homologação antes de produção, features grandes em janela de baixo risco (fim de semana), comunicação com o cliente.

---

## Revisão Rápida (5 minutos)

*Leia isto se sua entrevista começa em cinco minutos.*

**Conceitos que não posso esquecer**
- Docker: paridade dev/prod + isolamento. No MOST, dois projetos na mesma EC2 (portas 8000 e 8001) sem conflito. Cache de layers = requirements antes do código.
- Trio: **Gunicorn** roda o código (vários workers); **Nginx** na frente faz estáticos, rate limit, TLS, proxy. Django não encara a internet direto.
- Fluxo: DNS → Nginx (443, termina SSL) → Gunicorn (porta do container) → Django → RDS (5432, rede interna).
- AWS em fases: EC2 → RDS → S3 → HTTPS. RDS separado da EC2 (backup, sobrevive à EC2). S3 porque media no container some no redeploy. Security Group do RDS só aceita a EC2.
- SSL: Certbot + HTTP-01 challenge; Cloudflare em "DNS only" durante a emissão; renovação automática a cada 90 dias.
- **Deploy seguro (Barber)**: local → homologação (perto da produção) → produção; features grandes no fim de semana; comunicação com o cliente. Cliente usava todo dia — erro parava a barbearia.

**Decisões técnicas mais importantes**
- Docker no MOST pra isolar do outro projeto na mesma EC2.
- Nginx na frente do Gunicorn por segurança e eficiência.
- AWS incremental pra validar cada peça e entender cada serviço.
- Deploy pensado em gestão de risco (timing + validação + comunicação), não só `git push`.

**Erros que devo evitar ao responder**
- Dizer que "faço deploy" sem explicar o papel de cada peça.
- Confundir Nginx e Gunicorn (um é proxy/web server, o outro é WSGI que roda o código).
- Esquecer o ângulo de segurança de rede (Security Group do banco).
- Não ter na ponta da língua um bug de produção real.
- Dizer que o ambiente de homologação usava "o mesmo banco de produção" — antipadrão; diga "ambiente próximo da produção".

**Tecnologias principais abordadas**
- Docker / Docker Compose, Nginx (proxy reverso, rate limiting, `proxy_read_timeout`, headers), Gunicorn (workers WSGI), AWS (EC2, RDS, S3, Security Groups, IAM), Certbot/Let's Encrypt, Cloudflare (DNS).

**Palavras-chave que devem aparecer naturalmente**
- container, paridade dev/prod, cache de layers, proxy reverso, WSGI, workers, rate limiting, `proxy_read_timeout`, X-Forwarded-Proto, EC2, RDS, S3, Security Group, menor privilégio, HTTP-01 challenge, DNS only, renovação automática, 504, networkidle.

---

## Resumo para Entrevista (30 segundos)

*Se este módulo fosse resumido em 30 segundos, preciso conseguir explicar:*

- ✓ Por que Docker (paridade + isolamento), com o caso dos dois projetos na mesma EC2.
- ✓ Por que Nginx fica na frente do Gunicorn, e desenhar o fluxo DNS → Nginx → Gunicorn → Django → RDS.
- ✓ O caminho AWS em fases e o porquê de RDS, S3 e Security Group.
- ✓ O HTTP-01 challenge e por que o Cloudflare precisa ficar em "DNS only" na emissão.
- ✓ Pelo menos um obstáculo real de produção (o `networkidle`, o 504) com causa e solução.
