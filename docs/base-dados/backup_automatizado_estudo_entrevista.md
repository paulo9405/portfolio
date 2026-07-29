# Backup Automático do Banco → Google Drive — Guia de Estudo para Entrevistas

> Material de revisão rápida (~10–15 min). Não é documentação nem tutorial.
> Objetivo: relembrar toda a implementação e conseguir explicá-la a um Tech Lead.

---

## Resumo em 60 segundos

- **Problema:** não havia backup independente da infraestrutura (Render efêmero + Neon com retenção curta, sem servidor sempre ligado).
- **Solução:** GitHub Actions + pg_dump + gzip + rclone + Google Drive.
- **Resultado:** backup diário automatizado, retenção de 15 versões e custo zero.
- **Aprendizados:** GitHub Actions, PostgreSQL, Bash, automação, GitHub Secrets e integração entre serviços.

---

## 1. Objetivo da implementação

**Problema:** o sistema roda no **Render (free)** com banco no **Neon (Postgres serverless)**. Nenhum dos dois dá uma cópia de segurança confiável no meu controle: o Render tem filesystem **efêmero** (arquivo salvo some no próximo deploy) e **não tem cron** no plano free; o Neon free só retém histórico por algumas horas e não gera cópia no meu Google Drive. Também **não existe servidor sempre ligado** para rodar um cron tradicional.

**Por que resolver:** sem backup independente, uma corrupção, exclusão acidental ou encerramento do serviço poderia significar **perda total do histórico financeiro** da loja, sem recuperação.

**Solução escolhida:** backup **diário automatizado via GitHub Actions**, que conecta no Neon com `pg_dump`, comprime com `gzip`, envia ao Google Drive com `rclone` e mantém os 15 backups mais recentes (rotação). Roda 24/7 sem depender do meu notebook.

**Por que é melhor que as alternativas:**
- **Cron no meu notebook:** só roda com a máquina ligada → risco de pular dias.
- **Backup nativo do Neon (PITR/branch):** retenção curta no free e não gera cópia no Drive.
- **Render Cron Job:** indisponível no plano free.
- **GitHub Actions:** gratuito, sempre disponível, secrets nativos e o workflow fica versionado no próprio repo.

---

## 2. Arquitetura da solução

```
Aplicação Django (Render)
        ↓ usa
Neon (PostgreSQL 18.4)
        ↓ agendado por cron
GitHub Actions (runner ubuntu-latest, efêmero)
        ↓
pg_dump  → conecta no endpoint DIRETO do Neon e gera o dump SQL
        ↓
gzip     → comprime: acai_backup_AAAA-MM-DD_HHMMSS.sql.gz
        ↓
rclone   → faz upload para o Google Drive (OAuth)
        ↓
Google Drive (pasta acai-backups/)
        ↓
Rotação automática → mantém os 15 mais recentes, apaga o resto
```

**Responsabilidade de cada etapa:**
- **Neon:** hospeda o Postgres de produção; é a fonte dos dados.
- **GitHub Actions:** orquestrador — dispara tudo no horário certo, sem servidor próprio.
- **pg_dump:** extrai um backup lógico (SQL) do banco.
- **gzip:** reduz o tamanho do arquivo.
- **rclone:** transporta o arquivo até o Google Drive, gerenciando a autenticação OAuth.
- **Google Drive:** armazenamento durável (única cópia que sobrevive — o runner é descartado).
- **Rotação:** controla o crescimento, mantendo só os 15 backups mais novos.

Ordem obrigatória: **criar → validar → enviar → confirmar upload → só então rotacionar.**

---

## Palavras-chave

`GitHub Actions` · `Workflow` · `Runner` · `Cron` · `workflow_dispatch` · `GitHub Secrets` · `PostgreSQL` · `pg_dump` · `Backup lógico` · `Neon` · `Endpoint direto` · `PgBouncer` · `rclone` · `OAuth` · `Refresh Token` · `Google Drive` · `Rotação` · `Disaster Recovery` · `CI/CD`

---

## Como explicar esse projeto em 2 minutos

> "Implementei um sistema de backup automatizado para uma aplicação Django em produção, hospedada no Render com banco PostgreSQL no Neon. Como o Render Free não possui cron jobs e o filesystem é efêmero, utilizei **GitHub Actions** para executar diariamente um workflow que gera um backup lógico com **pg_dump**, compacta com **gzip**, envia ao **Google Drive** usando **rclone** e mantém automaticamente apenas os **15 backups mais recentes**. Todas as credenciais ficam no **GitHub Secrets**, e a solução funciona sem depender de um servidor dedicado ou do meu computador ligado."

Pontos que posso acrescentar se perguntarem mais:
- Uso o **endpoint direto** do Neon (o pooler/PgBouncer é incompatível com o `pg_dump`).
- A **rotação só roda após validar o upload**, para nunca apagar um backup antigo sem garantir o novo.
- O `rclone` usa **OAuth com refresh token**, então renova o acesso sozinho, sem reautenticação manual.

---

## 3. Decisões técnicas importantes

- **GitHub Actions em vez de servidor/cron local:** não há máquina sempre ligada. Actions é gratuito (repo público = minutos ilimitados), sempre disponível e versiona o workflow no repo.
- **Google Drive em vez de S3/Backblaze:** já existe, 15 GB grátis, sem cadastro/cartão/IAM. Para backup pessoal de pequeno porte, a simplicidade vence.
- **Endpoint direto do Neon (sem `-pooler`):** o pooler (PgBouncer) é para conexões curtas da app e é incompatível com `pg_dump`, que precisa de conexão direta ao Postgres. Usar o pooler dá erro de autenticação.
- **pg_dump:** ferramenta oficial de backup lógico do Postgres — portátil e restaurável em qualquer instância.
- **SQL puro + gzip em vez de formato custom (`-Fc`):** restaura com um simples `gunzip | psql`, sem precisar de `pg_restore`. Mais simples numa emergência e legível em qualquer editor.
- **GitHub Secrets para credenciais:** connection string e config do rclone ficam criptografadas e **mascaradas** nos logs (`***`), nunca no código.
- **Manter 15 backups:** ~15 dias de histórico cobrem a maioria dos cenários; com dumps de ~200 KB, ocupam <3 MB no Drive. Bom equilíbrio cobertura × espaço.

---

## 4. Fluxo da implementação (ordem em que foi construído)

1. **Estudo da infraestrutura** — confirmar stack (Django/Render/Neon), versão do Postgres (18.4), endpoint direto vs pooler, repo público.
2. **Script de backup** (`scripts/backup_database.sh`) — gera o `.sql.gz` a partir do `NEON_DATABASE_URL`.
3. **Configuração dos Secrets** — `NEON_DATABASE_URL` e `RCLONE_CONFIG` no GitHub.
4. **Workflow** (`.github/workflows/backup.yml`) — instala dependências, roda o script, configura rclone.
5. **Upload para o Google Drive** — `rclone copy` + validação de que o arquivo chegou.
6. **Rotação automática** — apaga os excedentes, só depois de confirmar o upload.
7. **Testes** — disparo manual, verificação de integridade e restore.

---

## 5. Tecnologias utilizadas

| Tecnologia | Função na arquitetura |
|---|---|
| **GitHub Actions** | Orquestrador do backup; executa o workflow diariamente sem servidor próprio. |
| **Workflow (`backup.yml`)** | Arquivo YAML versionado que define os steps do backup. |
| **GitHub Runner (`ubuntu-latest`)** | VM temporária e descartável onde o workflow roda; nada persiste entre execuções. |
| **Cron** | Agendador (`0 6 * * *`) que dispara o workflow todo dia às 06:00 UTC (03:00 BRT). |
| **workflow_dispatch** | Gatilho de execução manual pelo botão "Run workflow" (usado nos testes). |
| **GitHub Secrets** | Guarda credenciais criptografadas e mascaradas nos logs. |
| **PostgreSQL 18.4** | Banco de dados da aplicação. |
| **Neon** | Serviço gerenciado que hospeda o Postgres (com endpoint direto e pooler). |
| **pg_dump (18, PGDG)** | Gera o backup lógico (SQL) do banco. |
| **PGDG** | Repositório APT oficial do Postgres; fonte do `pg_dump` 18 no runner. |
| **gzip** | Comprime o dump via pipe, sem arquivo intermediário em disco. |
| **rclone** | Faz o upload ao Google Drive e gerencia o token OAuth. |
| **Google Drive** | Destino durável dos backups (pasta `acai-backups/`). |
| **Bash** | Linguagem do script de backup (`set -euo pipefail`). |
| **`scripts/backup_database.sh`** | Cria e valida o dump; portátil (roda local ou no CI). |
| **`$GITHUB_ENV` / `$GITHUB_PATH`** | Arquivos do runner para compartilhar variáveis e PATH entre steps. |

---

## 6. Principais dificuldades encontradas

### Incompatibilidade de versão do pg_dump

**Problema:** o `pg_dump` 16 (padrão do runner) recusa conectar num servidor Postgres 18 — a ferramenta não pode ser mais antiga que o servidor.
**Como descobri:** falha na primeira execução com erro de "server version mismatch".
**Como resolvi:** instalei o `postgresql-client-18` do repositório oficial **PGDG** e adicionei `/usr/lib/postgresql/18/bin` ao `$GITHUB_PATH`.

### PATH do GitHub Actions

**Problema:** mesmo após instalar o pg_dump 18, o binário 16 continuava na frente na PATH.
**Como descobri:** o step seguinte ainda usava a versão errada; `export PATH=...` dentro de um step não persistia para o próximo.
**Como resolvi:** escrevi o caminho no arquivo `$GITHUB_PATH`, que o runner carrega automaticamente antes de cada step subsequente.

### Endpoint pooler do Neon

**Problema:** usar a connection string com `-pooler` (a mesma da app) fazia o `pg_dump` falhar.
**Como descobri:** erro "password authentication failed" — o PgBouncer tem regras de auth diferentes e é incompatível com features do `pg_dump`.
**Como resolvi:** usei o **endpoint direto** do Neon (sem `-pooler`) no secret `NEON_DATABASE_URL`.

### GitHub Secrets multiline

**Problema:** colar o `rclone.conf` (multiline, com token) pela interface web falhava silenciosamente.
**Como descobri:** o rclone não autenticava no runner apesar do secret "estar lá".
**Como resolvi:** usei o GitHub CLI (`gh secret set RCLONE_CONFIG < rclone.conf`), que lida com conteúdo multiline corretamente.

### Ordem entre upload e rotação

**Problema:** rotacionar antes de confirmar o upload poderia apagar o backup mais antigo sem garantir que o novo chegou.
**Como descobri:** ao desenhar o pior caso (upload falho → rotação apaga o antigo → fico sem nenhum).
**Como resolvi:** step de validação (`rclone lsf | grep`) entre upload e rotação; se o arquivo novo não estiver no Drive, o job falha e a rotação não roda.

---

## 7. Conceitos importantes para entrevista

### GitHub Actions
- **Workflow:** arquivo YAML com os steps a executar.
- **Runner:** máquina (VM) que executa o workflow; aqui, efêmera e descartável.
- **Cron:** agendamento em UTC (`0 6 * * *`); "best-effort", pode atrasar minutos.
- **workflow_dispatch:** permite disparo manual sob demanda.

### GitHub Secrets
- Armazenamento **criptografado** de credenciais.
- **Mascaramento automático** nos logs (aparecem como `***`).

### PostgreSQL
- **pg_dump:** gera **backup lógico** (comandos SQL que recriam os dados), diferente de backup físico (cópia de arquivos).
- **Regra de versão:** o `pg_dump` deve ser **igual ou mais novo** que o servidor.

### Neon
- **Endpoint direto:** conexão real ao Postgres; necessário para `pg_dump`.
- **Endpoint pooler:** via PgBouncer; ideal para muitas conexões curtas da app, incompatível com `pg_dump`.

### rclone
- **OAuth:** autenticação delegada ao Google sem expor senha.
- **Refresh token:** token de longa duração guardado no `rclone.conf`; renova o access token automaticamente, sem reautenticação manual.
- **Escopo `drive.file`:** menor privilégio — o rclone só vê os arquivos que ele mesmo criou.

### Rotação / retenção
- Nomes com timestamp ISO (`AAAA-MM-DD_HHMMSS`) → **ordem alfabética = ordem cronológica** → apagar os mais antigos é trivial (`sort | head`).

---

## 8. Perguntas que um Tech Lead faria

**1. Por que GitHub Actions?**
Não há servidor sempre ligado; Actions é gratuito, sempre disponível e versiona o workflow no repo.

**2. Por que não um cron local/no notebook?**
Só roda com a máquina ligada — risco de pular dias. Preciso de algo 24/7.

**3. O que é o pg_dump?**
Ferramenta oficial do Postgres que gera um backup lógico (SQL) capaz de recriar o banco em qualquer instância compatível.

**4. Backup lógico vs físico?**
Lógico = comandos SQL (portátil entre versões/instâncias). Físico = cópia dos arquivos de dados (mais rápido, mas amarrado à versão/ambiente).

**5. O que acontece se o upload falhar?**
O step de validação não encontra o arquivo no Drive, o job falha (fica vermelho), a rotação **não roda** e o GitHub me envia e-mail. Nenhum backup antigo é apagado.

**6. Por que validar antes de rotacionar?**
Para nunca apagar um backup antigo sem ter certeza de que o novo chegou ao Drive.

**7. Diferença entre endpoint direto e pooler do Neon?**
O pooler (PgBouncer) serve conexões curtas da app e é incompatível com `pg_dump`; o direto conecta ao Postgres real e é o exigido pelo dump.

**8. O que são GitHub Secrets?**
Armazenamento criptografado de credenciais, mascarado nos logs, para não expor segredos no código.

**9. Como funciona o refresh token do rclone?**
É um token de longa duração no `rclone.conf`; o rclone usa ele para renovar o access token do Google automaticamente, sem intervenção humana.

**10. Por que gzip e não o formato custom (`-Fc`)?**
SQL + gzip restaura com `gunzip | psql`, sem `pg_restore`. Mais simples numa emergência.

**11. Por que Google Drive e não S3?**
Já existia, 15 GB grátis, sem cadastro/IAM/cartão. Simplicidade adequada ao porte.

**12. Por que manter 15 backups?**
~15 dias de histórico, com custo de espaço irrisório (<3 MB). Equilíbrio cobertura × espaço.

**13. Como restaurar um backup?**
`rclone copy` do Drive → `gzip -t` para checar integridade → `gunzip -c arquivo.sql.gz | psql "<endpoint direto>"`. De preferência num **branch do Neon** antes de promover.

**14. Como você lidou com a versão do pg_dump no runner?**
Instalei o `postgresql-client-18` via PGDG e ajustei o `$GITHUB_PATH` para usar o binário certo.

**15. O runner é efêmero — como isso afeta o design?**
Nada persiste entre runs; toda config (rclone, pg_dump, secrets) é reconstruída do zero. A única cópia durável vive no Drive; ganho: cada run parte de estado limpo e reprodutível.

**16. Como você garante que sabe se o backup falhou?**
Log completo por run na aba Actions + `$GITHUB_STEP_SUMMARY` + e-mail automático do GitHub em caso de falha.

---

## 9. O que aprendi com essa implementação

- **GitHub Actions:** criar e agendar workflows com cron e disparo manual.
- **CI/CD:** automatizar tarefas na nuvem a partir do repositório.
- **Bash:** scripts robustos com `set -euo pipefail` e validações.
- **PostgreSQL / pg_dump:** backup lógico e a regra de compatibilidade de versão.
- **Neon:** diferença entre endpoint direto e pooler (PgBouncer).
- **OAuth / refresh token:** autenticação delegada e renovação automática de acesso.
- **GitHub Secrets:** gestão segura de credenciais e mascaramento em logs.
- **Automação:** eliminar tarefa manual recorrente sem depender de máquina ligada.
- **Infraestrutura:** raciocinar sobre filesystem efêmero, runners descartáveis e limitações de planos free.
- **Backup e recuperação de desastre:** estratégia de retenção, rotação segura e runbook de restore.
- **Integração entre serviços:** orquestrar GitHub + Neon + Google Drive de ponta a ponta.

---

## 10. Erros que eu cometeria novamente

> Armadilhas reais que enfrentei — cita-las mostra aprendizado prático numa entrevista.

- **Esquecer a compatibilidade de versão do pg_dump** — o `pg_dump` não pode ser mais antigo que o servidor (16 contra Neon 18 falhou). Sempre casar a versão via PGDG.
- **Usar o endpoint `-pooler` do Neon** — o PgBouncer é incompatível com o `pg_dump` e dá erro de autenticação. Usar o endpoint direto.
- **Tentar `export PATH` em vez de `$GITHUB_PATH`** — o `export` não persiste entre steps do runner; o certo é escrever em `$GITHUB_PATH`.
- **Rotacionar antes de validar o upload** — pode apagar o backup antigo sem garantir que o novo chegou. Validar primeiro, rotacionar depois.
- **Colar Secrets multiline pela interface web** — o `rclone.conf` falha silenciosamente; usar `gh secret set < arquivo`.

---

## O que essa implementação demonstra

Experiência prática com:

- Automação de processos
- Backup e recuperação de desastres
- GitHub Actions (CI/CD)
- PostgreSQL
- Bash
- Integração entre serviços
- Infraestrutura em nuvem
- Segurança de credenciais
- Observabilidade
- Arquitetura de soluções
- Tomada de decisão técnica
