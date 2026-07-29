# Estudo CI/CD — Material de Entrevista (Açaí da Rose)

> Material de revisão rápida (~30–40 min). Não é documentação nem tutorial.
> Objetivo: reter os 20% que respondem 80% das perguntas de entrevista sobre CI/CD.

---

# Objetivo

- Coloquei uma **trava automática** entre o código e a produção.
- **Antes:** `git push` disparava o deploy direto no Render, **sem rodar testes**.
- **Depois:** testes + lint precisam passar (CI verde) **antes** de qualquer deploy.
- Contexto real: sistema financeiro usado pela minha mãe (baixa familiaridade com tecnologia) — uma regressão em produção atrapalha o dia a dia da loja.

---

# Visão Geral

- **CI (Integração Contínua):** validar o código automaticamente a cada mudança (testes + lint), pegando regressões cedo, antes do merge/deploy.
- **CD (Entrega/Deploy Contínuo):** automatizar a entrega do código **já validado** para produção.
- **Problema que resolve:** eu tinha boa munição (≈296 testes + backup diário), mas **nenhuma trava** — código quebrado podia ir direto ao ar.
- **Como ficou no meu projeto:**
  - Push/PR → GitHub Actions roda Ruff (lint) + pytest (testes) + coverage (gate 80%).
  - Só com **CI verde** o job de deploy chama o **Deploy Hook** do Render.
  - **Branch protection** na `main` torna os checks obrigatórios (fecha o push direto).

**Regra central:** *deploy só acontece depois de CI verde.*

---

# Arquitetura Geral

```
Git Push / Pull Request
        ↓
   GitHub Actions (CI)
        ↓
   Lint + Format (Ruff)
        ↓
   Testes (pytest + Postgres service container)
        ↓
   Coverage (gate 80%)
        ↓
   Checks verdes? — NÃO → bloqueia merge / deploy
        ↓ SIM
   Deploy no Render (CD, via Deploy Hook)
        ↓
   Produção
```

**Cada etapa em poucas linhas:**

- **Git Push / PR:** gatilho do pipeline. Todo push e todo PR disparam a CI.
- **GitHub Actions:** orquestrador; sobe um runner Ubuntu e executa o workflow.
- **Ruff (lint + format):** checa estilo e erros estáticos; qualquer violação reprova o job.
- **pytest + Postgres container:** roda os ≈296 testes contra um Postgres real (espelha produção).
- **Coverage (gate 80%):** se a cobertura cair abaixo de 80%, o job fica vermelho.
- **Checks verdes?:** se algo falha, o deploy nem começa (`needs:` no job).
- **Deploy no Render:** job de deploy dá `curl` no Deploy Hook → Render faz build e publica.
- **Produção:** app no ar, só com código testado e no padrão.

---

# Tecnologias utilizadas

**GitHub Actions**
- O que é: plataforma de automação (CI/CD) integrada ao GitHub.
- Para que serve: rodar workflows (testes, lint, deploy) a cada evento do repo.
- Por que usei: já está no GitHub, é gratuito em repo público, workflow versionado no próprio repo.
- Quando se usa: CI/CD, automações agendadas (cron), tarefas disparadas por push/PR.

**Ruff**
- O que é: linter + formatador de Python escrito em Rust.
- Para que serve: apontar problemas (imports não usados, código morto) e padronizar formatação.
- Por que usei: substitui flake8 + isort + black numa ferramenta só, muito mais rápida e com menos config.
- Quando se usa: padronização de estilo e análise estática em projetos Python.

**pytest**
- O que é: framework de testes do Python.
- Para que serve: escrever e executar a suíte de testes.
- Por que usei: é a suíte já existente do projeto (≈296 testes).
- Quando se usa: testes unitários e de integração em Python.

**pytest-django**
- O que é: plugin do pytest para projetos Django.
- Para que serve: banco de teste, fixtures e integração com o ORM/settings do Django.
- Por que usei: o projeto é Django; facilita testar models, views e services.
- Quando se usa: sempre que se testa Django com pytest.

**Coverage (pytest-cov)**
- O que é: ferramenta que mede a cobertura de testes.
- Para que serve: medir quanto do código é exercitado pelos testes e aplicar um gate.
- Por que usei: garantir que a cobertura não caia (gate `--cov-fail-under=80`).
- Quando se usa: para impor um mínimo de qualidade de testes no CI.

**PostgreSQL Service Container**
- O que é: um Postgres efêmero que o Actions sobe ao lado do job.
- Para que serve: os testes rodarem contra o mesmo banco de produção (Postgres, não SQLite).
- Por que usei: evitar bugs que só aparecem em produção (tipos, migrations, SQL específico).
- Quando se usa: quando o CI precisa de um serviço real (banco, cache) isolado e descartável.

**Render Deploy Hook**
- O que é: uma URL secreta que dispara um deploy ao receber um POST.
- Para que serve: controlar **quando** publicar, em vez de publicar em todo push.
- Por que usei: permite deployar só depois da CI passar, sem trocar de plataforma.
- Quando se usa: quando se quer deploy sob demanda controlado por um pipeline.

**Render**
- O que é: plataforma de hospedagem (PaaS) da aplicação Django.
- Para que serve: rodar o app (gunicorn), executar `build.sh` (migrate, collectstatic) e publicar.
- Por que usei: já era a hospedagem do projeto (plano gratuito).
- Quando se usa: deploy simples de apps web sem gerenciar servidor.

**GitHub Secrets**
- O que é: armazenamento criptografado de credenciais no GitHub.
- Para que serve: guardar segredos (ex.: URL do Deploy Hook) fora do código.
- Por que usei: nunca expor segredos no repo; valores são mascarados nos logs (`***`).
- Quando se usa: qualquer credencial usada por workflows.

**GitHub Branch Protection**
- O que é: regras que protegem uma branch (ex.: `main`).
- Para que serve: exigir checks verdes (e/ou PR/review) antes do merge.
- Por que usei: tornar a CI **obrigatória**, fechando a brecha do push direto.
- Quando se usa: em branches importantes que não podem receber código quebrado.

---

# Conceitos importantes

- **CI (Integração Contínua):** validar código automaticamente a cada mudança (testes/lint) para pegar erros cedo.
- **CD (Entrega/Deploy Contínuo):** automatizar a entrega/deploy do código já validado.
- **Pipeline:** sequência automatizada de etapas do código até produção (lint → testes → deploy).
- **Workflow:** arquivo YAML que define o pipeline no GitHub Actions.
- **Job:** unidade do workflow que roda num runner (ex.: `test`, `deploy`).
- **Step:** cada comando/ação dentro de um job.
- **Runner:** máquina (VM Ubuntu) que executa o job; efêmera e descartável.
- **Service Container:** container auxiliar (ex.: Postgres) que o Actions sobe ao lado do job e derruba no fim.
- **Deploy Hook:** endpoint que dispara o deploy sob demanda.
- **Coverage:** percentual do código exercitado pelos testes; com gate, reprova se cair abaixo do limite.
- **Lint:** análise que aponta problemas no código (bugs simples, código morto, imports não usados).
- **Formatação:** reescrita do layout do código de forma consistente (ex.: Ruff format).
- **Análise estática:** inspecionar o código **sem executá-lo** para achar problemas.
- **Branch Protection:** regras que condicionam o merge a checks/revisão.
- **Required Status Checks:** jobs de CI marcados como obrigatórios para permitir o merge.
- **Health Check:** verificação de que um serviço (ex.: Postgres container) está pronto antes de usá-lo.
- **Secrets:** credenciais criptografadas e mascaradas nos logs.
- **`needs:` / `if:`:** dependência entre jobs e condição de execução (deploy só após testes, só na `main`).

---

# Decisões arquiteturais

**Por que GitHub Actions**
- Já integrado ao GitHub, gratuito em repo público, workflow versionado no repo.
- Trade-off: acopla o CI ao GitHub; menos flexível que Jenkins self-hosted, mas muito mais simples.

**Por que Ruff (no lugar de flake8 + black + isort)**
- Uma ferramenta só, muito mais rápida (Rust), menos config para manter num projeto pequeno.
- Trade-off: ferramenta mais nova; ecossistema de plugins menor que o do flake8.

**Por que Deploy Hook (e não auto-deploy)**
- Dá controle para deployar **só após a CI**; solução simples sem trocar de plataforma.
- `autoDeploy: false` no `render.yaml` desliga o deploy automático por push.
- Trade-off: exige um step extra no pipeline; em troca, elimina deploy de código quebrado.

**Por que PostgreSQL no CI (service container, não SQLite)**
- Espelha produção (Neon/Postgres); evita bugs específicos de banco (tipos, migrations, SQL).
- Trade-off: CI um pouco mais lento e complexo, mas muito mais confiável.

**Por que Coverage com gate de 80%**
- Impede que a cobertura caia silenciosamente ao longo do tempo.
- Reaproveitei o gate já existente no `pytest.ini` em vez de recriar.
- Trade-off: pode travar PRs por queda de cobertura; força manter testes em dia.

**Por que Branch Protection**
- Torna a CI **obrigatória**, não opcional; fecha a brecha do push direto na `main`.
- Trade-off: fluxo um pouco mais burocrático (via PR), mas garante `main` sempre saudável.

**Por que manter o backup separado do CI/CD**
- O `backup.yml` é **operacional** (cron diário), não faz parte do fluxo de entrega.
- Manter separado evita misturar responsabilidades no pipeline de deploy.

---

# Perguntas frequentes de entrevistas

**Básicas**

1. **O que é CI?** Integrar e validar código automaticamente a cada mudança (testes/lint), pegando regressões cedo.
2. **O que é CD?** Automatizar a entrega/deploy do código já validado para produção.
3. **Diferença entre CI e CD?** CI valida (testes/lint); CD entrega/deploya o que já foi validado.
4. **O que é um pipeline?** Sequência automatizada do código até produção (lint → testes → deploy).
5. **O que é GitHub Actions?** Plataforma de CI/CD do GitHub que roda workflows a cada evento do repo.
6. **Workflow, job e step?** Workflow é o YAML; job roda num runner; step é cada comando do job.
7. **O que é um runner?** A VM que executa o job; aqui, efêmera e descartável.
8. **O que é lint?** Análise estática que aponta problemas no código sem executá-lo.
9. **Diferença entre linter e formatador?** Linter aponta problemas; formatador padroniza o layout.
10. **O que é coverage?** Percentual do código coberto pelos testes.

**Intermediárias**

11. **Por que usar Postgres no pipeline em vez de SQLite?** Para espelhar produção e evitar bugs de banco (tipos, migrations, SQL específico).
12. **O que é um service container?** Container auxiliar (ex.: banco) que o Actions sobe ao lado do job e derruba no fim.
13. **O que é um health check nesse contexto?** Verifica se o Postgres container está pronto antes de os testes rodarem.
14. **Como o CI garante cobertura mínima?** `--cov-fail-under=80` faz o pytest falhar se a cobertura cair abaixo de 80%, reprovando o job.
15. **O que é um Deploy Hook?** URL secreta que dispara o deploy sob demanda ao receber um POST.
16. **O que é Branch Protection?** Regras que exigem checks/revisão antes do merge numa branch.
17. **O que são Required Status Checks?** Jobs de CI que precisam ficar verdes para o merge ser permitido.
18. **O que são GitHub Secrets?** Armazenamento criptografado de credenciais, mascarado nos logs.
19. **Como funciona `needs:` e `if:`?** `needs:` faz um job depender de outro; `if:` condiciona a execução (ex.: deploy só na `main` em push).
20. **Por que Ruff em vez de flake8 + black + isort?** Unifica as três, é muito mais rápido e reduz config.

**Cenário real**

21. **Como impedir deploy de código quebrado?** Deploy depende do job de testes (`needs:` + `if:`); se a CI falha, o hook nunca é chamado.
22. **Como garantir que só código testado vai a produção?** CI verde é pré-condição do deploy + branch protection tornando os checks obrigatórios.
23. **O que acontece num push com teste quebrado na `main`?** Job `test` fica vermelho → job `deploy` não roda → sem deploy.
24. **Quando NÃO usar deploy automático?** Quando quero controle sobre *quando* publicar (ex.: só após CI, ou em janela específica) — daí o Deploy Hook.
25. **Como validar o pipeline?** Abrir PR com teste quebrado de propósito → job vermelho; corrigir → job verde.
26. **Como reduzir a chance de bug só aparecer em produção?** Rodar os testes no mesmo banco (Postgres real) que a produção usa.
27. **Como o time evita que a cobertura caia com o tempo?** Gate de 80% no CI, que reprova o job se a cobertura baixar.
28. **Por que separar o workflow de backup do de CI/CD?** Backup é operacional (cron), não faz parte do fluxo de entrega.
29. **O que é rollback e como reagir a um deploy ruim?** Voltar para a versão anterior estável; com o histórico de deploys do Render, redeployar o commit bom.
30. **Qual foi o maior risco antes dessa implementação?** Deploy direto por push, sem testes — qualquer regressão ia ao ar.

---

# Como explicar essa implementação na entrevista

> "Eu tinha um sistema financeiro Django em produção no Render, com uma suíte de ≈296 testes e backup diário do banco — mas **nada** impedia que código quebrado fosse ao ar, porque o Render deployava direto a cada `git push`, sem rodar teste nenhum.
>
> Então montei um pipeline no **GitHub Actions**: a cada push ou PR, ele roda o **Ruff** (lint e formatação), sobe um **Postgres em service container** para os testes rodarem contra o mesmo banco da produção, executa o **pytest** e aplica um **gate de cobertura de 80%**. Se qualquer etapa falha, o job fica vermelho.
>
> Para o deploy, desliguei o auto-deploy do Render (`autoDeploy: false`) e criei um job de **deploy** que só roda **depois** do job de testes (`needs:`) e apenas em push na `main` (`if:`). Esse job chama um **Deploy Hook** do Render por `curl`. Ou seja, sem CI verde o hook nunca é chamado — não tem como deployar código quebrado.
>
> Por fim, adicionei **branch protection** na `main` com os checks como obrigatórios, o que fecha a última brecha: o push direto quebrando a suíte. A ideia central é simples: **deploy só acontece depois de CI verde.**"

---

# O que eu preciso lembrar

- **CI valida (testes/lint); CD entrega o código já validado.**
- CI roda a cada **push e PR**; deploy só na **`main`** (`needs:` + `if:`).
- Testes usam **Postgres em service container** para espelhar produção.
- **Gate de cobertura 80%** (`--cov-fail-under=80`) reprova o job se cair.
- **Ruff** = lint + formatação numa ferramenta (substitui flake8 + isort + black).
- **Deploy Hook** + `autoDeploy: false` = deploy sob demanda, só após CI.
- Sem **CI verde**, o hook nunca é chamado → sem deploy.
- **Branch protection** + **required status checks** tornam a CI obrigatória.
- **Secrets** guardam a URL do hook; mascarados nos logs.
- Backup (`backup.yml`) é **operacional** e fica **fora** do fluxo de CI/CD.

---

# Resumo Final

**O problema:** deploy direto por push, sem testes — o maior risco do projeto.

**A solução:** um pipeline no GitHub Actions que trava o caminho até produção em quatro camadas:

- **CI:** Ruff + pytest (em Postgres real) + coverage 80% a cada push/PR.
- **CD:** deploy no Render via Deploy Hook, só após a CI (`needs:` + `if:`), só na `main`.
- **Qualidade:** Ruff padroniza estilo e pega erros estáticos automaticamente.
- **Proteção:** branch protection torna os checks obrigatórios, fechando o push direto.

**Aprendizados centrais:**

- CI/CD é sobre **automatizar confiança**: cada mudança é validada antes de chegar ao usuário.
- O CI deve **espelhar produção** (Postgres real, não SQLite) para não esconder bugs.
- Deploy controlado por **hook** dá o poder de decidir *quando* publicar.
- **Cobertura e branch protection** transformam boas intenções em regras obrigatórias.
- A regra que resume tudo: **deploy só acontece depois de CI verde.**
