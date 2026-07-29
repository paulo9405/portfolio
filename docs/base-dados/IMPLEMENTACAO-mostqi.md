# Registro de Implementação — Desafio mostQI

Este documento registra, fase a fase, o que foi implementado, como funciona e os conceitos introduzidos em cada etapa.

---

## Fase 2 — Playwright: Navegação e Busca

### O que foi implementado

O arquivo `app/scraper.py` ganhou a lógica de navegação e busca no Portal da Transparência.

O robô agora consegue:
1. Abrir o Chromium em modo headless
2. Acessar o portal
3. Preencher o campo de busca com o valor recebido
4. Aplicar o filtro social (se solicitado)
5. Clicar em "Buscar"
6. Fechar o navegador

Ainda não extrai dados, não tira screenshot e não gera JSON. Isso vem nas próximas fases.

---

### Estrutura do arquivo `scraper.py`

```
scraper.py
│
├── Constantes (topo do arquivo)
│   ├── PORTAL_URL         — URL do portal (vem do .env)
│   ├── PLAYWRIGHT_TIMEOUT — timeout em ms (vem do .env)
│   ├── HEADLESS           — modo headless (vem do .env)
│   └── SELETOR_*          — seletores CSS do portal
│
├── executar_consulta()    — função principal, gerencia o ciclo do navegador
├── _navegar_para_portal() — abre o portal e aguarda carregar
└── _realizar_busca()      — preenche o formulário e executa a busca
```

A convenção de nomear funções internas com `_` (underline) indica que elas não devem ser chamadas diretamente de fora do arquivo — apenas por `executar_consulta()`.

---

### Conceito 1 — `async with async_playwright()`

#### O que é

`async with` é um gerenciador de contexto assíncrono. Ele garante que um bloco de código seja executado e, ao terminar (com ou sem erro), execute uma limpeza automática.

#### Por que usamos aqui

O Playwright precisa ser iniciado antes de usar e encerrado depois. O `async with` faz isso automaticamente:

```python
async with async_playwright() as playwright:
    # tudo dentro deste bloco tem acesso ao playwright
# ao sair do bloco, o playwright é encerrado automaticamente
```

Sem isso, precisaríamos chamar `playwright.stop()` manualmente — e arriscar esquecer em caso de erro.

#### Analogia simples

É como alugar um carro: você pega as chaves, usa o carro e devolve. O `async with` é o contrato que garante que a devolução acontece sempre, mesmo se você bater o carro no meio do caminho.

---

### Conceito 2 — `browser.new_context()`

#### O que é

Um "contexto" no Playwright é um ambiente de navegação completamente isolado. Cada contexto tem seus próprios cookies, sessão, histórico e abas — sem compartilhar nada com outros contextos.

#### Por que usamos aqui

Para suportar execuções simultâneas. Se duas requisições chegarem ao mesmo tempo, cada uma cria seu próprio contexto:

```
Requisição A → contexto_A → page_A → robô A rodando
Requisição B → contexto_B → page_B → robô B rodando
```

Eles não interferem um no outro.

#### Sem contexto isolado (o problema)

Se os dois robôs compartilhassem o mesmo navegador sem contexto isolado, um poderia sobrescrever os cookies do outro, navegar para a página errada ou retornar dados misturados.

#### Analogia simples

Cada contexto é como abrir uma janela anônima separada. Duas janelas anônimas no mesmo Chrome não compartilham cookies nem histórico — são ambientes completamente independentes.

---

### Conceito 3 — `try / finally`

#### O que é

`try/finally` garante que o código dentro do `finally` seja executado sempre — mesmo que ocorra um erro dentro do `try`.

#### Por que usamos aqui

```python
try:
    page = await context.new_page()
    await _navegar_para_portal(page)
    await _realizar_busca(page, dados)
finally:
    await context.close()
    await browser.close()
```

Se `_realizar_busca()` lançar uma exceção, o Python pularia direto para o `finally` e fecharia o navegador corretamente.

Sem o `finally`, um erro no meio do fluxo deixaria o navegador aberto na memória. Com múltiplas requisições simultâneas, isso causaria vazamento de memória e eventual travamento do servidor.

#### Erro comum

Colocar o `context.close()` fora do `finally`:

```python
# ERRADO — se der erro antes, o context nunca fecha
await _realizar_busca(page, dados)
await context.close()
```

```python
# CORRETO — fecha sempre, independente de erro
try:
    await _realizar_busca(page, dados)
finally:
    await context.close()
```

---

### Conceito 4 — `page.wait_for_load_state("networkidle")`

#### O que é

Espera até que a página não faça mais requisições de rede por pelo menos 500ms. Indica que a página terminou de carregar todo o conteúdo dinâmico.

#### Por que não usar apenas `page.goto()`

`page.goto()` retorna quando o HTML principal é recebido — mas sites modernos continuam carregando conteúdo via JavaScript depois disso. Se tentar interagir com a página antes disso terminar, os elementos podem não existir ainda.

#### Outras opções de `wait_for_load_state`

| Opção | Quando usar |
|---|---|
| `"load"` | Aguarda o evento `load` do browser (recursos básicos carregados) |
| `"domcontentloaded"` | Aguarda apenas o HTML ser processado (mais rápido, mas ignora JS) |
| `"networkidle"` | Aguarda todas as requisições de rede terminarem (mais seguro para SPAs) |

Usamos `"networkidle"` porque o Portal da Transparência é uma aplicação com JavaScript dinâmico.

---

### Conceito 5 — Seletores CSS como constantes

#### O que é

Em vez de escrever o seletor diretamente onde ele é usado:

```python
# Espalhado pelo código — difícil de manter
await page.fill("#termo", dados.valor_busca)
await page.click("#termo")  # oops, seletor errado aqui
```

Definimos como constante no topo do arquivo:

```python
# Centralizado — fácil de encontrar e atualizar
SELETOR_CAMPO_BUSCA = "#termo"
SELETOR_BOTAO_BUSCA = "button[type='submit']"
```

#### Por que isso importa

O Portal da Transparência pode mudar o layout. Se o seletor `#termo` mudar para `#campo-busca`, basta atualizar a constante no topo — não precisa procurar em vários lugares do código.

#### Tipos de seletores usados

| Seletor | O que seleciona |
|---|---|
| `#termo` | Elemento com `id="termo"` |
| `button[type='submit']` | Botão de envio do formulário |
| `input[value='BENEFICIÁRIO DE PROGRAMA SOCIAL']` | Checkbox com esse valor específico |

Evitamos XPath (`//div[3]/span[1]/input`) porque ele depende da posição dos elementos na página — qualquer mudança de layout quebra o seletor.

---

### Descobertas durante o teste

Ao testar contra o portal real, três obstáculos foram encontrados e resolvidos:

---

**Obstáculo 1 — AWS WAF CAPTCHA**

Na primeira tentativa, o portal retornou uma página de CAPTCHA da Amazon antes de carregar. O browser Playwright puro era detectado como bot.

Solução: configurar o browser para imitar um usuário real:

```python
browser = await playwright.chromium.launch(
    headless=HEADLESS,
    args=["--disable-blink-features=AutomationControlled"],  # desativa flag que identifica automação
)
context = await browser.new_context(
    user_agent="Mozilla/5.0 (X11; Linux x86_64)...",  # user-agent de um Chrome real
    locale="pt-BR",
    timezone_id="America/Sao_Paulo",
    viewport={"width": 1920, "height": 1080},
)
```

O argumento `--disable-blink-features=AutomationControlled` remove um atributo JavaScript (`navigator.webdriver`) que os sites usam para identificar automação. O user-agent faz o browser se apresentar como Chrome normal.

---

**Obstáculo 2 — Banner de cookies bloqueando interação**

Após resolver o CAPTCHA, o botão "Consultar" foi encontrado no DOM mas estava invisível. Um banner de cookies estava cobrindo a página.

Solução: fechar o banner antes de qualquer interação com o formulário:

```python
async def _fechar_banner_cookies(page: Page) -> None:
    try:
        await page.click("button:has-text('Aceitar todos')", timeout=5000)
    except PlaywrightTimeoutError:
        pass  # banner não apareceu — segue normalmente
```

O `timeout=5000` (5 segundos) evita que o robô fique esperando indefinidamente se o banner não aparecer numa próxima execução. O `except PlaywrightTimeoutError` (não `except Exception`) captura apenas o timeout do Playwright — sem engolir outros erros acidentalmente.

---

**Obstáculo 3 — Estrutura real da página (REFINE A BUSCA)**

O botão "Consultar" e os checkboxes de filtro estão dentro de um **painel colapsado** chamado "REFINE A BUSCA". Clicar no botão diretamente era impossível porque o painel estava fechado.

Estrutura real da página:

```
[ Campo de busca: #termo ]  [ 🔍 ]

▼ REFINE A BUSCA              ← painel colapsado
   ☐ Servidor Público
   ☐ Beneficiário de Programa Social   ← #beneficiarioProgramaSocial
   ☐ ...
   [ Consultar ]              ← #btnConsultarPF (só acessível com painel aberto)

[ Todas ] [ A ] [ B ] [ C ] ...

Resultados
```

Solução: fluxo condicional por filtro:

```python
if dados.filtro_social:
    await page.click("button.header")           # abre o painel
    await page.check("#beneficiarioProgramaSocial")  # marca o filtro
    await page.click("#btnConsultarPF")         # clica Consultar
else:
    await page.press("#termo", "Enter")         # sem filtro: Enter basta
```

Pressionar Enter no campo `#termo` é equivalente a clicar no ícone de lupa e não exige expandir nenhum painel.

---

**Correção pós-implementação — `page.check()` travava com timeout no filtro social**

`page.check("#beneficiarioProgramaSocial")` tentava clicar diretamente no `<input>`, mas o `<label>` ficava posicionado em cima e interceptava o evento. O Playwright tentava 50+ vezes e estourava o timeout de 30s.

Correção: clicar na label ao invés do input — é como um usuário real interage com um checkbox HTML.

```python
# ANTES — travava: tentava clicar no input coberto pelo label
SELETOR_FILTRO_SOCIAL = "#beneficiarioProgramaSocial"
await page.check(SELETOR_FILTRO_SOCIAL)

# DEPOIS — correto: clica na label, que encaminha o clique ao checkbox
SELETOR_FILTRO_SOCIAL = "label[for='beneficiarioProgramaSocial']"
await page.click(SELETOR_FILTRO_SOCIAL)
```

---

### Como testar a Fase 2

Antes de testar, instale as dependências:

```bash
pip install -r requirements.txt
playwright install chromium
```

Crie o arquivo `.env` a partir do `.env.example`:

```bash
cp .env.example .env
```

Para testar com o navegador visível (facilita depuração), edite o `.env`:

```
HEADLESS=false
```

Execute o teste diretamente no terminal Python:

```python
import asyncio
from app.scraper import executar_consulta
from app.schemas import ConsultaEntrada

dados = ConsultaEntrada(tipo_busca="Nome", valor_busca="João Silva", filtro_social=False)
asyncio.run(executar_consulta(dados))
```

A saída esperada no terminal:

```
[SCRAPER] Acessando Portal da Transparência...
[SCRAPER] Portal carregado.
[SCRAPER] Iniciando busca: tipo=Nome, valor=João Silva
[SCRAPER] Busca executada.
```

---

### Como explicar a Fase 2 em uma entrevista

> "O scraper usa o Playwright com contextos isolados para suportar execuções simultâneas. Cada requisição cria seu próprio contexto de navegador — como uma janela anônima separada. O `try/finally` garante que o navegador seja sempre fechado, mesmo em caso de erro, evitando vazamento de memória. Os seletores ficam como constantes no topo do arquivo para facilitar manutenção quando o portal atualizar o layout."

---

### Resumo da Fase 2

| O que | Como |
|---|---|
| Abrir o navegador sem ser detectado como bot | `launch(args=["--disable-blink-features=AutomationControlled"])` + user-agent real |
| Isolar a sessão | `browser.new_context()` |
| Garantir limpeza | `try/finally` com `context.close()` |
| Fechar banner de cookies | `page.click("button:has-text('Aceitar todos')", timeout=5000)` com `except PlaywrightTimeoutError` |
| Esperar o portal carregar | `page.wait_for_load_state("networkidle")` |
| Preencher a busca | `page.fill("#termo", valor)` |
| Executar busca simples | `page.press("#termo", "Enter")` |
| Abrir painel de filtros | `page.click("button.header")` |
| Aplicar filtro social | `page.check("#beneficiarioProgramaSocial")` |
| Executar busca com filtro | `page.click("#btnConsultarPF")` |

---

*Próxima fase: extração dos dados da página de resultado.*

---

## Fase 3 — Extração de Dados

### O que foi implementado

Após a busca, o robô agora:
1. Clica no primeiro resultado da lista
2. Navega para a página "Pessoa Física" da pessoa
3. Extrai nome, CPF e NIS
4. Retorna um dicionário Python com esses dados

Dois seletores novos + duas funções novas foram adicionados ao `scraper.py`.

---

### Estrutura real da página de resultado

A página carregada após clicar no resultado tem esta estrutura:

```
Pessoa Física

Nome              CPF                   Localidade
JOAO DA SILVA     ***.659.347-**        NILÓPOLIS - RJ

Panorama da relação da pessoa com o Governo Federal

▼ RECEBIMENTOS DE RECURSOS
   ┌─────────────────────────────────────────────────────┐
   │ Benefício de Prestação Continuada                   │
   │ Detalhar │ NIS            │ Nome       │ Valor      │
   │ [link]   │ 2.679.513.387-5│ JOAO...   │ R$ 55.130  │
   └─────────────────────────────────────────────────────┘
```

---

### Seletores utilizados e por quê

**Nome:**
```python
page.locator("strong:has-text('Nome') + span").first
```
O HTML tem `<strong>Nome</strong><span>JOAO DA SILVA</span>`. O `+` é o seletor CSS de irmão adjacente — pega o `<span>` imediatamente após o `<strong>` que contém o texto "Nome".

**CPF:**
```python
page.locator("strong:has-text('CPF') + span").first
```
Mesma lógica. O CPF é retornado mascarado pelo portal (`***.659.347-**`) — isso é comportamento do próprio portal, não do robô.

**NIS:**
```python
page.locator("table:has(th:has-text('NIS')) tbody tr:first-child td:nth-child(2)").first
```
O NIS está dentro de uma tabela de benefícios. A tabela tem 4 colunas:

| Coluna | Header | `<td>` |
|---|---|---|
| 1ª | `Detalhar` (classe `noprint`) | Link "Detalhar" |
| 2ª | `NIS` | Número NIS ← aqui |
| 3ª | `Nome` | Nome da pessoa |
| 4ª | `Valor Recebido` | Valor em R$ |

Por isso `td:nth-child(2)` — a segunda célula da linha é o NIS.

---

### Conceito — `inner_text()` vs `text_content()`

Dois métodos para extrair texto de elementos no Playwright:

| Método | Lê elementos ocultos? | Respeita CSS? |
|---|---|---|
| `inner_text()` | Não | Sim |
| `text_content()` | Sim | Não |

O NIS está dentro da seção "RECEBIMENTOS DE RECURSOS" que pode estar visualmente colapsada. Por isso usamos `text_content()` para extrair o NIS — ele lê o valor mesmo quando o elemento está oculto por CSS.

Para Nome e CPF, que sempre estão visíveis, usamos `inner_text()`.

---

### Por que o NIS pode vir vazio

O NIS só aparece se a pessoa tiver benefícios cadastrados (Bolsa Família, BPC, Auxílio Emergencial, etc.). Se a pessoa não tiver benefícios:
- A tabela com `<th>NIS</th>` não existe na página
- O `timeout=5000` esgota
- O `except PlaywrightTimeoutError` captura e retorna `""`

Isso é comportamento correto — não todo cidadão tem NIS.

---

### Como explicar a Fase 3 em uma entrevista

> "Para extrair os dados da pessoa, usamos seletores CSS que localizam os elementos pelo conteúdo do texto — por exemplo, `strong:has-text('Nome') + span` encontra o `<span>` que vem logo após o `<strong>` com texto 'Nome'. O NIS fica dentro de uma tabela de benefícios que pode estar visualmente oculta, então usamos `text_content()` em vez de `inner_text()` — o primeiro lê o DOM diretamente, independente do CSS."

---

### Resumo da Fase 3

| O que | Como |
|---|---|
| Clicar no primeiro resultado | `page.locator("a[href*='/pessoa-fisica/']:not(.menu-item)").first` |
| Extrair Nome | `strong:has-text('Nome') + span` → `inner_text()` |
| Extrair CPF | `strong:has-text('CPF') + span` → `inner_text()` |
| Expandir seção de benefícios | `page.click("text=RECEBIMENTOS DE RECURSOS")` |
| Extrair NIS | `table:has(th:has-text('NIS')) tbody tr:first-child td:nth-child(2)` → `text_content()` |
| NIS ausente | `except PlaywrightTimeoutError` → retorna `""` |

---

*Próxima fase: screenshot da página e conversão para Base64.*

---

## Fase 4 — Screenshot e Conversão para Base64

### O que foi implementado

Dois arquivos foram alterados:

- `app/utils.py` — a função `screenshot_para_base64()` foi implementada.
- `app/scraper.py` — o scraper agora chama `page.screenshot()` após extrair os dados da pessoa e converte o resultado para Base64.

O robô agora captura uma imagem completa da página "Panorama da relação da pessoa com o Governo Federal" e a converte para o formato exigido pelo desafio.

---

### O que mudou em cada arquivo

**`utils.py`**

```python
def screenshot_para_base64(screenshot_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode("utf-8")
```

**`scraper.py`** — trecho adicionado logo após `_extrair_dados_pessoa()`:

```python
screenshot_bytes = await page.screenshot(full_page=True)
evidencia = screenshot_para_base64(screenshot_bytes)
print(f"[SCRAPER] Screenshot capturado. Base64 gerado ({len(evidencia)} caracteres).")
```

---

### Conceito 1 — `page.screenshot(full_page=True)`

#### O que é

`page.screenshot()` é um método nativo do Playwright que captura a tela atual do navegador e retorna os bytes brutos de um arquivo PNG.

#### O parâmetro `full_page=True`

Por padrão, o Playwright captura apenas a parte visível da página (o viewport configurado — neste projeto, 1920×1080). Com `full_page=True`, ele rola a página inteira e captura tudo, incluindo o que está abaixo da dobra.

Usamos `full_page=True` porque a página "Panorama" do Portal da Transparência tem conteúdo que fica abaixo da tela — benefícios, recebimentos, vínculos. A evidência deve mostrar tudo que foi coletado.

#### Por que retorna `bytes` e não um arquivo

O Playwright oferece duas formas de capturar:

```python
# Salva direto em arquivo no disco
await page.screenshot(path="evidencia.png")

# Retorna os bytes em memória (sem criar arquivo)
screenshot_bytes = await page.screenshot(full_page=True)
```

Usamos a versão em memória porque o desafio exige Base64 no JSON — não faz sentido salvar um arquivo temporário no disco só para lê-lo logo depois.

---

### Conceito 2 — Base64

#### O que é

Base64 é uma forma de representar dados binários (como imagens) usando apenas caracteres de texto. Ele transforma bytes em uma sequência de letras, números e símbolos (`A-Z`, `a-z`, `0-9`, `+`, `/`).

#### Por que o desafio pede Base64

O JSON só aceita texto — não é possível colocar bytes brutos de uma imagem diretamente em um campo JSON. Base64 resolve isso: converte a imagem inteira em uma string de texto que cabe dentro do JSON.

#### O prefixo `data:image/png;base64,`

```python
return "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode("utf-8")
```

O prefixo `data:image/png;base64,` é o padrão URI de dados. Ele informa ao receptor que:
- `data:` — é um dado embutido (não uma URL externa)
- `image/png` — o tipo do arquivo
- `base64,` — a codificação usada

Com esse prefixo, a string pode ser colada diretamente em HTML (`<img src="data:image/png;base64,...">`) e a imagem aparece sem precisar de nenhum arquivo externo.

#### O método `.decode("utf-8")`

`base64.b64encode()` retorna `bytes`, não `str`. O `.decode("utf-8")` converte para string Python — necessário para colocar dentro do JSON.

```python
# Sem .decode() — retorna bytes
base64.b64encode(screenshot_bytes)         # b'iVBORw0KGgo...'

# Com .decode() — retorna str (o que queremos)
base64.b64encode(screenshot_bytes).decode("utf-8")  # 'iVBORw0KGgo...'
```

---

### Resultado do teste

```
[SCRAPER] Screenshot capturado. Base64 gerado (188870 caracteres).
```

188.870 caracteres é o tamanho esperado para uma imagem PNG de página inteira convertida em Base64. A regra geral é que Base64 ocupa aproximadamente 33% a mais que o arquivo original — então o PNG original tem em torno de 140 KB.

---

### Como explicar a Fase 4 em uma entrevista

> "Para capturar a evidência, usamos `page.screenshot(full_page=True)` do Playwright, que retorna os bytes do PNG diretamente em memória — sem criar arquivo temporário no disco. Depois convertemos com `base64.b64encode()` e adicionamos o prefixo `data:image/png;base64,`, que é o formato URI de dados aceito pelo JSON e renderizável diretamente em HTML."

---

### Resumo da Fase 4

| O que | Como |
|---|---|
| Capturar a tela inteira | `page.screenshot(full_page=True)` → retorna `bytes` |
| Converter para Base64 | `base64.b64encode(bytes).decode("utf-8")` |
| Adicionar prefixo padrão | `"data:image/png;base64," + ...` |
| Onde fica a lógica | `utils.py` → `screenshot_para_base64()` |
| Onde é chamada | `scraper.py` → logo após `_extrair_dados_pessoa()` |

---

*Próxima fase: montar o JSON de saída completo com todos os dados coletados.*

---

## Fase 5 — JSON de Saída

### O que foi implementado

O `scraper.py` agora monta e retorna um objeto `ConsultaSaida` completo ao final do fluxo de sucesso. Dois imports foram adicionados em cada arquivo:

- `scraper.py` — importa `DadosConsulta`, `DadosPessoa`, `gerar_uuid` e `data_hora_atual`; constrói e retorna o `ConsultaSaida`
- Nenhuma alteração nos outros arquivos — `schemas.py` e `utils.py` já estavam prontos desde a Fase 1

---

### O que foi adicionado ao `scraper.py`

```python
resultado = ConsultaSaida(
    consulta=DadosConsulta(
        identificador_unico=gerar_uuid(),
        tipo_busca=dados.tipo_busca,
        valor_busca=dados.valor_busca,
        data_hora=data_hora_atual(),
        filtro_social=dados.filtro_social,
    ),
    pessoa=DadosPessoa(**dados_pessoa),
    beneficios=[],
    evidencia_base64=evidencia,
    status="sucesso",
    mensagem_erro=None,
)
print(f"[SCRAPER] JSON montado. Status: {resultado.status}")
return resultado
```

`beneficios` está vazio por ora — os detalhes de cada benefício serão coletados na Fase 6.

---

### Conceito 1 — Por que separar entrada e saída em classes Pydantic

O FastAPI usa os schemas Pydantic para duas coisas ao mesmo tempo:

1. **Validar** — garante que os dados têm os tipos certos antes de qualquer processamento
2. **Documentar** — gera o Swagger automaticamente com os campos, tipos e exemplos

Se colocássemos tudo em dicionários Python, o Swagger não saberia o formato esperado e não teria como validar automaticamente os dados de entrada.

```python
# Com Pydantic — o FastAPI valida e documenta automaticamente
@app.post("/consulta", response_model=ConsultaSaida)
async def consulta(dados: ConsultaEntrada):
    return await executar_consulta(dados)

# Sem Pydantic — sem validação automática, sem Swagger
@app.post("/consulta")
async def consulta(dados: dict):
    return await executar_consulta(dados)
```

---

### Conceito 2 — `DadosPessoa(**dados_pessoa)`

`dados_pessoa` é o dicionário retornado por `_extrair_dados_pessoa()`:

```python
{"nome": "JOAO VICTOR DA SILVA JOAO", "cpf": "***.659.347-**", "nis": "2.679.513.387-5"}
```

O `**` (double star) desempacota o dicionário como argumentos nomeados:

```python
# Equivalente a:
DadosPessoa(nome="JOAO VICTOR DA SILVA JOAO", cpf="***.659.347-**", nis="2.679.513.387-5")
```

Funciona porque as chaves do dicionário (`nome`, `cpf`, `nis`) têm exatamente os mesmos nomes dos campos de `DadosPessoa`. Se os nomes não coincidissem, o Python lançaria um `TypeError`.

---

### Conceito 3 — `return` dentro do `try/finally`

```python
try:
    ...
    return resultado   # ← retorna aqui
finally:
    await context.close()   # ← mas isso roda ANTES do retorno acontecer
    await browser.close()
```

O Python garante que o bloco `finally` sempre executa — inclusive quando há um `return` no `try`. O valor de retorno é preservado: o `return resultado` "agenda" o retorno, o `finally` fecha o navegador, e só então a função devolve o resultado para quem chamou.

Isso é fundamental: sem o `finally`, um `return` no meio do código deixaria o navegador aberto na memória.

---

### Resultado do teste

```json
{
  "consulta": {
    "identificador_unico": "95bb71c3-ed6d-45ee-b309-3cca3e571314",
    "tipo_busca": "Nome",
    "valor_busca": "João Silva",
    "data_hora": "2026-07-08T10:42:33",
    "filtro_social": false
  },
  "pessoa": {
    "nome": "JOAO VICTOR DA SILVA JOAO",
    "cpf": "***.659.347-**",
    "nis": "2.679.513.387-5"
  },
  "beneficios": [],
  "evidencia_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAB3QA...",
  "status": "sucesso",
  "mensagem_erro": null
}
```

A estrutura está idêntica ao formato exigido no desafio.

---

### Como explicar a Fase 5 em uma entrevista

> "A saída é um objeto Pydantic chamado `ConsultaSaida` que agrupa os dados em seções: `consulta` com os metadados da requisição, `pessoa` com os dados extraídos, `beneficios` com os detalhes de cada benefício e `evidencia_base64` com o screenshot. O Pydantic garante que o JSON de saída sempre tenha o formato correto — o FastAPI usa esse mesmo schema para gerar o Swagger automaticamente."

---

### Resumo da Fase 5

| O que | Como |
|---|---|
| Montar os metadados da consulta | `DadosConsulta(identificador_unico=gerar_uuid(), ...)` |
| Montar os dados da pessoa | `DadosPessoa(**dados_pessoa)` |
| Incluir o screenshot | `evidencia_base64=evidencia` |
| Definir o status | `status="sucesso"` |
| Retornar com navegador garantido de fechar | `return resultado` dentro do `try/finally` |

---

*Próxima fase: tratamento de erros para os 5 cenários de teste.*

---

## Fase 6 — Tratamento de Erros

### O que foi implementado

Quatro mudanças no `scraper.py`:

1. `from typing import Optional` adicionado aos imports
2. Duas constantes com as mensagens de erro exatas do desafio
3. Função `_montar_erro()` — monta o JSON com `status: "erro"`
4. Função `_verificar_resultado_busca()` — detecta os dois tipos de erro esperados
5. `executar_consulta()` atualizado com a verificação e um `except Exception` para erros inesperados

---

### As duas constantes de erro

```python
MENSAGEM_ERRO_CPF = "Não foi possível retornar os dados no tempo de resposta solicitado"
MENSAGEM_ERRO_NOME = "Foram encontrados 0 resultados para o termo"
```

As mensagens ficam como constantes no topo do arquivo por dois motivos: são usadas em mais de um lugar, e são os valores exatos exigidos pelo desafio — se precisarem ser ajustadas, basta alterar aqui.

---

### `_montar_erro()`

```python
def _montar_erro(dados: ConsultaEntrada, mensagem: str) -> ConsultaSaida:
    return ConsultaSaida(
        consulta=DadosConsulta(
            identificador_unico=gerar_uuid(),
            tipo_busca=dados.tipo_busca,
            valor_busca=dados.valor_busca,
            data_hora=data_hora_atual(),
            filtro_social=dados.filtro_social,
        ),
        pessoa=None,
        beneficios=[],
        evidencia_base64=None,
        status="erro",
        mensagem_erro=mensagem,
    )
```

É uma função síncrona (sem `async`) — não precisa chamar nenhuma operação do Playwright. Recebe os dados de entrada e a mensagem de erro e devolve um `ConsultaSaida` completo com `status: "erro"`, `pessoa: null` e `evidencia_base64: null`.

---

### `_verificar_resultado_busca()`

```python
async def _verificar_resultado_busca(page: Page, dados: ConsultaEntrada) -> Optional[str]:
    # O portal exibe "0 resultados" para qualquer busca sem resultado.
    # A mensagem de erro devolvida depende do tipo de busca.
    if await page.locator("text=0 resultados").count() > 0:
        if dados.tipo_busca == "Nome":
            return f"{MENSAGEM_ERRO_NOME} {dados.valor_busca}"
        else:
            return MENSAGEM_ERRO_CPF

    # CPF/NIS inválido: o portal exibe a mensagem de timeout/erro
    if await page.locator(f"text={MENSAGEM_ERRO_CPF}").count() > 0:
        return MENSAGEM_ERRO_CPF

    # Verifica se há ao menos um resultado clicável
    try:
        await page.locator(SELETOR_PRIMEIRO_RESULTADO).first.wait_for(state="visible", timeout=5000)
        return None
    except PlaywrightTimeoutError:
        return MENSAGEM_ERRO_CPF
```

Retorna `None` se há resultados (caminho de sucesso) ou uma string com a mensagem de erro (caminho de erro).

---

### Correção pós-implementação — seletor de "0 resultados" dava falso positivo

**Problema:** o seletor `"text=0 resultados"` retornava erro mesmo quando a busca tinha resultados.

**Causa:** o Playwright faz busca por **substring**. O texto "**10.00`0 resultados`**" exibido pelo portal contém "0 resultados" dentro dele, então o robô entendia como se não houvesse resultado.

**Correção:** trocar pelo texto completo que nunca aparece quando há resultados:

```python
# ANTES — falso positivo: "10.000 resultados" contém "0 resultados"
if await page.locator("text=0 resultados").count() > 0:

# DEPOIS — correto: "Foram encontrados 10.000 resultados" não contém essa substring
if await page.locator("text=Foram encontrados 0 resultados").count() > 0:
```

**Como foi descoberto:** screenshot salvo em disco (`page.screenshot(path="debug_resultado.png")`) mostrou que o portal exibia 10.000 resultados enquanto o scraper retornava erro.

---

**Correção pós-implementação — fallback de timeout retornava mensagem errada para busca por Nome**

O bloco `except PlaywrightTimeoutError` no final de `_verificar_resultado_busca()` sempre retornava `MENSAGEM_ERRO_CPF`, mesmo quando a busca era por Nome.

```python
# ANTES — sempre retornava mensagem de CPF, independente do tipo de busca
except PlaywrightTimeoutError:
    return MENSAGEM_ERRO_CPF

# DEPOIS — retorna a mensagem correta para cada tipo de busca
except PlaywrightTimeoutError:
    if dados.tipo_busca == "Nome":
        return f"{MENSAGEM_ERRO_NOME} {dados.valor_busca}"
    return MENSAGEM_ERRO_CPF
```

---

### Resultado final dos 5 cenários de teste

| # | Cenário | Entrada | Status | Resultado |
|---|---|---|---|---|
| 1 | Sucesso por NIS | `NIS: 13233581857` | `sucesso` | `TEREZINHA DA SILVA E SILVA DA SILVA`, CPF mascarado, NIS correto |
| 2 | Erro por CPF | `CPF: 123.456.789-00` | `erro` | `"Não foi possível retornar os dados no tempo de resposta solicitado"` |
| 3 | Sucesso por Nome | `Nome: Silva` | `sucesso` | `GISLAINE SILVA DA SILVA E SILVA`, CPF mascarado |
| 4 | Erro por Nome | `Nome: xyzxyzabc987654` | `erro` | `"Foram encontrados 0 resultados para o termo xyzxyzabc987654"` |
| 5 | Filtrado | `Nome: Silva`, filtro social | `sucesso` | `TEREZINHA DA SILVA E SILVA DA SILVA`, NIS presente |

---

### Descoberta durante o teste — o portal usa "0 resultados" para tudo

O comportamento esperado pelo desafio era:

| Cenário | Mensagem |
|---|---|
| CPF/NIS inexistente | `"Não foi possível retornar os dados..."` |
| Nome inexistente | `"Foram encontrados 0 resultados para o termo..."` |

Na prática, o portal exibe `"0 resultados"` na página para **qualquer** busca sem resultado — seja por CPF, NIS ou Nome. Não há elemento diferente na página para distinguir os dois casos.

A solução foi usar `dados.tipo_busca` como critério de decisão: se o texto "0 resultados" apareceu e a busca era por Nome, retorna a mensagem de Nome. Se era por CPF ou NIS, retorna a mensagem de CPF.

```python
if await page.locator("text=0 resultados").count() > 0:
    if dados.tipo_busca == "Nome":
        return f"{MENSAGEM_ERRO_NOME} {dados.valor_busca}"
    else:
        return MENSAGEM_ERRO_CPF
```

---

### Conceito — três categorias de erro

**Categoria A — Erros esperados do portal** (fazem parte dos cenários de teste):

| Situação | Como detectar | Mensagem retornada |
|---|---|---|
| Nome sem resultados | `"text=0 resultados"` + `tipo_busca == "Nome"` | `"Foram encontrados 0 resultados para o termo [valor]"` |
| CPF/NIS inexistente | `"text=0 resultados"` + `tipo_busca != "Nome"` | `"Não foi possível retornar os dados..."` |

**Categoria B — Timeout sem resultado visível:**

Se o portal não exibiu "0 resultados" mas também não apareceu nenhum link de resultado em 5 segundos — retorna a mensagem de erro de CPF como fallback.

```python
try:
    await page.locator(SELETOR_PRIMEIRO_RESULTADO).first.wait_for(state="visible", timeout=5000)
    return None
except PlaywrightTimeoutError:
    return MENSAGEM_ERRO_CPF
```

**Categoria C — Erros inesperados** (exceções Python não previstas):

```python
except Exception as e:
    print(f"[SCRAPER] Erro inesperado: {e}")
    return _montar_erro(dados, f"Erro interno: {str(e)}")
```

A API nunca quebra com um erro 500 sem retornar um JSON. Qualquer exceção não prevista é capturada aqui e devolvida como JSON de erro.

---

### Conceito — `except Exception` não engole o `finally`

```python
try:
    ...
except Exception as e:
    return _montar_erro(dados, ...)  # captura qualquer exceção inesperada
finally:
    await context.close()   # executa SEMPRE — com sucesso, com erro esperado ou com exceção
    await browser.close()
```

A ordem de execução em cada cenário:

| Cenário | O que executa |
|---|---|
| Sucesso | `try` completo → `finally` |
| Erro esperado (`_verificar_resultado_busca` detecta) | `try` parcial → `return` no meio → `finally` |
| Exceção inesperada | `try` parcial → `except` → `finally` |

Em todos os casos, o `finally` fecha o navegador. Nenhum contexto de browser fica aberto na memória.

---

### Fluxo atualizado do `executar_consulta()`

```
Abre navegador
    ↓
Acessa portal
    ↓
Fecha banner de cookies
    ↓
Realiza busca
    ↓
_verificar_resultado_busca()
    ├── "0 resultados" + Nome  → return _montar_erro(..., MENSAGEM_ERRO_NOME)
    ├── "0 resultados" + CPF   → return _montar_erro(..., MENSAGEM_ERRO_CPF)
    ├── timeout sem resultado  → return _montar_erro(..., MENSAGEM_ERRO_CPF)
    └── resultado encontrado   → continua ↓
Clica no primeiro resultado
    ↓
Extrai dados da pessoa
    ↓
Tira screenshot → Base64
    ↓
Monta e retorna ConsultaSaida (sucesso)
```

---

### Resultado dos testes

**Cenário de erro — Nome inexistente:**
```json
{
  "status": "erro",
  "mensagem_erro": "Foram encontrados 0 resultados para o termo xyzxyzxyzabc987654"
}
```

**Cenário de erro — CPF inexistente:**
```json
{
  "status": "erro",
  "mensagem_erro": "Não foi possível retornar os dados no tempo de resposta solicitado"
}
```

---

### Como explicar a Fase 6 em uma entrevista

> "O tratamento de erros tem três camadas. A primeira detecta erros esperados do portal: quando o portal exibe '0 resultados', verificamos o tipo de busca para devolver a mensagem correta — Nome ou CPF têm mensagens diferentes no desafio. A segunda é um timeout: se não aparecer resultado clicável em 5 segundos, retornamos a mensagem de CPF. A terceira é um `except Exception` que captura qualquer erro inesperado e garante que a API nunca retorne um 500 sem JSON."

---

### Resumo da Fase 6

| O que | Como |
|---|---|
| Mensagens de erro centralizadas | Constantes `MENSAGEM_ERRO_CPF` e `MENSAGEM_ERRO_NOME` |
| Montar JSON de erro | `_montar_erro(dados, mensagem)` — função síncrona |
| Detectar erro de nome | `"text=0 resultados"` + `tipo_busca == "Nome"` |
| Detectar erro de CPF/NIS | `"text=0 resultados"` + `tipo_busca != "Nome"` |
| Fallback por timeout | `wait_for(timeout=5000)` → `except PlaywrightTimeoutError` |
| Erros inesperados | `except Exception` → retorna JSON de erro com mensagem da exceção |
| Navegador sempre fechado | `finally` com `context.close()` + `browser.close()` |

---

*Próxima fase: endpoint FastAPI com POST /consulta e Swagger.*

---

## Fase 7 — Endpoint FastAPI

### O que foi implementado

O arquivo `app/main.py` recebeu o endpoint `POST /consulta`, conectando a API ao robô desenvolvido nas fases anteriores.

O servidor agora:
1. Recebe uma requisição HTTP com os parâmetros de busca
2. Valida automaticamente os dados de entrada via Pydantic
3. Chama `executar_consulta()` do `scraper.py`
4. Retorna o JSON de saída com o resultado da consulta
5. Expõe o Swagger UI automaticamente em `/docs`

---

### O que mudou em `main.py`

```python
from fastapi import FastAPI
from app.schemas import ConsultaEntrada, ConsultaSaida
from app.scraper import executar_consulta

app = FastAPI(
    title="mostQI — Consulta Portal da Transparência",
    description="Robô para coleta de dados de pessoas físicas no Portal da Transparência do Governo Federal.",
    version="1.0.0",
)

@app.post("/consulta", response_model=ConsultaSaida)
async def consulta(dados: ConsultaEntrada) -> ConsultaSaida:
    return await executar_consulta(dados)
```

Quatro linhas de código. O FastAPI cuida do resto: validação, serialização, documentação e tratamento de erros de entrada.

---

### Conceito 1 — `response_model=ConsultaSaida`

#### O que é

O parâmetro `response_model` diz ao FastAPI qual o formato esperado da resposta. Ele faz duas coisas:

1. **Filtra** — se o objeto retornado tiver campos a mais, o FastAPI os remove antes de enviar ao cliente
2. **Documenta** — o Swagger mostra exatamente os campos que o cliente vai receber, com tipos e exemplos

#### Por que isso importa

Sem `response_model`, o Swagger não saberia o formato da resposta e não conseguiria documentá-la. Com ele, qualquer pessoa que abrir `/docs` vê exatamente o que a API retorna — sem precisar ler o código.

---

### Conceito 2 — Validação automática de entrada

Quando o cliente envia um JSON com campo inválido, o FastAPI rejeita automaticamente com HTTP 422 antes de chamar o robô:

```json
// Entrada inválida — tipo_busca não aceito
{"tipo_busca": "email", "valor_busca": "teste"}

// Resposta automática do FastAPI
{
  "detail": [
    {
      "type": "literal_error",
      "loc": ["body", "tipo_busca"],
      "msg": "Input should be 'CPF', 'NIS' or 'Nome'"
    }
  ]
}
```

Isso acontece porque `ConsultaEntrada` usa `Literal["CPF", "NIS", "Nome"]` — o Pydantic rejeita qualquer outro valor antes do código do robô ser executado.

---

### Conceito 3 — Por que o endpoint é `async`

```python
async def consulta(dados: ConsultaEntrada) -> ConsultaSaida:
    return await executar_consulta(dados)
```

O `executar_consulta()` do `scraper.py` é uma função `async` porque usa o Playwright, que é assíncrono. Para chamar uma função `async` com `await`, quem chama também precisa ser `async`.

Se o endpoint fosse síncrono (`def consulta`), não seria possível usar `await` e o Playwright bloquearia o servidor inteiro enquanto o robô rodasse — impedindo qualquer outra requisição simultânea.

Com `async def`, o servidor pode receber outras requisições enquanto o robô está navegando no portal.

---

### Como executar

```bash
uvicorn app.main:app --reload
```

- API disponível em: `http://localhost:8000/consulta`
- Swagger UI em: `http://localhost:8000/docs`
- OpenAPI JSON em: `http://localhost:8000/openapi.json`

O `--reload` reinicia o servidor automaticamente a cada mudança no código — útil durante o desenvolvimento.

---

### Como testar manualmente

**Pelo Swagger:** abrir `http://localhost:8000/docs`, clicar em `POST /consulta` → `Try it out` → editar o body → `Execute`.

**Pelo terminal:**

```bash
# Cenário de erro — nome inexistente
curl -X POST http://localhost:8000/consulta \
  -H "Content-Type: application/json" \
  -d '{"tipo_busca": "Nome", "valor_busca": "xyzxyzabc987654", "filtro_social": false}'

# Cenário com filtro social
curl -X POST http://localhost:8000/consulta \
  -H "Content-Type: application/json" \
  -d '{"tipo_busca": "Nome", "valor_busca": "Silva", "filtro_social": true}'
```

---

### Como explicar a Fase 7 em uma entrevista

> "O endpoint `POST /consulta` recebe os parâmetros, valida automaticamente via Pydantic — se `tipo_busca` não for CPF, NIS ou Nome, o FastAPI rejeita com 422 antes de chamar o robô. O endpoint é `async` porque o scraper usa Playwright assíncrono — isso permite múltiplas requisições simultâneas sem bloquear o servidor. O Swagger é gerado automaticamente pelo `response_model` — sem escrever uma linha de documentação."

---

### Resumo da Fase 7

| O que | Como |
|---|---|
| Receber a requisição | `@app.post("/consulta")` |
| Validar entrada automaticamente | `ConsultaEntrada` via Pydantic — rejeita com 422 se inválido |
| Chamar o robô | `await executar_consulta(dados)` |
| Documentar a resposta | `response_model=ConsultaSaida` |
| Gerar Swagger automaticamente | FastAPI gera em `/docs` a partir dos schemas Pydantic |
| Suportar execuções simultâneas | `async def` + `await` |

---

*Próxima fase: testes automatizados dos 5 cenários.*

---

## Fase 8 — Testes Automatizados

### O que foi implementado

Dois arquivos foram criados ou alterados:

- `pytest.ini` — configuração do pytest com `asyncio_mode = auto`
- `tests/test_cenarios.py` — os 5 testes de integração exigidos pelo desafio

Os testes rodam contra o Portal da Transparência ao vivo, sem mock. Isso garante que o robô funciona no site real — que é o que importa na apresentação.

---

### Estrutura do arquivo `test_cenarios.py`

```
test_cenarios.py
│
├── test_sucesso_cpf()   — Cenário 1: NIS válido → sucesso com dados e evidência
├── test_erro_cpf()      — Cenário 2: CPF inexistente → erro com mensagem exata
├── test_sucesso_nome()  — Cenário 3: Nome "Silva" → sucesso com dados e evidência
├── test_erro_nome()     — Cenário 4: Nome inexistente → erro com mensagem exata
└── test_filtrado()      — Cenário 5: Nome + filtro social → sucesso com NIS presente
```

---

### Por que testes de integração reais (sem mock)

Mock significa substituir o portal por um objeto falso que simula as respostas. A vantagem é velocidade — os testes rodam em milissegundos. A desvantagem é que o mock nunca vai mudar quando o portal mudar.

Para este projeto, o objetivo principal dos testes é garantir que o robô funciona no site real antes da apresentação — não testar a lógica interna do Python. Por isso a escolha foi integração real.

```
# Com mock — rápido, mas não testa o portal real
mock_page.locator.return_value.inner_text.return_value = "JOAO DA SILVA"

# Com integração real — lento (60s), mas testa o que importa
resultado = await executar_consulta(dados)
assert resultado.pessoa.nome != ""
```

---

### O que cada teste valida

**Cenários de sucesso (1, 3 e 5):**

```python
assert resultado.status == "sucesso"
assert resultado.mensagem_erro is None
assert resultado.pessoa is not None
assert resultado.pessoa.nome != ""
assert resultado.evidencia_base64.startswith("data:image/png;base64,")
```

**Cenários de erro (2 e 4):**

```python
assert resultado.status == "erro"
assert resultado.mensagem_erro == MENSAGEM_ERRO_CPF   # ou MENSAGEM_ERRO_NOME
assert resultado.pessoa is None
assert resultado.evidencia_base64 is None
```

**Cenário 5 — verificação extra do NIS:**

```python
assert resultado.pessoa.nis != ""
```

O filtro social garante que o resultado é um beneficiário de programa social — e beneficiários têm NIS. Se o NIS viesse vazio, significaria que o filtro não funcionou.

---

### Conceito — `asyncio_mode = auto` no `pytest.ini`

#### O problema

O `pytest` padrão não sabe executar funções `async`. Se tentarmos rodar um teste assim:

```python
async def test_sucesso_cpf():
    resultado = await executar_consulta(dados)
```

O pytest apenas ignora a função — ela nunca é executada de verdade.

#### A solução: `pytest-asyncio`

O `pytest-asyncio` ensina o pytest a rodar funções `async`. Ele tem dois modos de operação:

| Modo | Como ativar | Comportamento |
|---|---|---|
| `strict` | padrão | precisa marcar cada teste com `@pytest.mark.asyncio` |
| `auto` | `asyncio_mode = auto` no `pytest.ini` | detecta `async def` automaticamente |

Usamos `auto` porque todos os testes deste arquivo são `async` — não faz sentido repetir o decorador em cada um.

#### O arquivo `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
```

Dois campos:
- `[pytest]` — seção que o pytest lê ao iniciar
- `asyncio_mode = auto` — instrui o `pytest-asyncio` a detectar funções `async` automaticamente

---

### Resultado dos testes

```
============================= test session starts ==============================
plugins: asyncio-0.23.7
asyncio: mode=auto
collected 5 items

tests/test_cenarios.py::test_sucesso_cpf   PASSED  [ 20%]
tests/test_cenarios.py::test_erro_cpf      PASSED  [ 40%]
tests/test_cenarios.py::test_sucesso_nome  PASSED  [ 60%]
tests/test_cenarios.py::test_erro_nome     PASSED  [ 80%]
tests/test_cenarios.py::test_filtrado      PASSED  [100%]

========================= 5 passed in 65.41s (0:01:05) =========================
```

5/5 passaram. O tempo de 65 segundos é esperado — cada teste abre um navegador real e navega pelo portal.

---

### Como executar

```bash
.venv/bin/python -m pytest tests/test_cenarios.py -v
```

O `-v` exibe o nome de cada teste individualmente. Sem ele, o pytest mostra apenas o resultado final.

---

### Como explicar a Fase 8 em uma entrevista

> "Os testes são de integração real — eles rodam contra o Portal da Transparência ao vivo, sem mock. A escolha foi intencional: o objetivo é garantir que o robô funciona no site real antes da apresentação, não testar lógica Python isolada. O `pytest-asyncio` com `asyncio_mode = auto` permite escrever os testes como funções `async` normais, sem nenhum decorador extra — o pytest detecta automaticamente."

---

### Resumo da Fase 8

| O que | Como |
|---|---|
| Habilitar testes async | `pytest.ini` com `asyncio_mode = auto` |
| Cenário 1 — sucesso por NIS | `NIS: 13233581857` → `status: sucesso`, pessoa e evidência presentes |
| Cenário 2 — erro por CPF | `CPF: 123.456.789-00` → `status: erro`, mensagem exata do desafio |
| Cenário 3 — sucesso por Nome | `Nome: Silva` → `status: sucesso`, pessoa e evidência presentes |
| Cenário 4 — erro por Nome | `Nome: xyzxyzabc987654` → `status: erro`, mensagem com o valor buscado |
| Cenário 5 — filtro social | `Nome: Silva` + `filtro_social: true` → `status: sucesso`, NIS presente |
| Estratégia | Integração real, sem mock — testa o portal ao vivo |

---

*Próxima fase: deploy (Dockerfile + configuração de servidor).*

---

## Fase 9 — Deploy na AWS EC2

### O que foi implementado

Três arquivos foram criados:

- `Dockerfile` — define como a imagem do container é construída
- `docker-compose.yml` — define como o container é executado no servidor
- `.dockerignore` — define quais arquivos não entram no container

O projeto está rodando em produção em `https://mostqi.paulodev.net`.

---

### Fase 9.1 — Análise da infraestrutura existente

Antes de criar qualquer arquivo, a EC2 foi inspecionada via SSH para entender o que já estava em execução.

#### Resultado da análise

| Item | Encontrado |
|---|---|
| Containers em execução | `aws-nicia-web-1` (porta 8000) e `aws-nicia-db-1` (PostgreSQL) |
| Porta 8000 | Ocupada pelo projeto existente |
| Porta 8001 | Disponível — escolhida para o novo projeto |
| Nginx | Instalado, versão 1.30.2 |
| Configuração Nginx | `/etc/nginx/conf.d/` (não `sites-enabled/`) |
| SSL | Certbot / Let's Encrypt (não Cloudflare como planejado) |
| Diretório do projeto existente | `/home/ec2-user/aws-nicia/` |

#### Diferenças em relação ao plano original

O plano assumia duas coisas que se mostraram diferentes na prática:

| Item | Plano | Realidade |
|---|---|---|
| SSL | Cloudflare | Certbot / Let's Encrypt |
| Config Nginx | `sites-enabled/` | `conf.d/` |

A abordagem foi adaptada para seguir o mesmo padrão do projeto existente (`nicia.paulodev.net`) — tanto para o Nginx quanto para o SSL via Certbot.

---

### Fase 9.2.5 — Validação em ambiente headless

Antes de criar o container, os testes foram executados localmente com `HEADLESS=true` para confirmar que o robô funciona sem interface gráfica.

```bash
# .env local temporariamente com HEADLESS=true
.venv/bin/python -m pytest tests/test_cenarios.py -v
```

**Resultado:** 5/5 passaram em 69 segundos. Nenhuma diferença de comportamento em relação ao modo com interface gráfica.

O `.env.example` foi atualizado para refletir `HEADLESS=true` como valor padrão para produção.

---

### Fase 9.3 — Dockerfile

#### Estrutura final

```dockerfile
FROM python:3.9-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Conceito — ordem das instruções e cache do Docker

O Docker armazena em cache cada camada da imagem. Uma camada só é reconstruída se ela ou alguma camada anterior mudar.

A ordem importa:

```
COPY requirements.txt .          ← muda raramente
RUN pip install ...              ← cacheado enquanto requirements não mudar
RUN playwright install ...       ← cacheado enquanto versão do playwright não mudar
COPY . .                         ← muda com frequência (código)
```

Se o código mudar mas as dependências não, o Docker pula os passos de instalação e vai direto para o `COPY . .`. Isso reduz o tempo de rebuild de minutos para segundos.

#### Conceito — `python:3.9-slim-bookworm`

O ambiente de desenvolvimento usa Python 3.9.6. A imagem base escolhida foi `python:3.9-slim-bookworm` para corresponder à versão local e fixar o Debian 12 (bookworm) explicitamente.

**Por que fixar bookworm e não usar apenas `python:3.9-slim`?**

Na data do deploy, a tag `python:3.9-slim` passou a apontar para Debian 13 (trixie). O Playwright 1.44.0 não reconhece o trixie oficialmente e tenta instalar dependências com nomes que foram renomeados nessa versão do Debian — causando falha no build.

Ao usar `python:3.9-slim-bookworm`, a versão do Debian fica fixa e previsível, independente de atualizações futuras da tag `slim`.

#### Obstáculo 1 — `docker compose up --build` exige buildx 0.17.0+

O Docker instalado na EC2 tinha uma versão do plugin de compose que exigia uma versão mais recente do buildx.

```
compose build requires buildx 0.17.0 or later
```

Solução: desabilitar o BuildKit para usar o builder clássico.

```bash
DOCKER_BUILDKIT=0 docker compose up --build -d
```

O BuildKit é o backend moderno de build do Docker. Sem ele, o Docker usa o builder original que funciona com qualquer versão do compose instalada.

#### Obstáculo 2 — pacotes de fonte não disponíveis no Debian trixie

Com a imagem `python:3.9-slim` (que apontava para trixie), o `playwright install --with-deps chromium` falhava:

```
E: Package 'ttf-unifont' has no installation candidate
E: Package 'ttf-ubuntu-font-family' has no installation candidate
```

Esses pacotes foram renomeados no Debian 13. O Playwright 1.44.0, ao não reconhecer o trixie, usava a lista de dependências do ubuntu20.04 — que continha os nomes antigos.

Solução: trocar `FROM python:3.9-slim` por `FROM python:3.9-slim-bookworm`.

#### Conceito — `playwright install --with-deps chromium`

O Playwright oferece duas formas de instalar o Chromium:

```bash
playwright install chromium              # só o browser
playwright install --with-deps chromium  # browser + dependências do sistema
```

A opção `--with-deps` automaticamente instala todos os pacotes do sistema operacional que o Chromium precisa para funcionar — como bibliotecas gráficas, fontes e codecs. Isso é mais robusto do que listar pacotes manualmente, porque o Playwright sabe exatamente quais dependências cada versão do Chromium precisa.

#### Conceito — `--host 0.0.0.0`

Por padrão, o uvicorn escuta apenas em `127.0.0.1` (localhost do container). Com `--host 0.0.0.0`, ele aceita conexões de qualquer endereço — o que permite que o Nginx, fora do container, consiga se conectar.

#### Conceito — `--no-cache-dir`

Evita que o pip armazene pacotes em cache dentro da imagem. Como o cache só seria útil em reinstalações futuras (que não acontecem em containers), removê-lo reduz o tamanho final da imagem.

---

### Fase 9.4 — docker-compose.yml

#### Estrutura final

```yaml
services:
  mostqi-rpa:
    build: .
    container_name: mostqi-rpa
    ports:
      - "8001:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

#### Conceito — mapeamento de portas `8001:8000`

O formato é `PORTA_DO_HOST:PORTA_DO_CONTAINER`.

- `8000` é onde o uvicorn escuta dentro do container
- `8001` é a porta exposta no sistema operacional da EC2

A porta `8001` foi escolhida porque a `8000` já estava ocupada pelo projeto `aws-nicia`. O Nginx vai se conectar à `8001` do host para chegar à API.

#### Conceito — healthcheck sem curl

A imagem `python:3.9-slim-bookworm` não inclui curl. Em vez de instalar curl só para o healthcheck, usamos Python — que já está disponível:

```
["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"]
```

`urllib.request` lança uma exceção se a conexão falhar ou se o servidor retornar erro — o Docker interpreta isso como falha no healthcheck. Se `/docs` responder 200 OK, o healthcheck passa.

O `start_period: 10s` dá 10 segundos para o uvicorn iniciar antes de começar as verificações — evita falsos negativos logo após o container subir.

#### Conceito — `restart: unless-stopped`

Se o container cair por qualquer motivo (erro, reinicialização da EC2), o Docker o reinicia automaticamente. A única exceção é quando parado manualmente com `docker compose down`.

---

### Fase 9.6 — Transferência para a EC2

#### Autenticação SSH com GitHub

O repositório é privado. Para clonar na EC2 sem expor credenciais, foi criada uma chave SSH dedicada ao deploy:

```bash
ssh-keygen -t ed25519 -C "ec2-deploy" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # chave adicionada ao GitHub → Settings → SSH keys
ssh -T git@github.com      # confirmação: "Hi paulo9405! You've successfully authenticated"
```

O clone foi feito com SSH (não HTTPS) para evitar prompt de senha em `git pull` futuros:

```bash
git clone git@github.com:paulo9405/-desafios-fullstack-python.git mostqi-rpa
```

O projeto foi clonado em `/home/ec2-user/mostqi-rpa/`. O `.env` de produção foi criado a partir do `.env.example` (que já tem `HEADLESS=true`):

```bash
cp .env.example .env
```

---

### Fase 9.7 — Container em execução na EC2

```bash
DOCKER_BUILDKIT=0 docker compose up --build -d
```

**Resultado:**

```
✔ Image desafio-01-mostqi-rpa Built    71.2s
✔ Network desafio-01_default Created
✔ Container mostqi-rpa Started
```

Verificação:

```bash
docker compose ps
# NAME         STATUS                    PORTS
# mostqi-rpa   Up 33 seconds (healthy)   0.0.0.0:8001->8000/tcp

curl http://localhost:8001/docs
# HTML do Swagger UI retornado com sucesso
```

O container iniciou em menos de 1 segundo e ficou `(healthy)` em 10 segundos — o healthcheck passou na primeira verificação.

---

### Como explicar a Fase 9 em uma entrevista

> "O deploy foi feito em uma EC2 que eu já tinha na AWS, ao lado de outro projeto. Usei Docker para isolar completamente o novo projeto — cada um tem seu próprio container, porta e arquivo `.env`. O container expõe a porta `8001` porque a `8000` já estava em uso. O Nginx faz o proxy reverso: `mostqi.paulodev.net` → `127.0.0.1:8001`. O SSL é gerenciado pelo Certbot com Let's Encrypt, igual ao outro projeto já em produção. O Playwright rodando em headless dentro do container funciona exatamente igual ao ambiente local — validamos isso antes do deploy com `HEADLESS=true` nos testes."

---

### Resumo da Fase 9 (até aqui)

| Subfase | O que | Resultado |
|---|---|---|
| 9.1 | Análise da EC2 | Porta 8001 livre, Nginx em `conf.d/`, SSL via Certbot |
| 9.2.5 | Validação headless | 5/5 testes passaram com `HEADLESS=true` |
| 9.3 | Dockerfile | Criado com `python:3.9-slim-bookworm` + `playwright install --with-deps` |
| 9.4 | docker-compose.yml | Criado com porta 8001, healthcheck Python, restart automático |
| 9.6 | Transferência para EC2 | Clone via SSH em `/home/ec2-user/mostqi-rpa/` |
| 9.7 | Container rodando | `(healthy)` na porta 8001, Swagger acessível |

---

*Próximas subfases: 9.8 (Nginx), 9.9 (Certbot SSL), 9.10 (testes em produção).*

---

### Fase 9.8 — Configuração do Nginx

#### O que foi feito

Criado o arquivo `/etc/nginx/conf.d/mostqi.conf` na EC2:

```nginx
server {
    listen 80;
    server_name mostqi.paulodev.net;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }
}
```

Validado e recarregado:

```bash
sudo nginx -t
# nginx: configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

sudo systemctl reload nginx
```

#### Diferença em relação ao plano

O plano original previa usar `/etc/nginx/sites-enabled/`. A EC2 usa `/etc/nginx/conf.d/` — o mesmo padrão do projeto existente (`nicia-track.conf`). A configuração foi criada seguindo esse padrão.

#### Conceito — proxy reverso

O Nginx recebe a requisição externa na porta 80 e encaminha para o container Docker na porta 8001:

```
Internet → mostqi.paulodev.net:80 → Nginx → 127.0.0.1:8001 → Container (API)
```

O container não precisa estar exposto diretamente para a internet. Apenas as portas 80 e 443 ficam abertas para acesso externo — o Nginx decide para onde cada requisição vai com base no `server_name`.

#### Conceito — `proxy_read_timeout 120`

O robô pode levar até 60-90 segundos para completar uma consulta no portal. O Nginx tem timeout padrão de 60 segundos. Sem esse ajuste, o Nginx cancelaria a requisição antes do robô terminar e retornaria erro 504 ao cliente.

#### Conceito — headers de proxy

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Esses headers informam à aplicação quem é o cliente real. Sem eles, a API enxergaria todas as requisições como vindas de `127.0.0.1` (o Nginx), perdendo o IP original do cliente.

---

### Fase 9.9 — SSL com Certbot

#### O que foi feito

Antes de rodar o Certbot, o registro DNS foi criado no Cloudflare:

| Campo | Valor |
|---|---|
| Tipo | A |
| Nome | `mostqi` |
| IPv4 | `3.148.15.93` |
| Proxy status | DNS only (nuvem cinza) |

O proxy foi desativado para que o Certbot conseguisse validar o domínio via HTTP-01 challenge — o desafio HTTP exige que o Certbot acesse diretamente a porta 80 da EC2, sem intermediário.

Após a propagação do DNS (~2 minutos), o Certbot foi executado:

```bash
sudo certbot --nginx -d mostqi.paulodev.net
```

**Resultado:**

```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/mostqi.paulodev.net/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/mostqi.paulodev.net/privkey.pem
This certificate expires on 2026-10-06.
Certbot has set up a scheduled task to automatically renew this certificate in the background.

Successfully deployed certificate for mostqi.paulodev.net to /etc/nginx/conf.d/mostqi.conf
Congratulations! You have successfully enabled HTTPS on https://mostqi.paulodev.net
```

O Certbot modificou automaticamente o `mostqi.conf` para incluir SSL — o mesmo comportamento observado no `nicia-track.conf` já existente.

#### Diferença em relação ao plano

O plano original previa usar o Cloudflare para SSL (proxy ativado). A EC2 já usava Certbot/Let's Encrypt para o `nicia.paulodev.net`. A abordagem foi adaptada para seguir o mesmo padrão — Certbot com DNS only no Cloudflare.

#### Conceito — HTTP-01 challenge

O Certbot precisa provar para a Let's Encrypt que você controla o domínio. O método HTTP-01 funciona assim:

1. Certbot cria um arquivo temporário em `/.well-known/acme-challenge/`
2. Let's Encrypt tenta acessar `http://mostqi.paulodev.net/.well-known/acme-challenge/...`
3. Se conseguir ler o arquivo, o domínio está validado
4. Certbot recebe o certificado

Por isso o proxy do Cloudflare precisa estar desativado: com o proxy ativo, o Cloudflare intercepta a requisição e a Let's Encrypt não consegue chegar diretamente à EC2.

#### Conceito — renovação automática

Certificados Let's Encrypt expiram em 90 dias. O Certbot configura automaticamente um cron job que renova o certificado antes do vencimento — sem intervenção manual.

```bash
# Verificar renovação automática
sudo certbot renew --dry-run
```

#### Como explicar em uma entrevista

> "O SSL foi provisionado com Certbot e Let's Encrypt, o mesmo padrão do outro projeto na mesma EC2. O Certbot valida o domínio via HTTP-01 challenge — por isso o proxy do Cloudflare precisa estar desativado durante a validação. Após emitir o certificado, o Certbot modifica automaticamente o Nginx para servir HTTPS e agenda a renovação automática a cada 90 dias."

---

### Resumo das Fases 9.8 e 9.9

| O que | Como |
|---|---|
| Arquivo Nginx | `/etc/nginx/conf.d/mostqi.conf` |
| Proxy reverso | `mostqi.paulodev.net:443` → `127.0.0.1:8001` |
| Timeout configurado | `proxy_read_timeout 120` |
| Certificado SSL | Let's Encrypt via Certbot |
| Validade do certificado | Até 2026-10-06, renovação automática |
| DNS durante validação | Cloudflare em modo DNS only (nuvem cinza) |
| HTTPS ativo | `https://mostqi.paulodev.net` |

---

*Próxima subfase: 9.10 (testes finais em produção).*

---

## Fase 9.10 — Testes em produção e correção de timeout

### O que foi encontrado

Após o deploy, a API respondia HTTP 200 e o Swagger abria corretamente em `https://mostqi.paulodev.net/docs`. Porém, todas as consultas ao Portal da Transparência retornavam erro:

```json
{"status": "erro", "mensagem_erro": "Erro interno: Timeout 30000ms exceeded."}
```

---

### Diagnóstico — três problemas em sequência

---

**Problema 1 — Timeout de 30 segundos insuficiente para EC2**

Localmente, 30 segundos eram suficientes para o portal responder. Da EC2, o portal demora mais — o WAF da AWS é mais agressivo para IPs de servidor e adiciona latência extra.

Solução: aumentar `PLAYWRIGHT_TIMEOUT` para 90000ms diretamente no `.env` da EC2:

```bash
sed -i 's/PLAYWRIGHT_TIMEOUT=30000/PLAYWRIGHT_TIMEOUT=90000/' .env
docker compose down && docker compose up -d
```

Verificação de que o env var chegou ao container:

```bash
docker exec mostqi-rpa printenv PLAYWRIGHT_TIMEOUT
# 90000
```

---

**Problema 2 — Navigation timeout ignorava o `PLAYWRIGHT_TIMEOUT`**

Mesmo com `PLAYWRIGHT_TIMEOUT=90000` no container, o erro continuava dizendo `Timeout 30000ms exceeded.`. O env var estava chegando corretamente, mas o código só aplicava o timeout via `page.set_default_timeout()`.

O Playwright tem dois timeouts separados:

| Timeout | Configurado por | Afeta |
|---|---|---|
| Default timeout | `page.set_default_timeout()` | Ações (click, fill, locator...) |
| Navigation timeout | `page.set_default_navigation_timeout()` | `goto()`, `wait_for_load_state()` |

O código só chamava `set_default_timeout()`. As operações de navegação continuavam usando o padrão interno de 30000ms.

Solução: adicionar `set_default_navigation_timeout()` e passar `timeout=PLAYWRIGHT_TIMEOUT` explicitamente em cada chamada de navegação:

```python
page.set_default_timeout(PLAYWRIGHT_TIMEOUT)
page.set_default_navigation_timeout(PLAYWRIGHT_TIMEOUT)  # ← adicionado

await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
await page.wait_for_load_state("load", timeout=PLAYWRIGHT_TIMEOUT)
```

---

**Problema 3 — `wait_for_load_state("networkidle")` nunca terminava**

Com o timeout corrigido para 90 segundos, o erro mudou para `Timeout 90000ms exceeded.`. O código estava chegando mais longe, mas agora o próprio `networkidle` esgotava os 90 segundos.

**Por que `networkidle` falha em portais governamentais:**

`wait_for_load_state("networkidle")` espera até que não haja nenhuma requisição de rede ativa por pelo menos 500ms. O Portal da Transparência tem scripts de analytics, telemetria e monitoramento que continuam fazendo requisições em background indefinidamente. Da EC2, esse estado nunca é atingido dentro de 90 segundos.

Solução: substituir `networkidle` por estratégias que esperam apenas o que o robô realmente precisa:

```python
# ANTES — esperava zero requisições de rede por 500ms (nunca acontecia)
await page.goto(PORTAL_URL)
await page.wait_for_load_state("networkidle")

# DEPOIS — espera o HTML ser processado e o campo de busca estar disponível
await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
await page.wait_for_selector(SELETOR_CAMPO_BUSCA, timeout=PLAYWRIGHT_TIMEOUT)
```

Para as navegações internas (após busca e após clicar no resultado):

```python
# ANTES
await page.wait_for_load_state("networkidle")

# DEPOIS — espera o evento load (recursos principais carregados, ignora analytics)
await page.wait_for_load_state("load", timeout=PLAYWRIGHT_TIMEOUT)
```

**Comparação dos estados de carregamento:**

| Estado | O que espera | Velocidade |
|---|---|---|
| `domcontentloaded` | HTML processado (sem scripts/imagens) | Muito rápido |
| `load` | Todos os recursos da página carregados | Rápido |
| `networkidle` | Zero requisições de rede por 500ms | Lento / pode nunca acontecer |

---

### Resultado após as correções

Busca por Nome retornou `"status": "sucesso"` com JSON completo e `evidencia_base64` preenchido. O portal respondeu em aproximadamente 30-45 segundos a partir da EC2.

---

### `.env.example` atualizado

O valor padrão de `PLAYWRIGHT_TIMEOUT` foi atualizado para refletir o mínimo necessário para produção em EC2:

```
# Antes
PLAYWRIGHT_TIMEOUT=30000

# Depois
PLAYWRIGHT_TIMEOUT=90000
```

---

### Como explicar em uma entrevista

> "Em produção na EC2, o robô enfrentou dois problemas de timeout. O primeiro era o timeout de 30 segundos — insuficiente para o WAF da AWS, que adiciona latência extra para IPs de servidor. O segundo era o `wait_for_load_state('networkidle')` — ele espera até zero requisições de rede por 500ms, mas portais governamentais têm scripts de analytics que nunca param. A solução foi usar `domcontentloaded` para a navegação inicial e esperar pelo seletor específico que precisávamos, em vez de esperar a rede inteira silenciar."

---

### Resumo da Fase 9.10

| O que | Como |
|---|---|
| Timeout insuficiente | `PLAYWRIGHT_TIMEOUT=90000` no `.env` da EC2 |
| Navigation timeout separado | `page.set_default_navigation_timeout(PLAYWRIGHT_TIMEOUT)` + timeout explícito em cada chamada |
| `networkidle` nunca terminava | Substituído por `domcontentloaded` + `wait_for_selector` e `load` |
| `.env.example` atualizado | `PLAYWRIGHT_TIMEOUT=90000` como padrão recomendado |

---

*Próxima subfase: 9.11 (testes dos 5 cenários em produção).*

---

## Fase 9.11 — Testes dos 5 cenários em produção

### O que foi testado

Os 5 cenários exigidos pelo desafio foram executados contra `https://mostqi.paulodev.net/consulta`.

---

### Obstáculo — Cenário 5 retornava 504 Gateway Time-out

Os cenários 1, 2, 3 e 4 passaram na primeira rodada. O cenário 5 (filtro social) retornou:

```html
<html>
<head><title>504 Gateway Time-out</title></head>
<body><center><h1>504 Gateway Time-out</h1></center>
<hr><center>nginx/1.30.2</center></body>
</html>
```

O erro 504 vem do **Nginx**, não do Playwright. Significa que o Nginx encerrou a conexão antes do robô terminar.

**Por que o cenário 5 demora mais:**

O fluxo com filtro social tem mais etapas do que os outros cenários:

```
1. Abrir o portal
2. Preencher o campo de busca
3. Abrir o painel "REFINE A BUSCA"   ← passo extra
4. Marcar "Beneficiário de Programa Social"  ← passo extra
5. Clicar em "Consultar"
6. Aguardar resultados carregarem
7. Clicar no primeiro resultado
8. Aguardar página da pessoa carregar
9. Extrair dados
10. Tirar screenshot
```

Com a latência da EC2 para o portal, esse fluxo ultrapassa os 120 segundos configurados no `proxy_read_timeout` do Nginx.

**Correção — aumentar `proxy_read_timeout` para 300 segundos:**

```bash
sudo sed -i 's/proxy_read_timeout 120/proxy_read_timeout 300/' /etc/nginx/conf.d/mostqi.conf
sudo nginx -t
sudo systemctl reload nginx
```

Não foi necessário rebuildar o container — a alteração é apenas no Nginx.

---

### Resultado final — 5/5 cenários passaram

| # | Cenário | Entrada | Status | Mensagem |
|---|---|---|---|---|
| 1 | NIS válido | `NIS: 13233581857` | ✅ `sucesso` | — |
| 2 | CPF inexistente | `CPF: 123.456.789-00` | ✅ `erro` | `"Não foi possível retornar os dados no tempo de resposta solicitado"` |
| 3 | Nome sucesso | `Nome: Silva` | ✅ `sucesso` | — |
| 4 | Nome inexistente | `Nome: xyzxyzabc987654` | ✅ `erro` | `"Foram encontrados 0 resultados para o termo xyzxyzabc987654"` |
| 5 | Filtro social | `Nome: Silva`, `filtro_social: true` | ✅ `sucesso` | — |

---

### Como explicar em uma entrevista

> "Em produção, o cenário com filtro social retornava 504 Gateway Time-out. O erro vinha do Nginx, não do robô — o fluxo com filtro tem dois passos extras (abrir o painel e marcar o checkbox) e ultrapassava os 120 segundos configurados no proxy_read_timeout. A correção foi aumentar esse timeout para 300 segundos. Não foi necessário rebuildar o container — apenas recarregar o Nginx."

---

### Resumo da Fase 9.11

| O que | Como |
|---|---|
| Cenários 1, 2, 3, 4 | Passaram sem ajuste adicional |
| Cenário 5 — 504 do Nginx | `proxy_read_timeout` aumentado de 120s para 300s |
| Arquivo alterado | `/etc/nginx/conf.d/mostqi.conf` |
| Comando para aplicar | `sudo systemctl reload nginx` (sem rebuild do container) |
| Resultado final | 5/5 cenários funcionando em produção |

---

*Deploy concluído. API disponível em `https://mostqi.paulodev.net`.*

---

## Fase 9.12 — Guia de Apresentação: Deploy

### O que foi feito

Esta fase não adiciona código — ela consolida os pontos principais do deploy para que sejam explicados com clareza durante a apresentação técnica.

---

### A arquitetura em uma linha

```
Cliente → Cloudflare (DNS) → Nginx (proxy reverso) → Docker (FastAPI + Playwright)
```

---

### Por que cada peça existe

**AWS EC2**

A EC2 já estava em uso com outro projeto (`nicia.paulodev.net`). Usar a mesma máquina foi uma decisão deliberada: não abrir infraestrutura nova, demonstrar que dois projetos coexistem de forma isolada no mesmo servidor.

**Docker**

Sem Docker, instalar Playwright + Chromium + Python diretamente na EC2 criaria conflito com as dependências do outro projeto. Com Docker, cada projeto tem seu container independente — incluindo suas próprias versões de bibliotecas e variáveis de ambiente.

```
/home/ec2-user/
├── aws-nicia/          ← projeto existente, porta 8000
└── mostqi-rpa/         ← novo projeto, porta 8001
```

**Nginx**

O Nginx é o único ponto de entrada externo. Ele recebe a requisição em `mostqi.paulodev.net` e encaminha para `127.0.0.1:8001` — a porta do container. A porta 8001 nunca fica exposta diretamente para a internet.

O `proxy_read_timeout 300` foi necessário porque o robô pode levar até 3 minutos no cenário com filtro social (mais etapas de navegação + latência da EC2 para o portal).

**Certbot / Let's Encrypt**

O SSL foi emitido via Certbot seguindo o mesmo padrão já existente na EC2 (`nicia.paulodev.net`). O Cloudflare ficou em modo DNS only durante a validação — o HTTP-01 challenge exige acesso direto à porta 80, sem proxy na frente. Após emitir o certificado, o Certbot modificou o `mostqi.conf` automaticamente e configurou renovação automática a cada 90 dias.

---

### Obstáculos reais encontrados no deploy

| Obstáculo | Causa | Solução |
|---|---|---|
| Timeout 30s insuficiente | WAF da AWS adiciona latência extra para IPs de servidor | `PLAYWRIGHT_TIMEOUT=90000` no `.env` da EC2 |
| Navigation timeout ignorava a config | `set_default_timeout()` não afeta `goto()` e `wait_for_load_state()` | Adicionado `set_default_navigation_timeout()` + timeout explícito em cada chamada |
| `networkidle` nunca terminava | Portal tem scripts de analytics em background indefinidamente | Substituído por `domcontentloaded` + `wait_for_selector` |
| 504 no cenário 5 | Fluxo com filtro social ultrapassa 120s de `proxy_read_timeout` | Aumentado para 300s no Nginx (sem rebuild do container) |
| `docker compose up --build` falhava | Versão do buildx na EC2 abaixo do exigido pelo compose | `DOCKER_BUILDKIT=0 docker compose up --build -d` |
| Pacotes de fonte não encontrados | Imagem `python:3.9-slim` apontava para Debian 13 (trixie); Playwright 1.44 não reconhece o trixie | Fixado `FROM python:3.9-slim-bookworm` |

---

### Como explicar em uma entrevista

> "O deploy foi feito em uma EC2 que eu já usava para outro projeto. Usei Docker para isolar completamente os dois projetos — cada um tem seu container, sua porta e seu próprio `.env`. O Nginx faz o proxy reverso: `mostqi.paulodev.net` chega na EC2, o Nginx identifica pelo domínio e encaminha para o container na porta 8001. O SSL é gerenciado pelo Certbot com Let's Encrypt, com renovação automática a cada 90 dias. Em produção apareceram três problemas que não existiam localmente: timeout insuficiente, `networkidle` que nunca terminava por causa de scripts de analytics do portal, e um 504 do Nginx no cenário com filtro social. Os três foram corrigidos sem rebuildar o container."

---

### Resumo da Fase 9.12

| Componente | O que faz no projeto |
|---|---|
| EC2 | Hospeda os dois projetos com isolamento total via Docker |
| Docker | Encapsula Playwright + Chromium + FastAPI sem conflito com outros projetos |
| docker-compose.yml | Define porta 8001, restart automático e healthcheck via Python |
| Nginx | Proxy reverso com `proxy_read_timeout 300` para aguentar o fluxo do robô |
| Certbot | SSL automático com renovação a cada 90 dias |
| Cloudflare | DNS do domínio `mostqi.paulodev.net` apontando para o IP da EC2 |

---

*Fase 9 concluída.*

---

## Fase 10 — Coleta de Benefícios

### O que foi implementado

Três alterações em `app/scraper.py`:

1. `Beneficio` e `DetalhesBeneficio` adicionados ao import de `schemas`
2. Constante `BENEFICIOS_CONHECIDOS` com os tipos monitorados
3. Função `_extrair_beneficios()` — coleta tipo e valor de cada benefício presente na página
4. `executar_consulta()` atualizado: chama `_extrair_beneficios()` e passa o resultado para `ConsultaSaida`

A seção "RECEBIMENTOS DE RECURSOS" já estava expandida pela `_extrair_nis()`, então não é necessário expandir novamente.

---

### Estratégia de extração

O portal exibe os benefícios dentro de tabelas. Cada tabela tem um título antes dela indicando o tipo de benefício (ex: "Bolsa Família", "Benefício de Prestação Continuada").

O problema: não existe um seletor CSS direto que associe um título à sua tabela, porque a estrutura do DOM varia conforme os benefícios presentes. A solução foi usar `page.evaluate()` para rodar JavaScript diretamente no DOM:

```python
valor = await page.evaluate(
    """(nome) => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (node.textContent.trim() === nome) {
                let el = node.parentElement;
                for (let i = 0; i < 6; i++) {
                    if (!el) break;
                    const table = el.querySelector('table');
                    if (table) {
                        const row = table.querySelector('tbody tr');
                        if (row) {
                            const cells = Array.from(row.querySelectorAll('td'));
                            return cells[cells.length - 1]?.textContent?.trim() ?? null;
                        }
                    }
                    el = el.parentElement;
                }
            }
        }
        return null;
    }""",
    tipo,
)
```

O script percorre os nós de texto do DOM até encontrar exatamente o nome do benefício, depois sobe na árvore até encontrar uma `<table>` no mesmo bloco e pega o valor da última coluna da primeira linha.

---

### Conceito — `page.evaluate()` com argumento

`page.evaluate()` executa JavaScript no contexto do navegador e retorna o resultado para o Python. O argumento `tipo` é passado de forma segura como segundo parâmetro — não é concatenado na string JS, o que evita problemas com caracteres especiais (como o "ã" de "Bolsa Família").

```python
# Correto — tipo é passado como argumento JS, não interpolado na string
valor = await page.evaluate("(nome) => { ... }", tipo)

# Errado — interpolação pode quebrar com caracteres especiais
valor = await page.evaluate(f"() => {{ ... '{tipo}' ... }}")
```

---

### Limitação documentada — Competência

O campo `competencia` do JSON fica `null`. A competência (mês de referência do benefício) está disponível apenas na **página de detalhe**, acessível pelo link "Detalhar" em cada linha da tabela. Navegar para cada detalhe e voltar aumentaria significativamente a complexidade e o tempo de resposta. Os schemas já definem o campo como `Optional[str]`, então a ausência do valor é válida pelo contrato da API.

---

### Como explicar em uma entrevista

> "Os benefícios são coletados da seção RECEBIMENTOS DE RECURSOS, que já fica expandida pelo passo anterior de extração do NIS. O desafio era associar cada tipo de benefício à sua tabela — o DOM do portal não tem um seletor CSS direto pra isso. A solução foi usar `page.evaluate()` para rodar JavaScript no navegador: percorro os nós de texto até achar o nome do benefício, subo na árvore do DOM e pego o valor da tabela mais próxima. O campo competência ficou null porque requereria navegar para a página de detalhe de cada benefício e voltar — custo alto demais para o ganho, e o schema já prevê o campo como opcional."

---

### Resumo da Fase 10

| O que | Como |
|---|---|
| Tipos monitorados | `BENEFICIOS_CONHECIDOS` — lista de nomes exatos como aparecem no portal |
| Localizar cada benefício | `page.locator("text=Tipo")` para verificar se existe na página |
| Extrair o valor | `page.evaluate()` com TreeWalker navegando o DOM |
| Competência | `null` — requer página de detalhe, fora do escopo |
| Integração no fluxo | Chamado após `_extrair_dados_pessoa()`, antes do screenshot |

---

## Correção pós-deploy — Timeout na verificação de resultados

### O que foi corrigido

Em `_verificar_resultado_busca()`, o trecho que aguarda o primeiro link clicável aparecer usava `timeout=5000` (5 segundos fixos):

```python
# ANTES — 5 segundos fixos, insuficiente quando o portal está lento
await page.locator(SELETOR_PRIMEIRO_RESULTADO).first.wait_for(state="visible", timeout=5000)
```

Em condições normais 5 segundos eram suficientes. Com instabilidade do portal ou latência maior na EC2, a página de resultados demorava mais que isso para renderizar o primeiro link — e o robô caia no `except PlaywrightTimeoutError` retornando falso erro.

**Correção:** usar `PLAYWRIGHT_TIMEOUT` (configurável via `.env`, padrão 90 segundos na EC2):

```python
# DEPOIS — usa o mesmo timeout configurado para todas as operações
await page.locator(SELETOR_PRIMEIRO_RESULTADO).first.wait_for(state="visible", timeout=PLAYWRIGHT_TIMEOUT)
```

### Por que isso não afeta os cenários de erro

Os casos de "sem resultado" são detectados **antes** desse `wait_for`, por checagem de texto na página:

```python
if await page.locator("text=Foram encontrados 0 resultados").count() > 0:
    return MENSAGEM_ERRO_NOME / MENSAGEM_ERRO_CPF  # retorna imediatamente

if await page.locator(f"text={MENSAGEM_ERRO_CPF}").count() > 0:
    return MENSAGEM_ERRO_CPF  # retorna imediatamente
```

Só chega no `wait_for` quando nenhum texto de erro foi encontrado — ou seja, há resultados esperando carregar. O timeout longo nesse ponto é correto.

### Resumo

| O que | Como |
|---|---|
| Timeout anterior | `5000ms` fixo — falhava com portal lento |
| Timeout novo | `PLAYWRIGHT_TIMEOUT` — consistente com o resto do scraper |
| Cenários de erro | Não afetados — detectados antes por checagem de texto |
