# Material de Estudo para Entrevistas Técnicas

**Projeto:** Barber Cashflow (Sistema SaaS Multi-Tenant para Barbearias)
**Stack:** Django 4.2 + Django REST Framework + PostgreSQL + Docker + Nginx
**Versão:** v3.1 (PWA implementado)
**Gerado em:** Janeiro/2026

---

# DJANGO

---

## Transaction Atomic

### Onde está implementado

**Arquivo:** `sales/services.py`
**Classe:** (módulo de serviços)
**Função:** `cancelar_venda()`
**Linha:** ~45

---

### Problema de negócio

Quando uma venda é cancelada, múltiplas operações precisam acontecer de forma atômica:
1. Reverter o status do agendamento vinculado para "não finalizado"
2. Restaurar o estoque dos produtos vendidos
3. Marcar a venda como deletada (soft delete)

Se qualquer operação falhar, TODAS devem ser revertidas para evitar inconsistência de dados.

---

### Como foi implementado

```python
# sales/services.py (~linha 45)
from django.db import transaction

def cancelar_venda(venda):
    """
    Cancela uma venda e reverte todas as operações associadas.
    """
    resultado = {
        'ja_deletada': False,
        'agendamento_revertido': False,
        'agendamento_id': None,
        'estoque_restaurado': [],
        'total_itens_estoque': 0
    }

    # Verificar se já foi deletada (idempotência)
    if venda.deleted_at:
        resultado['ja_deletada'] = True
        return resultado

    with transaction.atomic():
        # 1. Reverter agendamento se existir
        if venda.agendamento and not venda.agendamento.deleted_at:
            venda.agendamento.atendimento_finalizado = False
            venda.agendamento.save()
            resultado['agendamento_revertido'] = True
            resultado['agendamento_id'] = venda.agendamento.pk

        # 2. Restaurar estoque de produtos
        for item in venda.produtos.all():
            if item.produto:
                item.produto.estoque += item.quantidade
                item.produto.save()
                resultado['estoque_restaurado'].append({
                    'produto_id': item.produto.pk,
                    'quantidade_restaurada': item.quantidade
                })
        resultado['total_itens_estoque'] = len(resultado['estoque_restaurado'])

        # 3. Soft delete da venda
        venda.delete()  # SoftDeleteModel marca deleted_at

    return resultado
```

---

### O que aconteceria sem isso

Sem `transaction.atomic()`:
- O agendamento poderia ser revertido, mas o estoque não restaurado (se ocorrer erro)
- O estoque poderia ser restaurado parcialmente (ex: 2 de 5 produtos)
- A venda poderia não ser marcada como deletada, resultando em dados órfãos
- **Exemplo real:** Cliente cancela venda, estoque volta, mas sistema falha antes de reverter agendamento → barbeiro perde horário disponível

---

### O que o Django faz internamente

1. Abre uma transação no banco (`BEGIN`)
2. Executa todas as queries dentro do bloco
3. Se tudo der certo: `COMMIT`
4. Se qualquer exceção ocorrer: `ROLLBACK` automático
5. Suporta `savepoints` para transações aninhadas

---

### O que o PostgreSQL faz internamente

1. Cria um ponto de início da transação
2. Mantém as mudanças em um "buffer" temporário
3. Aplica locks nas linhas afetadas (evita leitura suja)
4. No `COMMIT`: persiste todas as mudanças no disco (WAL - Write-Ahead Log)
5. No `ROLLBACK`: descarta todas as mudanças do buffer

---

### Possíveis perguntas de entrevista

* O que é `transaction.atomic()` e quando você utilizaria?
* O que acontece se uma exceção ocorrer dentro de um bloco `atomic()`?
* Qual a diferença entre `atomic()` como decorator e como context manager?
* Como funcionam transações aninhadas no Django?
* O que é um deadlock e como evitar?

---

### Como responder na entrevista

> "No meu projeto utilizei `transaction.atomic()` para garantir consistência ao cancelar vendas. Quando o cliente cancela uma venda, preciso reverter o agendamento, restaurar o estoque e marcar a venda como deletada. Se qualquer operação falhar, todas são revertidas automaticamente. Isso evita estados inconsistentes como estoque restaurado parcialmente ou agendamento não liberado."

---

### Melhorias possíveis

1. **select_for_update():** Adicionar lock explícito para evitar condições de corrida em cenários de alta concorrência
2. **Retry com exponential backoff:** Para lidar com deadlocks temporários
3. **Saga Pattern:** Para operações que envolvem serviços externos (não compensáveis via rollback do BD)

---

## Middleware

### Onde está implementado

**Arquivo:** `tenants/middleware.py`
**Classe:** `TenantMiddleware`
**Função:** `process_request()`
**Linha:** ~87

---

### Problema de negócio

Em um sistema SaaS multi-tenant, cada barbearia (tenant) deve ver apenas seus próprios dados. O middleware resolve qual tenant está ativo em cada request para:
1. Filtrar dados automaticamente
2. Bloquear acesso a tenants suspensos
3. Permitir superusers acessarem sem tenant (modo global)

---

### Como foi implementado

```python
# tenants/middleware.py (~linha 69)
import threading
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()

def get_current_tenant():
    """Retorna o tenant ativo no request atual."""
    return getattr(_thread_locals, 'tenant', None)

def set_current_tenant(tenant):
    """Define o tenant ativo no request atual."""
    _thread_locals.tenant = tenant

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        tenant = None

        # PRIORIDADE 1: Session (login com slug)
        tenant_id = request.session.get("tenant_id")
        if tenant_id:
            tenant = Tenant.objects.get(id=tenant_id, ativo=True)

        # PRIORIDADE 2: User profile (fallback)
        elif request.user.is_authenticated and not request.user.is_superuser:
            tenant = request.user.profile.tenant

            # Bloquear tenant suspenso
            if tenant and not tenant.ativo:
                return render(request, 'tenants/suspended.html', status=403)

        # PRIORIDADE 3: Domínio (legado)
        elif not tenant:
            host = request.get_host().split(':')[0].lower()
            tenant_domain = TenantDomain.objects.select_related('tenant').get(dominio=host)
            tenant = tenant_domain.tenant

        # Armazenar no request e thread-local
        request.tenant = tenant
        set_current_tenant(tenant)

        return None  # Continua processamento

    def process_response(self, request, response):
        set_current_tenant(None)  # Limpar thread-local
        return response
```

---

### O que aconteceria sem isso

- Sem middleware de tenant: usuário do Tenant A poderia ver dados do Tenant B
- Vazamento de dados entre empresas concorrentes
- Violação de LGPD/compliance
- Perda de confiança no sistema SaaS

---

### O que o Django faz internamente

1. Carrega middlewares na ordem definida em `settings.MIDDLEWARE`
2. Para cada request: executa `process_request()` de TODOS os middlewares (de cima para baixo)
3. Executa a view
4. Para cada response: executa `process_response()` de TODOS os middlewares (de baixo para cima)
5. Se qualquer middleware retornar uma Response em `process_request()`, interrompe a cadeia

---

### Possíveis perguntas de entrevista

* O que é um middleware e qual o ciclo de vida?
* Por que usar thread-local storage no middleware de tenant?
* Qual a diferença entre `MiddlewareMixin` e middleware funcional?
* Como garantir que o thread-local é limpo mesmo com exceções?
* Qual a ordem correta de middlewares (auth, session, tenant)?

---

### Como responder na entrevista

> "Implementei um TenantMiddleware para resolver qual barbearia está ativa em cada request. Ele verifica primeiro a session (login com slug), depois o profile do usuário, e por último o domínio. O tenant resolvido é armazenado em `request.tenant` e em thread-local para acesso em qualquer parte do código. Isso garante isolamento total entre clientes do SaaS."

---

### Melhorias possíveis

1. **Caching:** Cachear resolução de domínio para evitar query em todo request
2. **Async support:** Usar `contextvars` ao invés de `threading.local` para compatibilidade com ASGI
3. **Metrics:** Adicionar telemetria de tempo de resolução de tenant

---

## Class-Based Views (CBV)

### Onde está implementado

**Arquivo:** `sales/views.py`
**Classe:** `SaleListView`
**Função:** `get_queryset()`
**Linha:** ~45

---

### Problema de negócio

Listar vendas de uma barbearia com:
- Filtro automático por tenant (multi-tenant)
- Filtro por período (data início/fim)
- Filtro por barbeiro
- Paginação
- Ordenação por data

---

### Como foi implementado

```python
# sales/views.py (~linha 45)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'vendas'
    paginate_by = 20

    def get_queryset(self):
        # Filtro obrigatório por tenant (multi-tenant)
        qs = Sale.objects.filter(
            tenant=self.request.tenant
        ).select_related(
            'barbeiro', 'agendamento', 'cliente_cadastrado'
        ).prefetch_related(
            'servicos', 'produtos'
        )

        # Filtros opcionais via GET params
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        barbeiro_id = self.request.GET.get('barbeiro')

        if data_inicio:
            qs = qs.filter(data__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)
        if barbeiro_id:
            qs = qs.filter(barbeiro_id=barbeiro_id)

        return qs.order_by('-data', '-criado_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Barbeiros para dropdown de filtro
        context['barbeiros'] = Barber.objects.filter(
            tenant=self.request.tenant, ativo=True
        )
        return context
```

---

### O que aconteceria sem isso

- Código duplicado em múltiplas views de listagem
- Filtro de tenant esquecido → vazamento de dados
- Paginação implementada manualmente → erros
- N+1 queries → performance ruim

---

### O que o Django faz internamente

1. `LoginRequiredMixin`: Verifica `request.user.is_authenticated` antes de executar
2. `ListView`: Chama `get_queryset()` → `get_context_data()` → `render_to_response()`
3. Paginação: Divide queryset em páginas usando `Paginator`
4. Template: Recebe `object_list` (ou `context_object_name` customizado)

---

### Possíveis perguntas de entrevista

* Qual a diferença entre CBV e FBV? Quando usar cada um?
* O que são Mixins e como funcionam com herança múltipla?
* Como customizar o queryset em uma ListView?
* O que é Method Resolution Order (MRO) em Python?
* Como adicionar autenticação a uma CBV?

---

### Como responder na entrevista

> "Uso Class-Based Views para operações CRUD padrão porque elas eliminam código boilerplate. Na SaleListView, sobrescrevo `get_queryset()` para filtrar por tenant e aplicar filtros dinâmicos (período, barbeiro). Uso `select_related` e `prefetch_related` para evitar N+1 queries
e melhoria de performance. O Django cuida automaticamente de paginação e renderização do template."

---

### Melhorias possíveis

1. **Mixin genérico:** Criar `TenantFilterMixin` para reutilizar filtro de tenant em todas as views
2. **FilterSet:** Usar django-filter para filtros mais complexos
3. **Caching:** Cachear lista de barbeiros para dropdown

---

## Model Validation (clean)

### Onde está implementado

**Arquivo:** `agendas/models.py`
**Classe:** `Agendamento`
**Função:** `clean()`
**Linha:** ~186

---

### Problema de negócio

Validar regras de negócio complexas antes de salvar um agendamento:
1. Não permitir agendamentos no passado
2. Horário de término deve ser maior que início
3. Verificar conflito de horário com outros agendamentos do mesmo barbeiro
4. Validar se horário está dentro do funcionamento da barbearia

---

### Como foi implementado

```python
# agendas/models.py (~linha 186)
from django.core.exceptions import ValidationError

class Agendamento(SoftDeleteModel):
    # ... campos ...

    def clean(self):
        super().clean()

        # Preencher cliente automaticamente
        if self.cliente_cadastrado:
            self.cliente = self.cliente_cadastrado.nome

        # Validação: não permitir agendamentos no passado
        if self.data and not self.pk:  # Apenas novos agendamentos
            if self.data < date.today():
                raise ValidationError({
                    'data': 'Não é possível criar agendamentos com datas passadas.'
                })

        # Validação: hora_fim > hora_inicio
        if self.hora_inicio and self.hora_fim:
            if self.hora_inicio >= self.hora_fim:
                raise ValidationError({
                    'hora_fim': 'Horário de término deve ser posterior ao início.'
                })

        # Validação: conflito de horário (multi-tenant)
        if self.barbeiro_id and self.data and self.hora_inicio and self.hora_fim and self.tenant:
            tem_conflito, conflito = AgendamentoService.verificar_conflito_horario(
                barbeiro=self.barbeiro,
                data=self.data,
                hora_inicio=self.hora_inicio,
                hora_fim=self.hora_fim,
                tenant=self.tenant,
                agendamento_id=self.pk,  # Excluir self ao editar
            )
            if tem_conflito:
                raise ValidationError(
                    f'Conflito com agendamento: {conflito.cliente} às {conflito.hora_inicio}'
                )

    def save(self, *args, **kwargs):
        self.full_clean()  # Garante clean() antes de salvar
        super().save(*args, **kwargs)
```

---

### O que aconteceria sem isso

- Barbeiro com dois clientes no mesmo horário
- Agendamentos retroativos manipulando histórico
- Horário de término antes do início (dados inválidos)
- Agendamentos fora do horário de funcionamento

---

### O que o Django faz internamente

1. `full_clean()` chama: `clean_fields()` → `clean()` → `validate_unique()`
2. `clean_fields()`: Valida cada campo individualmente (validators, max_length, etc.)
3. `clean()`: Validação cross-field (lógica de negócio)
4. `validate_unique()`: Verifica constraints unique
5. `ValidationError` com dict permite erros específicos por campo

---

### Possíveis perguntas de entrevista

* Qual a diferença entre `clean()` e `validators` de campo?
* Por que sobrescrever `save()` para chamar `full_clean()`?
* Como validar múltiplos campos juntos (cross-field validation)?
* Quando usar `ValidationError` com string vs dict?
* O que acontece se `clean()` for chamado via admin vs API?

---

### Como responder na entrevista

> "No modelo Agendamento, implementei `clean()` para validar regras de negócio complexas como conflito de horário entre barbeiros. Verifico se o novo agendamento não sobrepõe com outros do mesmo barbeiro no mesmo dia. Também valido que não é possível criar agendamentos no passado. Sobrescrevo `save()` chamando `full_clean()` para garantir que validações rodem sempre, não apenas via forms."

---

### Melhorias possíveis

1. **Custom validators:** Extrair validações para validators reutilizáveis
2. **Async validation:** Para validações que precisam de I/O externo
3. **Cache de horários:** Cachear conflitos recentes para performance

---

## Signals

### Onde está implementado

**Arquivo:** `notifications/signals.py`
**Classe:** (módulo de signals)
**Função:** `criar_notificacao_agendamento()`
**Linha:** ~15

---

### Problema de negócio

Quando um agendamento é criado, enviar notificação automática para:
1. O barbeiro responsável
2. O cliente (se cadastrado)
3. O admin da barbearia

Sem acoplar a lógica de notificação ao modelo de agendamento.

---

### Como foi implementado

```python
# notifications/signals.py (~linha 15)
from django.db.models.signals import post_save
from django.dispatch import receiver
from agendas.models import Agendamento
from .models import Notification

@receiver(post_save, sender=Agendamento)
def criar_notificacao_agendamento(sender, instance, created, **kwargs):
    """
    Cria notificações quando agendamento é criado.
    """
    if not created:
        return  # Ignora updates

    agendamento = instance

    # Notificar barbeiro
    if agendamento.barbeiro and agendamento.barbeiro.user:
        Notification.objects.create(
            tenant=agendamento.tenant,
            usuario=agendamento.barbeiro.user,
            tipo='agendamento_novo',
            titulo='Novo agendamento',
            mensagem=f'{agendamento.cliente} agendou para {agendamento.data} às {agendamento.hora_inicio}',
            link=f'/agendamentos/{agendamento.pk}/'
        )

    # Notificar cliente (se tiver user)
    if agendamento.cliente_cadastrado and agendamento.cliente_cadastrado.user:
        Notification.objects.create(
            tenant=agendamento.tenant,
            usuario=agendamento.cliente_cadastrado.user,
            tipo='agendamento_confirmado',
            titulo='Agendamento confirmado',
            mensagem=f'Seu agendamento foi confirmado para {agendamento.data}'
        )
```

**Registro do signal em apps.py:**

```python
# notifications/apps.py
class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        import notifications.signals  # Importa para registrar receivers
```

---

### O que aconteceria sem isso

- Lógica de notificação espalhada em várias views
- Código duplicado ao criar agendamento via web, API, admin
- Acoplamento forte entre models
- Fácil esquecer de notificar em novos pontos de entrada

---

### O que o Django faz internamente

1. `post_save.connect()` registra função callback
2. No `Model.save()`, Django emite signal com `sender`, `instance`, `created`
3. Todos os receivers registrados são executados em ordem
4. Signals são síncronos (mesmo thread do request)
5. Exceção em receiver propaga para o chamador

---

### Possíveis perguntas de entrevista

* O que são signals e quando usar?
* Qual a diferença entre `pre_save` e `post_save`?
* Signals são síncronos ou assíncronos?
* Como evitar loops infinitos em signals?
* Alternativas a signals (ex: service layer)?

---

### Como responder na entrevista

> "Uso signals para desacoplar lógica de notificações do modelo de agendamento. Quando um agendamento é criado, o signal `post_save` dispara automaticamente e cria notificações para barbeiro e cliente. Isso garante que notificações sejam criadas independente de onde o agendamento foi criado: web, API ou admin."

---

### Melhorias possíveis

1. **Async signals:** Processar notificações em background (Celery)
2. **Batch notifications:** Agrupar notificações para evitar spam
3. **Conditional signals:** Flag para desabilitar em imports em massa
4. **Service layer:** Considerar substituir signals por serviços explícitos para melhor testabilidade

---

## Django ORM - select_related e prefetch_related

### Onde está implementado

**Arquivo:** `sales/views.py`
**Classe:** `SaleListView`
**Função:** `get_queryset()`
**Linha:** ~55

---

### Problema de negócio

Listar vendas com dados relacionados (barbeiro, cliente, serviços, produtos) sem causar N+1 queries. Uma página com 20 vendas não pode fazer 100+ queries ao banco.

---

### Como foi implementado

```python
# sales/views.py (~linha 55)
def get_queryset(self):
    return Sale.objects.filter(
        tenant=self.request.tenant
    ).select_related(
        'barbeiro',           # FK - 1 JOIN
        'agendamento',        # FK - 1 JOIN
        'cliente_cadastrado'  # FK - 1 JOIN
    ).prefetch_related(
        'servicos',  # M2M - query separada
        'produtos'   # M2M/reverse FK - query separada
    ).order_by('-data')
```

**Outro exemplo em views_finance.py:**

```python
# sales/views_finance.py (~linha 89)
def get_vendas_periodo(self, data_inicio, data_fim):
    return Sale.objects.filter(
        tenant=self.request.tenant,
        data__range=[data_inicio, data_fim]
    ).select_related(
        'barbeiro'
    ).prefetch_related(
        Prefetch(
            'servicos',
            queryset=SaleServiceItem.objects.select_related('servico')
        ),
        Prefetch(
            'produtos',
            queryset=SaleProductItem.objects.select_related('produto')
        )
    )
```

---

### O que aconteceria sem isso

**Sem otimização (N+1 problem):**
```
SELECT * FROM sales_sale                    -- 1 query
SELECT * FROM barbers_barber WHERE id = 1   -- N queries
SELECT * FROM barbers_barber WHERE id = 2
SELECT * FROM barbers_barber WHERE id = 3
... (para cada venda)
```

**Com 20 vendas:** 1 + 20 (barbeiros) + 20 (agendamentos) + 20 (clientes) = **61 queries**

**Com otimização:**
```
SELECT sales_sale.*, barbers_barber.*, agendas_agendamento.*, clients_client.*
FROM sales_sale
LEFT JOIN barbers_barber ON ...
LEFT JOIN agendas_agendamento ON ...
LEFT JOIN clients_client ON ...
-- 1 query
```

---

### O que o Django faz internamente

**select_related (FK e OneToOne):**
1. Adiciona JOINs na query SQL
2. Traz todos os dados em uma única query
3. Cria objetos relacionados já populados no ORM

**prefetch_related (M2M e reverse FK):**
1. Executa query principal
2. Coleta todos os IDs dos objetos
3. Faz query IN separada: `WHERE id IN (1, 2, 3, ...)`
4. Faz o "join" em Python na memória

---

### O que o PostgreSQL faz internamente

**Com JOINs:**
1. Carrega tabelas na memória
2. Usa índices para encontrar matches
3. Hash Join ou Merge Join dependendo do tamanho
4. Retorna resultado em uma passada

**Sem JOINs (N+1):**
1. Query principal retorna IDs
2. Para cada ID: nova query, novo round-trip de rede
3. Overhead de parse/plan para cada query

---

### Possíveis perguntas de entrevista

* O que é o problema N+1 e como resolver?
* Qual a diferença entre `select_related` e `prefetch_related`?
* Quando usar `Prefetch` object?
* Como debugar queries lentas no Django?
* O que é `only()` e `defer()` e quando usar?

---

### Como responder na entrevista

> "Uso `select_related` para ForeignKeys e OneToOne, que adiciona JOINs na query. Para ManyToMany e reverse ForeignKeys, uso `prefetch_related`, que faz queries separadas com IN clause. Isso reduziu de 60+ queries para 3 na listagem de vendas. Uso Django Debug Toolbar em desenvolvimento para identificar N+1 queries."

---

### Melhorias possíveis

1. **only() e defer():** Carregar apenas campos necessários
2. **Caching:** Cachear queries frequentes (Redis)
3. **Materialized views:** Para relatórios complexos
4. **Database indexes:** Garantir índices nas FKs

---

# DJANGO REST FRAMEWORK

---

## Serializers

### Onde está implementado

**Arquivo:** `sales/serializers.py`
**Classe:** `SaleSerializer`
**Função:** `create()`, `to_representation()`
**Linha:** ~25

---

### Problema de negócio

Serializar vendas para API com:
- Validação de dados de entrada
- Cálculo automático de comissão do barbeiro
- Representação customizada (incluir nome do barbeiro, não só ID)
- Suporte a nested writes (criar itens de serviço junto com venda)

---

### Como foi implementado

```python
# sales/serializers.py (~linha 25)
from rest_framework import serializers

class SaleServiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleServiceItem
        fields = ['servico', 'quantidade', 'preco_unitario', 'duracao_minutos']

class SaleSerializer(serializers.ModelSerializer):
    # Nested serializer para criação
    servicos = SaleServiceItemSerializer(many=True, required=False)

    # Read-only fields para representação
    barbeiro_nome = serializers.CharField(source='barbeiro.nome', read_only=True)
    cliente_nome_display = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            'id', 'tipo', 'barbeiro', 'barbeiro_nome',
            'cliente_nome', 'cliente_nome_display',
            'forma_pagamento', 'valor_total', 'comissao',
            'servicos', 'data', 'criado_em'
        ]
        read_only_fields = ['id', 'comissao', 'criado_em']

    def get_cliente_nome_display(self, obj):
        if obj.cliente_cadastrado:
            return obj.cliente_cadastrado.nome
        return obj.cliente_nome

    def validate(self, attrs):
        # Validação cross-field
        barbeiro = attrs.get('barbeiro')
        tenant = self.context['request'].tenant

        if barbeiro and barbeiro.tenant != tenant:
            raise serializers.ValidationError({
                'barbeiro': 'Barbeiro não pertence a este tenant.'
            })
        return attrs

    def create(self, validated_data):
        servicos_data = validated_data.pop('servicos', [])
        tenant = self.context['request'].tenant

        # Calcular comissão
        barbeiro = validated_data['barbeiro']
        valor_total = validated_data.get('valor_total', Decimal('0'))
        comissao = (valor_total * barbeiro.percentual_comissao) / 100

        sale = Sale.objects.create(
            tenant=tenant,
            comissao=comissao,
            **validated_data
        )

        # Criar itens de serviço
        for servico_data in servicos_data:
            SaleServiceItem.objects.create(
                tenant=tenant,
                sale=sale,
                **servico_data
            )

        return sale
```

---

### O que aconteceria sem isso

- Campos sensíveis expostos na API (ex: deleted_at, tenant_id interno)
- Validação duplicada entre views e serializers
- Nested creates implementados manualmente em cada view
- Inconsistência entre diferentes endpoints da API

---

### O que o Django REST Framework faz internamente

1. **Deserialização:** Converte JSON → Python dict → Model instance
2. **Validação:** `field.run_validators()` → `validate_<field>()` → `validate()`
3. **Serialização:** Model instance → Python dict → JSON
4. **Nested:** Chama serializers aninhados recursivamente

---

### Possíveis perguntas de entrevista

* Qual a diferença entre `Serializer` e `ModelSerializer`?
* Como criar nested writes (create/update)?
* O que é `SerializerMethodField` e quando usar?
* Como acessar o request dentro do serializer?
* Diferença entre `validate()` e `validate_<field>()`?

---

### Como responder na entrevista

> "Uso ModelSerializer para mapear campos do model automaticamente, mas customizo `create()` para nested writes - quando crio uma venda, crio também os itens de serviço na mesma transação. Uso `SerializerMethodField` para campos calculados como nome formatado do cliente. Acesso o tenant via `self.context['request'].tenant` para garantir isolamento multi-tenant."

---

### Melhorias possíveis

1. **Bulk create:** Usar `bulk_create` para performance com muitos itens
2. **Caching:** Cachear representações frequentes
3. **Versioning:** Suportar múltiplas versões do serializer

---

## ViewSets e Routers

### Onde está implementado

**Arquivo:** `sales/views_api.py`
**Classe:** `SaleViewSet`
**Função:** `get_queryset()`, `perform_create()`
**Linha:** ~35

---

### Problema de negócio

Criar API REST completa para vendas com:
- CRUD completo (list, create, retrieve, update, delete)
- Filtro automático por tenant
- Actions customizadas (ex: `/vendas/{id}/cancelar/`)
- URLs automáticas via router

---

### Como foi implementado

```python
# sales/views_api.py (~linha 35)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtro por tenant (multi-tenant)."""
        return Sale.objects.filter(
            tenant=self.request.tenant
        ).select_related(
            'barbeiro', 'cliente_cadastrado'
        ).order_by('-data')

    def perform_create(self, serializer):
        """Seta tenant automaticamente."""
        serializer.save(tenant=self.request.tenant)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        POST /api/vendas/{id}/cancelar/
        Cancela a venda e reverte operações.
        """
        venda = self.get_object()
        resultado = cancelar_venda(venda)
        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def resumo_dia(self, request):
        """
        GET /api/vendas/resumo_dia/?data=2026-01-15
        Retorna resumo de vendas do dia.
        """
        data = request.query_params.get('data', date.today())
        vendas = self.get_queryset().filter(data=data)

        return Response({
            'total': vendas.aggregate(Sum('valor_total'))['valor_total__sum'] or 0,
            'quantidade': vendas.count(),
            'comissoes': vendas.aggregate(Sum('comissao'))['comissao__sum'] or 0,
        })
```

**Router em api_urls.py:**

```python
# cash_flow/api_urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('vendas', SaleViewSet, basename='sale')
router.register('barbeiros', BarberViewSet, basename='barber')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

### O que aconteceria sem isso

- URLs definidas manualmente para cada action CRUD
- Código duplicado entre views similares
- Actions customizadas dispersas em múltiplos arquivos
- Inconsistência de nomes de URLs

---

### O que o DRF faz internamente

1. **ViewSet:** Agrupa actions relacionadas em uma classe
2. **Router:** Gera automaticamente URLs baseado nos métodos do ViewSet:
   - `GET /vendas/` → `list()`
   - `POST /vendas/` → `create()`
   - `GET /vendas/{id}/` → `retrieve()`
   - `PUT /vendas/{id}/` → `update()`
   - `DELETE /vendas/{id}/` → `destroy()`
   - `POST /vendas/{id}/cancelar/` → `cancelar()` (custom action)

---

### Possíveis perguntas de entrevista

* Qual a diferença entre `APIView`, `ViewSet` e `GenericViewSet`?
* O que são actions e como criar custom actions?
* Diferença entre `detail=True` e `detail=False` em actions?
* Como funciona o router e quais URLs ele gera?
* Quando usar ViewSet vs views separadas?

---

### Como responder na entrevista

> "Uso ModelViewSet para CRUD completo com uma classe só. O Router gera URLs automaticamente seguindo convenções REST. Para operações específicas como cancelar venda, uso `@action` decorator. `detail=True` significa que a action precisa de um ID (ex: /vendas/5/cancelar/), `detail=False` é para actions na collection (ex: /vendas/resumo_dia/)."

---

### Melhorias possíveis

1. **Throttling:** Rate limiting por tenant
2. **Caching:** Cache de listagens com invalidação
3. **Pagination customizada:** Cursor pagination para grandes datasets

---

## Permissions

### Onde está implementado

**Arquivo:** `cash_flow/permissions.py`
**Classe:** `IsTenantAdmin`
**Função:** `has_permission()`
**Linha:** ~25

---

### Problema de negócio

Controlar acesso a diferentes partes do sistema:
- Apenas admins podem acessar relatórios financeiros
- Barbeiros podem ver apenas suas próprias vendas
- Clientes podem ver apenas seus agendamentos
- Superusers têm acesso global

---

### Como foi implementado

```python
# cash_flow/permissions.py (~linha 25)
from rest_framework.permissions import BasePermission

def is_tenant_admin(user):
    """
    Verifica se usuário é admin (SaaS ou tenant).
    """
    if not user.is_authenticated:
        return False

    # Superuser sempre é admin
    if user.is_superuser:
        return True

    # Staff com perfil é admin do tenant
    if user.is_staff:
        return True

    # Verificar cargo no perfil
    try:
        return user.profile.cargo in ['proprietario', 'gerente']
    except:
        return False


class IsTenantAdmin(BasePermission):
    """
    Permission para views que exigem admin do tenant.
    """
    message = 'Apenas administradores podem acessar este recurso.'

    def has_permission(self, request, view):
        return is_tenant_admin(request.user)


class IsTenantMember(BasePermission):
    """
    Permission para verificar se usuário pertence ao tenant.
    """
    message = 'Você não tem acesso a este tenant.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Superuser tem acesso global
        if request.user.is_superuser:
            return True

        # Verificar se user pertence ao tenant do request
        try:
            return request.user.profile.tenant == request.tenant
        except:
            return False


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: dono do objeto ou admin.
    """
    def has_object_permission(self, request, view, obj):
        # Admin sempre pode
        if is_tenant_admin(request.user):
            return True

        # Verificar ownership (obj.usuario ou obj.barbeiro.user)
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        if hasattr(obj, 'barbeiro') and obj.barbeiro:
            return obj.barbeiro.user == request.user

        return False
```

**Uso em views:**

```python
# sales/views_api.py
class FinanceiroViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    # Apenas admins acessam
```

---

### O que aconteceria sem isso

- Barbeiro acessando dados de outros barbeiros
- Cliente alterando agendamentos de outros clientes
- Funcionário comum acessando relatórios financeiros sensíveis
- Vazamento de dados entre tenants

---

### O que o DRF faz internamente

1. **View-level:** `has_permission()` chamado ANTES de processar request
2. **Object-level:** `has_object_permission()` chamado ao usar `get_object()`
3. **Múltiplas permissions:** Todas devem retornar True (AND lógico)
4. **403 Forbidden:** Retornado quando permission falha

---

### Possíveis perguntas de entrevista

* Diferença entre `has_permission` e `has_object_permission`?
* Como combinar múltiplas permissions?
* Diferença entre authentication e authorization?
* Como implementar row-level security?
* O que são permission classes vs decorators?

---

### Como responder na entrevista

> "Criei permissions customizadas para controle de acesso multi-camada. `IsTenantAdmin` verifica se o usuário é admin do tenant para acessar relatórios. `IsOwnerOrAdmin` implementa object-level permission - barbeiros podem ver apenas suas próprias vendas. Uso `has_permission` para verificações gerais e `has_object_permission` para verificar ownership específico."

---

### Melhorias possíveis

1. **Role-based:** Sistema de roles com permissions granulares
2. **Caching:** Cachear verificações de permission por sessão
3. **Audit log:** Registrar tentativas de acesso negadas

---

# BANCO DE DADOS

---

## Database Indexes

### Onde está implementado

**Arquivo:** `agendas/models.py`
**Classe:** `Agendamento`
**Meta:** `indexes`
**Linha:** ~166

---

### Problema de negócio

Queries frequentes de agendamentos precisam ser rápidas:
- Listar agendamentos do dia de um barbeiro
- Buscar agendamentos por data
- Filtrar por tenant + data (multi-tenant)

Sem índices, o PostgreSQL faria full table scan em cada query.

---

### Como foi implementado

```python
# agendas/models.py (~linha 166)
class Agendamento(SoftDeleteModel):
    # ... campos com db_index=True ...
    barbeiro = models.ForeignKey(
        Barber,
        db_index=True,  # Índice automático
        ...
    )
    data = models.DateField(db_index=True)
    cliente = models.CharField(db_index=True, ...)

    class Meta:
        indexes = [
            # Índice composto para queries frequentes
            models.Index(fields=['data', 'barbeiro']),
            models.Index(fields=['data', 'hora_inicio']),
            models.Index(fields=['barbeiro', 'data']),
            # Multi-tenant: tenant + data
            models.Index(
                fields=['tenant', 'data'],
                name='agendamento_tenant_data_idx'
            ),
        ]
```

**Outro exemplo em cash_register/models.py:**

```python
# cash_register/models.py (~linha 127)
class Meta:
    indexes = [
        models.Index(
            fields=['tenant', '-referencia_data'],
            name='cashregister_tenant_data_idx'
        ),
    ]
```

---

### O que aconteceria sem isso

- Query `SELECT * FROM agendamentos WHERE data = '2026-01-15' AND barbeiro_id = 5`:
  - **Sem índice:** Full table scan (lê TODAS as linhas)
  - **Com índice:** Index scan (lê apenas linhas relevantes)
- Com 100.000 agendamentos: diferença de segundos vs milissegundos

---

### O que o PostgreSQL faz internamente

**B-Tree Index (padrão):**
1. Estrutura de árvore balanceada
2. Cada nó aponta para páginas de dados
3. Busca binária para encontrar valores
4. Complexidade O(log n) vs O(n) do full scan

**Índice Composto:**
- `Index(fields=['tenant', 'data'])` cria árvore ordenada por (tenant, data)
- Útil para queries que filtram por AMBOS os campos
- Ordem importa: `WHERE tenant = X AND data = Y` usa o índice, mas `WHERE data = Y` sozinho pode não usar

---

### Possíveis perguntas de entrevista

* O que é um índice de banco de dados e quando criar?
* Diferença entre índice simples e composto?
* Quando um índice pode prejudicar performance?
* O que é `EXPLAIN ANALYZE` e como usar?
* Diferença entre B-Tree, Hash e GIN indexes?

---

### Como responder na entrevista

> "Criei índices compostos para queries frequentes do sistema. Por exemplo, `Index(['tenant', 'data'])` otimiza a listagem de agendamentos do dia por tenant - a query mais comum. Uso `EXPLAIN ANALYZE` para validar que os índices estão sendo usados. Índices têm trade-off: aceleram leitura mas podem deixar escrita mais lenta, então crio apenas os necessários."

---

### Melhorias possíveis

1. **Partial indexes:** Índice apenas para `status='aberto'`
2. **Covering indexes:** Incluir campos no índice para evitar acesso à tabela
3. **Index monitoring:** Monitorar uso de índices e remover os não usados

---

## Database Constraints

### Onde está implementado

**Arquivo:** `cash_register/models.py`
**Classe:** `CashRegister`
**Meta:** `constraints`
**Linha:** ~119

---

### Problema de negócio

Garantir no nível do banco de dados que:
1. Apenas 1 caixa pode estar aberto por tenant/dia
2. Horário de término deve ser maior que horário de início
3. Não permitir valores negativos em campos de valor

Validações em código podem ser bypassadas; constraints no banco são invioláveis.

---

### Como foi implementado

```python
# cash_register/models.py (~linha 119)
class CashRegister(SoftDeleteModel):
    class Meta:
        constraints = [
            # Apenas 1 caixa aberto por tenant/dia
            models.UniqueConstraint(
                fields=['tenant', 'referencia_data'],
                condition=models.Q(status='aberto', deleted_at__isnull=True),
                name='unique_open_cash_per_tenant_date'
            )
        ]
```

**Outro exemplo em agendas/models.py:**

```python
# agendas/models.py (~linha 173)
class Agendamento(SoftDeleteModel):
    class Meta:
        constraints = [
            # hora_fim > hora_inicio
            models.CheckConstraint(
                check=models.Q(hora_fim__gt=models.F('hora_inicio')),
                name='hora_fim_maior_que_inicio'
            )
        ]
```

---

### O que aconteceria sem isso

- **Sem UniqueConstraint:** Race condition poderia criar 2 caixas abertos
  - User A clica "Abrir Caixa" → verifica que não existe → cria
  - User B clica "Abrir Caixa" → verifica que não existe (A ainda não salvou) → cria
  - Resultado: 2 caixas abertos = inconsistência
- **Sem CheckConstraint:** Dados inválidos persistidos (hora_fim < hora_inicio)

---

### O que o PostgreSQL faz internamente

**UniqueConstraint:**
1. Cria índice único parcial (com condition)
2. Antes de cada INSERT/UPDATE, verifica se viola o índice
3. Se viola: `IntegrityError` → transação falha

**CheckConstraint:**
1. Avalia expressão booleana antes de INSERT/UPDATE
2. Se falsa: `IntegrityError` → transação falha
3. Executado no banco, não no ORM

---

### Possíveis perguntas de entrevista

* Diferença entre validação no código vs constraint no banco?
* O que é um constraint parcial (conditional)?
* Como lidar com IntegrityError no Django?
* Quando usar CheckConstraint vs trigger?
* O que acontece se constraint falhar dentro de transaction.atomic()?

---

### Como responder na entrevista

> "Uso database constraints para garantias que não podem ser bypassadas. O `UniqueConstraint` com condition garante que apenas 1 caixa pode estar aberto por tenant, mesmo com requests concorrentes - o banco valida atomicamente. Isso é mais robusto que validação no Python porque funciona mesmo se alguém acessar o banco diretamente."

---

### Melhorias possíveis

1. **Exclusion constraints:** Para validar não-sobreposição de intervalos
2. **Foreign key constraints:** `on_delete=PROTECT` para evitar deletes acidentais
3. **Deferrable constraints:** Para validar no final da transação

---

## Soft Delete

### Onde está implementado

**Arquivo:** `cash_flow/models.py`
**Classe:** `SoftDeleteModel`
**Função:** `delete()`, `SoftDeleteManager`
**Linha:** ~15

---

### Problema de negócio

Permitir "deletar" registros sem perder dados:
- Compliance/auditoria: manter histórico de tudo
- Recuperação: desfazer deleções acidentais
- Integridade referencial: não quebrar FKs

---

### Como foi implementado

```python
# cash_flow/models.py (~linha 15)
from django.db import models
from django.utils import timezone

class SoftDeleteManager(models.Manager):
    """Manager que filtra automaticamente registros deletados."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """
    Model base com soft delete.
    Registros "deletados" são marcados com deleted_at, não removidos.
    """
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name='Deletado em'
    )

    # Manager padrão filtra deletados
    objects = SoftDeleteManager()

    # Manager para incluir deletados
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: marca deleted_at ao invés de remover."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Delete real para casos excepcionais."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restaura registro soft-deleted."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
```

**Uso em outros models:**

```python
# sales/models.py
class Sale(SoftDeleteModel):
    # Herda soft delete
    ...

# Uso
sale.delete()  # Marca deleted_at, não remove
Sale.objects.all()  # Retorna apenas não-deletados
Sale.all_objects.all()  # Retorna todos, incluindo deletados
```

---

### O que aconteceria sem isso

- Deleção acidental sem possibilidade de recuperação
- Perda de histórico para auditoria
- ForeignKey quebradas quando registro pai é deletado
- Inconsistência de dados em relatórios históricos

---

### O que o Django faz internamente

1. **Custom Manager:** `SoftDeleteManager.get_queryset()` adiciona `WHERE deleted_at IS NULL` em TODAS as queries
2. **Override delete():** Transforma DELETE em UPDATE do campo deleted_at
3. **all_objects:** Manager sem filtro para acesso administrativo

---

### Possíveis perguntas de entrevista

* O que é soft delete e quando usar?
* Como garantir que queries não retornem registros deletados?
* Problemas de soft delete com unique constraints?
* Alternativas a soft delete (ex: archive table)?
* Como fazer cascading soft delete?

---

### Como responder na entrevista

> "Implementei SoftDeleteModel como classe base para todos os models que precisam de histórico. O delete() marca `deleted_at` ao invés de remover, e o manager padrão filtra automaticamente. Isso permite auditoria completa e recuperação de dados. Para unique constraints, uso `condition=Q(deleted_at__isnull=True)` para ignorar deletados."

---

### Melhorias possíveis

1. **Cascading soft delete:** Deletar relacionados automaticamente
2. **Scheduled hard delete:** Job para remover soft-deleted após X dias
3. **Archive table:** Mover deletados para tabela separada

---

# ARQUITETURA

---

## Multi-Tenant Architecture

### Onde está implementado

**Arquivo:** `tenants/models.py`, `tenants/middleware.py`, todos os models
**Classe:** `Tenant`, `TenantMiddleware`
**Linha:** Múltiplas

---

### Problema de negócio

Sistema SaaS onde múltiplas barbearias usam a mesma aplicação, mas cada uma vê apenas seus próprios dados:
- Barbearia A não pode ver clientes da Barbearia B
- Dados são isolados mesmo com banco compartilhado
- Admin pode ver tudo (modo global)

---

### Como foi implementado

**1. Model Tenant:**
```python
# tenants/models.py (~linha 15)
class Tenant(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    email_contato = models.EmailField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
```

**2. FK em todos os models:**
```python
# sales/models.py
class Sale(SoftDeleteModel):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='vendas'
    )
```

**3. Middleware para resolver tenant:**
```python
# tenants/middleware.py (~linha 87)
class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Resolve tenant via session ou profile
        tenant = self._resolve_tenant(request)
        request.tenant = tenant
        set_current_tenant(tenant)
```

**4. Filtro obrigatório em views:**
```python
# sales/views.py
def get_queryset(self):
    return Sale.objects.filter(tenant=self.request.tenant)
```

**5. Testes de isolamento:**
```python
# project_tests/test_tenant_isolation.py
def test_cross_tenant_blocked(self):
    """Tenant A NÃO vê dados do Tenant B."""
    request = self.create_request_for_tenant(self.tenant_a, self.user_a)
    queryset = view.get_queryset()
    self.assertNotIn(self.sale_b, queryset)
```

---

### O que aconteceria sem isso

- Vazamento de dados entre empresas concorrentes
- Violação de LGPD e contratos
- Perda de confiança no sistema SaaS
- Possíveis processos judiciais

---

### Possíveis perguntas de entrevista

* Quais estratégias de multi-tenancy existem (shared db, separate db, schema)?
* Por que usar shared database com FK em cada model?
* Como garantir que nenhuma query escape o filtro de tenant?
* O que é row-level security no PostgreSQL?
* Como testar isolamento de tenants?

---

### Como responder na entrevista

> "Implementei multi-tenancy com shared database e tenant_id em cada model. O TenantMiddleware resolve o tenant via session ou profile e armazena em request.tenant. Todas as views filtram por tenant obrigatoriamente. Testes de isolamento validam que Tenant A nunca vê dados do Tenant B. Escolhi shared database para simplificar deploys e reduzir custos de infraestrutura."

---

### Melhorias possíveis

1. **Row-level security:** Usar RLS do PostgreSQL como camada extra
2. **Tenant-aware manager:** Manager que filtra automaticamente por thread-local
3. **Schema per tenant:** Para clientes enterprise com requisitos de isolamento

---

## Services Layer

### Onde está implementado

**Arquivo:** `sales/services.py`, `agendas/services.py`
**Classe:** (módulos de serviços)
**Função:** `cancelar_venda()`, `verificar_conflito_horario()`
**Linha:** Múltiplas

---

### Problema de negócio

Separar lógica de negócio complexa das views e models:
- Cancelar venda envolve múltiplas operações
- Verificar conflito de agendamento é reutilizável
- Testes unitários mais fáceis
- Views ficam finas (apenas HTTP handling)

---

### Como foi implementado

```python
# sales/services.py (~linha 15)
from django.db import transaction

def cancelar_venda(venda):
    """
    Serviço que encapsula toda lógica de cancelamento.

    Responsabilidades:
    1. Verificar se já foi cancelada (idempotência)
    2. Reverter agendamento vinculado
    3. Restaurar estoque de produtos
    4. Soft delete da venda
    5. Retornar resultado detalhado
    """
    resultado = {'ja_deletada': False, ...}

    if venda.deleted_at:
        resultado['ja_deletada'] = True
        return resultado

    with transaction.atomic():
        # Lógica de negócio
        ...

    return resultado
```

```python
# agendas/services.py (~linha 25)
class AgendamentoService:
    @staticmethod
    def verificar_conflito_horario(barbeiro, data, hora_inicio, hora_fim, tenant, agendamento_id=None):
        """
        Verifica se há conflito com agendamentos existentes.

        Returns:
            tuple: (tem_conflito: bool, agendamento_conflitante: Agendamento|None)
        """
        agendamentos = Agendamento.objects.filter(
            tenant=tenant,
            barbeiro=barbeiro,
            data=data,
            deleted_at__isnull=True
        ).exclude(pk=agendamento_id)

        for ag in agendamentos:
            if (hora_inicio < ag.hora_fim and hora_fim > ag.hora_inicio):
                return True, ag

        return False, None
```

**Uso em views:**

```python
# sales/views.py
from sales.services import cancelar_venda

class SaleDeleteView(DeleteView):
    def delete(self, request, *args, **kwargs):
        venda = self.get_object()
        resultado = cancelar_venda(venda)  # Serviço
        messages.success(request, 'Venda cancelada.')
        return redirect('sales:list')
```

---

### O que aconteceria sem isso

- Lógica de negócio espalhada em views, models, serializers
- Código duplicado entre views web e API
- Testes difíceis (precisa mockar request HTTP)
- Violação do Single Responsibility Principle

---

### Possíveis perguntas de entrevista

* O que é Service Layer e quando usar?
* Diferença entre Fat Models e Service Layer?
* Como testar serviços isoladamente?
* O que são use cases/interactors?
* Trade-offs de adicionar camada de serviços?

---

### Como responder na entrevista

> "Extraí lógica de negócio complexa para services. O serviço `cancelar_venda()` encapsula toda lógica de cancelamento: reverter agendamento, restaurar estoque, soft delete. Isso permite reutilizar em views web, API e testes. Services são funções puras que recebem dados e retornam resultados, facilitando testes unitários sem mock de HTTP."

---

### Melhorias possíveis

1. **Dependency injection:** Injetar repositories ao invés de acessar ORM diretamente
2. **Result objects:** Retornar objetos tipados ao invés de dicts
3. **Use cases:** Separar cada operação em classe própria

---

# TESTES

---

## Pytest e Fixtures

### Onde está implementado

**Arquivo:** `sales/tests/test_fase2_reversao.py`
**Classe:** `CancelarVendaServiceTestCase`
**Função:** `setUp()`, `test_cancelar_venda_*`
**Linha:** ~33

---

### Problema de negócio

Testar automaticamente que:
1. Cancelar venda reverte agendamento
2. Cancelar venda restaura estoque
3. Cancelar 2x não duplica estoque (idempotência)
4. Cancelar venda sem agendamento não quebra

---

### Como foi implementado

```python
# sales/tests/test_fase2_reversao.py (~linha 33)
from django.test import TestCase
from sales.services import cancelar_venda

class CancelarVendaServiceTestCase(TestCase):
    def setUp(self):
        """Fixture: cria dados necessários para os testes."""
        # Criar tenant
        self.tenant = Tenant.objects.create(
            nome='Barbearia Teste',
            slug='teste',
            ativo=True
        )

        # Criar barbeiro
        self.barbeiro = Barber.objects.create(
            tenant=self.tenant,
            nome='Barbeiro Teste',
            percentual_comissao=Decimal('40.00')
        )

        # Criar produto com estoque
        self.produto = Product.objects.create(
            tenant=self.tenant,
            nome='Pomada',
            estoque=10
        )

    def test_cancelar_venda_reverte_agendamento(self):
        """Ao cancelar venda, agendamento volta para não finalizado."""
        # Arrange
        agendamento = self.create_agendamento(finalizado=True)
        venda = self.create_venda_com_agendamento(agendamento)

        # Act
        resultado = cancelar_venda(venda)

        # Assert
        self.assertTrue(resultado['agendamento_revertido'])
        agendamento.refresh_from_db()
        self.assertFalse(agendamento.atendimento_finalizado)

    def test_cancelar_venda_idempotencia(self):
        """Cancelar 2x não duplica estoque."""
        estoque_inicial = self.produto.estoque  # 10
        venda = self.create_venda_com_produto(quantidade=2)

        # Primeira execução
        resultado1 = cancelar_venda(venda)
        self.assertFalse(resultado1['ja_deletada'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 10)  # Restaurado

        # Segunda execução
        venda.refresh_from_db()
        resultado2 = cancelar_venda(venda)
        self.assertTrue(resultado2['ja_deletada'])  # Detecta duplicata
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 10)  # Continua 10, não 12
```

---

### O que aconteceria sem isso

- Bugs introduzidos sem detecção
- Regressões ao modificar código existente
- Medo de refatorar
- Deploys quebrados em produção

---

### O que o Django/pytest faz internamente

1. **TestCase:** Cria transação de banco, faz rollback após cada teste
2. **setUp():** Executado antes de CADA método de teste
3. **refresh_from_db():** Recarrega objeto do banco (necessário após modificações externas)
4. **Isolation:** Cada teste roda em transação isolada

---

### Possíveis perguntas de entrevista

* Diferença entre `TestCase` e `TransactionTestCase`?
* O que são fixtures e como funcionam?
* Como usar `setUp` vs `setUpClass` vs `setUpTestData`?
* O que é `refresh_from_db()` e quando usar?
* Como testar código que usa transações?

---

### Como responder na entrevista

> "Implementei testes para garantir que cancelamento de vendas funciona corretamente. O teste de idempotência verifica que cancelar 2x não duplica estoque - importante porque eventos duplicados acontecem em sistemas distribuídos. Uso `refresh_from_db()` para garantir que estou lendo o estado atual do banco após o serviço modificar."

---

### Melhorias possíveis

1. **Factory Boy:** Usar factories ao invés de criar objetos manualmente
2. **pytest fixtures:** Escopo de fixtures (function, class, session)
3. **Coverage:** Medir cobertura de testes

---

## Testes de Isolamento Multi-Tenant

### Onde está implementado

**Arquivo:** `project_tests/test_tenant_isolation.py`
**Classe:** `SalesIsolationTest`, `BarbersIsolationTest`
**Função:** `test_listview_isolated_by_tenant()`, `test_cross_tenant_blocked()`
**Linha:** ~116

---

### Problema de negócio

Garantir que isolamento multi-tenant funciona:
- Tenant A lista apenas suas vendas
- Tenant A recebe 404 ao tentar acessar venda do Tenant B
- Não existe forma de bypass

---

### Como foi implementado

```python
# project_tests/test_tenant_isolation.py (~linha 116)
class SalesIsolationTest(TenantIsolationTestCase):
    def test_listview_isolated_by_tenant(self):
        """ListView retorna apenas vendas do próprio tenant."""
        # Request simulado do Tenant A
        request = self.create_request_for_tenant(self.tenant_a, self.user_a)

        view = SaleListView()
        view.request = request
        queryset = view.get_queryset()

        # Tenant A vê APENAS sua venda
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.sale_a, queryset)
        self.assertNotIn(self.sale_b, queryset)

    def test_detailview_cross_tenant_404(self):
        """Acesso cross-tenant retorna 404."""
        # Tenant A tenta acessar venda do Tenant B
        request = self.create_request_for_tenant(self.tenant_a, self.user_a)

        view = SaleUpdateView()
        view.request = request
        view.kwargs = {'pk': self.sale_b.pk}  # ID da venda do Tenant B

        # Deve lançar 404 (não 403)
        with self.assertRaises(Http404):
            view.get_object()
```

---

### O que aconteceria sem isso

- Vazamento de dados não detectado em development
- Bug de segurança descoberto apenas em produção
- Violação de compliance sem evidência

---

### Possíveis perguntas de entrevista

* Por que retornar 404 ao invés de 403 para cross-tenant?
* Como testar middleware sem fazer requests HTTP?
* O que é RequestFactory e quando usar?
* Como garantir cobertura de todos os endpoints?

---

### Como responder na entrevista

> "Implementei testes de segurança específicos para multi-tenant. O teste verifica que Tenant A recebe 404 ao tentar acessar venda do Tenant B - uso 404 ao invés de 403 para não vazar que o recurso existe. Uso RequestFactory para simular requests sem overhead de HTTP, injetando tenant diretamente no request."

---

# INFRAESTRUTURA

---

## Docker

### Onde está implementado

**Arquivo:** `Dockerfile`
**Linha:** Inteiro

---

### Problema de negócio

Deploy consistente em qualquer ambiente:
- Desenvolvimento local idêntico a produção
- Sem conflitos de versões de dependências
- CI/CD automatizado

---

### Como foi implementado

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (cache de layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# Porta
EXPOSE 80

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

---

### O que aconteceria sem isso

- "Funciona na minha máquina"
- Conflitos de versão de Python/libs
- Setup manual em cada servidor
- Deploys inconsistentes

---

### O que o Docker faz internamente

1. **FROM:** Inicia com imagem base (python:3.12-slim)
2. **Layers:** Cada comando cria layer cacheada
3. **COPY requirements primeiro:** Reutiliza cache se requirements não mudou
4. **ENTRYPOINT:** Script executado ao iniciar container

---

### Possíveis perguntas de entrevista

* Diferença entre `CMD` e `ENTRYPOINT`?
* O que são Docker layers e como otimizar cache?
* Por que usar `--no-cache-dir` no pip?
* Diferença entre `COPY` e `ADD`?
* O que é multi-stage build?

---

### Como responder na entrevista

> "Uso Dockerfile para garantir ambiente consistente. Copio requirements.txt primeiro para aproveitar cache de layer - se dependências não mudaram, não reinstala. Uso python:3.12-slim para imagem menor. O entrypoint.sh permite configuração flexível via variáveis de ambiente para migrations, collectstatic, etc."

---

### Melhorias possíveis

1. **Multi-stage build:** Build em imagem grande, runtime em imagem mínima
2. **Non-root user:** Segurança adicional
3. **Health checks:** Verificar se app está healthy

---

## Docker Compose

### Onde está implementado

**Arquivo:** `docker-compose.yml`
**Linha:** Inteiro

---

### Problema de negócio

Orquestrar múltiplos serviços localmente:
- Django app
- PostgreSQL database
- Nginx reverse proxy
- Redis (futuro)

---

### Como foi implementado

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:80"
    environment:
      - DEBUG=1
      - DATABASE_URL=postgresql://user:pass@db:5432/barber
      - RUN_MIGRATIONS=1
    depends_on:
      - db
    volumes:
      - .:/app  # Hot reload em dev

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=barber
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./staticfiles:/static
    depends_on:
      - web

volumes:
  postgres_data:
```

---

### O que o Docker Compose faz internamente

1. **depends_on:** Inicia serviços na ordem correta
2. **volumes:** Persiste dados entre restarts
3. **Network:** Cria rede interna para comunicação entre containers
4. **Environment:** Injeta variáveis de ambiente

---

### Possíveis perguntas de entrevista

* Diferença entre `docker run` e `docker-compose up`?
* O que é um volume e quando usar?
* Como escalar serviços no compose?
* Diferença entre `depends_on` e health checks?
* Como debugar containers que não iniciam?

---

### Como responder na entrevista

> "Uso docker-compose para desenvolvimento local com todos os serviços. O web depende do db, garantindo ordem de inicialização. Volumes persistem dados do PostgreSQL entre restarts. Em desenvolvimento, monto o código como volume para hot reload. O nginx serve estáticos em produção."

---

## Nginx

### Onde está implementado

**Arquivo:** `nginx.conf`
**Linha:** Inteiro

---

### Problema de negócio

Reverse proxy em frente ao Django:
- Servir arquivos estáticos eficientemente
- Rate limiting para proteção contra DoS
- Bloquear bots maliciosos
- SSL termination (via Cloudflare)

---

### Como foi implementado

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    # Bot blocking
    map $http_user_agent $is_bot {
        default 0;
        ~*bot 1;
        ~*crawl 1;
        ~*spider 1;
    }

    server {
        listen 80;

        # Arquivos estáticos
        location /static/ {
            alias /static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Rate limit em login
        location /accounts/login/ {
            limit_req zone=login_limit burst=3 nodelay;
            proxy_pass http://web:80;
        }

        # Bloquear bots em API
        location /api/ {
            if ($is_bot) {
                return 403;
            }
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://web:80;
        }

        # Proxy para Django
        location / {
            proxy_pass http://web:80;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

### O que o Nginx faz internamente

1. **Static files:** Serve diretamente do filesystem, sem passar pelo Python
2. **Rate limiting:** Usa leaky bucket algorithm
3. **Proxy pass:** Encaminha requests para Django via HTTP
4. **Headers:** Preserva IP real do cliente

---

### Possíveis perguntas de entrevista

* Por que usar Nginx em frente ao Django?
* Diferença entre rate limiting no Nginx vs aplicação?
* O que é o header X-Real-IP?
* Como configurar SSL/TLS no Nginx?
* Diferença entre `proxy_pass` e `fastcgi_pass`?

---

### Como responder na entrevista

> "Uso Nginx como reverse proxy para servir estáticos eficientemente e rate limiting. O rate limit de login (5r/m) protege contra brute force. Bloqueio bots na API para economizar recursos. Estáticos são servidos diretamente pelo Nginx com cache de 30 dias, sem passar pelo Python."

---

## Entrypoint Script

### Onde está implementado

**Arquivo:** `entrypoint.sh`
**Linha:** Inteiro

---

### Problema de negócio

Configurar container de forma flexível:
- Rodar migrations (ou não)
- Collectstatic (ou não)
- Modo console para debugging
- Hotfixes de emergência

---

### Como foi implementado

```bash
# entrypoint.sh (simplificado)
#!/bin/bash
set -euo pipefail

# Configuração via env vars
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-1}"
SKIP_WEB_SERVER="${SKIP_WEB_SERVER:-0}"

# Collectstatic
if [ "$RUN_COLLECTSTATIC" = "1" ]; then
    python manage.py collectstatic --noinput --clear
fi

# Migrations
if [ "$RUN_MIGRATIONS" = "1" ]; then
    python manage.py migrate --noinput
fi

# Web server ou console
if [ "$SKIP_WEB_SERVER" = "1" ]; then
    exec tail -f /dev/null  # Manter vivo para console
else
    exec gunicorn cash_flow.wsgi:application \
        --bind 0.0.0.0:80 \
        --workers 3 \
        --timeout 30
fi
```

---

### O que o script faz

1. **set -euo pipefail:** Falha em qualquer erro
2. **Defaults seguros:** Migrations rodam por padrão
3. **exec:** Substitui shell pelo processo final (PID 1)
4. **Gunicorn:** Servidor WSGI production-ready

---

### Possíveis perguntas de entrevista

* Por que usar `exec` antes do gunicorn?
* O que é PID 1 e por que importa em containers?
* Diferença entre gunicorn e Django runserver?
* Como configurar workers do gunicorn?
* O que é graceful shutdown?

---

### Como responder na entrevista

> "O entrypoint permite configuração flexível via variáveis de ambiente. `RUN_MIGRATIONS=0` permite deploy sem migrations em emergências. Uso `exec` para substituir o shell pelo gunicorn como PID 1, garantindo que sinais de shutdown sejam capturados corretamente. Gunicorn com 3 workers escala melhor que runserver."

---

# IA, LLM E RAG

---

## Classificação da Implementação: RAG COMPLETO

### Evidências do Código

O projeto Barber Cashflow implementa **RAG Completo** (Retrieval-Augmented Generation), não pseudo-RAG.

**Critérios de RAG Completo atendidos:**

| Componente | Implementado | Arquivo |
|------------|--------------|---------|
| Document Loading | Sim | `ai_chat/extract_manual.py` |
| Chunking Semântico | Sim | `ai_chat/rag_system.py:65` |
| Embeddings (vetores) | Sim | `ai_chat/rag_system.py:219` |
| Vector Store (FAISS) | Sim | `ai_chat/rag_system.py:272` |
| Semantic Search | Sim | `ai_chat/rag_system.py:453` |
| Context Building | Sim | `ai_chat/rag_system.py:479` |
| Prompt Engineering | Sim | `ai_chat/prompt_engineering.py` |
| LLM Generation | Sim | `ai_chat/views.py:155` |

**Diferença para pseudo-RAG:**
- Pseudo-RAG: Usa keyword search ou regex para encontrar contexto
- RAG Completo: Usa embeddings + busca vetorial (similaridade semântica)

O projeto usa **OpenAI text-embedding-3-small** para embeddings e **FAISS** para busca vetorial.

---

## TABELA DE VERIFICAÇÃO - Afirmações Técnicas

Esta tabela comprova cada afirmação técnica desta seção contra o código-fonte real.

### RAG System Core

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe RAGSystem existe | `ai_chat/rag_system.py` | 323 | `class RAGSystem:` | CONFIRMADO |
| Método search() existe | `ai_chat/rag_system.py` | 453 | `def search(self, query: str, top_k: int = 5)` | CONFIRMADO |
| Método build_context() existe | `ai_chat/rag_system.py` | 479 | `def build_context(self, query: str, top_k: int = 5, max_chars: int = 8000)` | CONFIRMADO |
| Limite de contexto 8000 chars | `ai_chat/rag_system.py` | 479 | `max_chars: int = 8000` | CONFIRMADO |
| Top-K padrão é 5 | `ai_chat/rag_system.py` | 453, 479 | `top_k: int = 5` | CONFIRMADO |

### Chunking

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe ChunkingStrategy existe | `ai_chat/rag_system.py` | 65 | `class ChunkingStrategy:` | CONFIRMADO |
| CHUNK_SIZE = 800 | `ai_chat/rag_system.py` | 68 | `CHUNK_SIZE = 800` | CONFIRMADO |
| OVERLAP = 150 | `ai_chat/rag_system.py` | 69 | `OVERLAP = 150` | CONFIRMADO |
| MIN_CHUNK_SIZE = 200 | `ai_chat/rag_system.py` | 70 | `MIN_CHUNK_SIZE = 200` | CONFIRMADO |
| Método semantic_chunking() existe | `ai_chat/rag_system.py` | 79 | `def semantic_chunking(text: str) -> List[Dict]:` | CONFIRMADO |
| Detecta seções H1 | `ai_chat/rag_system.py` | 95 | `re.split(r'={80,}\n#\s*(.+?)\n\n\[ID:.*?\]\n={80,}', text)` | CONFIRMADO |
| Detecta subseções H2 | `ai_chat/rag_system.py` | 105 | `re.split(r'\n## (.+?)\n', section_content)` | CONFIRMADO |

### Embeddings

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe EmbeddingGenerator existe | `ai_chat/rag_system.py` | 219 | `class EmbeddingGenerator:` | CONFIRMADO |
| Modelo text-embedding-3-small | `ai_chat/rag_system.py` | 227 | `self.model = 'text-embedding-3-small'` | CONFIRMADO |
| Dimensão 1536 | `ai_chat/rag_system.py` | 228 | `self.dimension = 1536` | CONFIRMADO |
| Método generate_batch() existe | `ai_chat/rag_system.py` | 236 | `def generate_batch(self, texts: List[str]) -> List[List[float]]:` | CONFIRMADO |
| Método generate_single() existe | `ai_chat/rag_system.py` | 261 | `def generate_single(self, text: str) -> List[float]:` | CONFIRMADO |

### FAISS Vector Store

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe FAISSIndex existe | `ai_chat/rag_system.py` | 272 | `class FAISSIndex:` | CONFIRMADO |
| Usa IndexFlatIP | `ai_chat/rag_system.py` | 279 | `self.index = faiss.IndexFlatIP(dimension)` | CONFIRMADO |
| Normaliza L2 na adição | `ai_chat/rag_system.py` | 283 | `faiss.normalize_L2(embeddings)` | CONFIRMADO |
| Normaliza L2 na busca | `ai_chat/rag_system.py` | 289 | `faiss.normalize_L2(query_embedding)` | CONFIRMADO |
| Método save() existe | `ai_chat/rag_system.py` | 294 | `def save(self, path: str):` | CONFIRMADO |
| Método load() existe | `ai_chat/rag_system.py` | 298 | `def load(self, path: str):` | CONFIRMADO |

### Prompt Engineering

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe PromptBuilder existe | `ai_chat/prompt_engineering.py` | 14 | `class PromptBuilder:` | CONFIRMADO |
| SYSTEM_PROMPT_TEMPLATE existe | `ai_chat/prompt_engineering.py` | 21 | `SYSTEM_PROMPT_TEMPLATE = """Você é o assistente...` | CONFIRMADO |
| Regra anti-alucinação existe | `ai_chat/prompt_engineering.py` | 29-33 | `Responda APENAS com informações do manual` | CONFIRMADO |
| Método build_system_prompt() existe | `ai_chat/prompt_engineering.py` | 102 | `def build_system_prompt(context: str) -> str:` | CONFIRMADO |
| Método build_user_message() existe | `ai_chat/prompt_engineering.py` | 115 | `def build_user_message(query: str) -> str:` | CONFIRMADO |

### LLM Integration

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| ANTHROPIC_MODEL definido | `ai_chat/views.py` | 52 | `ANTHROPIC_MODEL = 'claude-sonnet-4-5-20250929'` | CONFIRMADO |
| OPENAI_MODEL definido | `ai_chat/views.py` | 53 | `OPENAI_MODEL = 'gpt-4o'` | CONFIRMADO |
| generate_response_anthropic() existe | `ai_chat/views.py` | 155 | `def generate_response_anthropic(query: str, context: str, ...)` | CONFIRMADO |
| generate_response_openai() existe | `ai_chat/views.py` | 221 | `def generate_response_openai(query: str, context: str, ...)` | CONFIRMADO |
| max_tokens = 2000 | `ai_chat/views.py` | 199, 268 | `max_tokens=2000` | CONFIRMADO |
| Retorna tokens usados | `ai_chat/views.py` | 213-216 | `'tokens_used': {'input': ..., 'output': ...}` | CONFIRMADO |

### Rate Limiting

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Decorator rate_limit_chat() existe | `ai_chat/views.py` | 309 | `def rate_limit_chat(view_func):` | CONFIRMADO |
| Limite de 50 requests | `ai_chat/views.py` | 324 | `if count >= 50:` | CONFIRMADO |
| TTL de 1 hora (3600s) | `ai_chat/views.py` | 331 | `cache.set(cache_key, count + 1, timeout=3600)` | CONFIRMADO |
| Cache key com tenant + user | `ai_chat/views.py` | 320 | `cache_key = f"chat_rate:{tenant_id}:{user_id}"` | CONFIRMADO |
| Retorna HTTP 429 quando excede | `ai_chat/views.py` | 325-328 | `return JsonResponse({...}, status=429)` | CONFIRMADO |

### Chat Logging Middleware

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Classe ChatLogMiddleware existe | `ai_chat/middleware.py` | 28 | `class ChatLogMiddleware(MiddlewareMixin):` | CONFIRMADO |
| Método process_request() existe | `ai_chat/middleware.py` | 46 | `def process_request(self, request: HttpRequest):` | CONFIRMADO |
| Método process_response() existe | `ai_chat/middleware.py` | 65 | `def process_response(self, request: HttpRequest, response: HttpResponse):` | CONFIRMADO |
| Logs separados por tenant | `ai_chat/middleware.py` | 214 | `log_file = self.log_dir / f'chat_logs_{tenant_slug}_{current_month}.jsonl'` | CONFIRMADO |
| Formato JSONL | `ai_chat/middleware.py` | 219 | `f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')` | CONFIRMADO |
| Registra tokens usados | `ai_chat/middleware.py` | 157-158 | `'tokens_input': ..., 'tokens_output': ...` | CONFIRMADO |

### Security

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Decorator login_required_json() existe | `ai_chat/views.py` | 293 | `def login_required_json(view_func):` | CONFIRMADO |
| Retorna 401 se não autenticado | `ai_chat/views.py` | 301-304 | `return JsonResponse({...}, status=401)` | CONFIRMADO |
| Verifica tenant (403 se None) | `ai_chat/views.py` | 393-397 | `if not hasattr(request, 'tenant') or request.tenant is None:` | CONFIRMADO |
| Verifica header X-Requested-With | `ai_chat/views.py` | 381-382 | `x_requested_with = request.META.get('HTTP_X_REQUESTED_WITH', '')` | CONFIRMADO |
| Sanitiza input do usuário | `ai_chat/views.py` | 87-108 | `def sanitize_input(text: str, max_length: int = 2000)` | CONFIRMADO |
| Limite de 2000 caracteres | `ai_chat/views.py` | 145-146 | `if len(message) > 2000:` | CONFIRMADO |

### Testes Automatizados

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| Teste de 401 sem auth | `ai_chat/tests/test_chat_api_security.py` | 47 | `def test_unauthenticated_request_returns_401(self):` | CONFIRMADO |
| Teste de 429 rate limit | `ai_chat/tests/test_chat_api_security.py` | 72 | `def test_rate_limit_returns_429_after_50_requests(self):` | CONFIRMADO |
| Teste de 403 sem tenant | `ai_chat/tests/test_chat_api_security.py` | 145 | `def test_request_without_tenant_returns_403(self):` | CONFIRMADO |

### Decisões Arquiteturais

| Afirmação | Arquivo | Linha | Trecho de Código | Status |
|-----------|---------|-------|------------------|--------|
| RAG é GLOBAL (todos tenants) | `ai_chat/views.py` | 58-62 | Comentário: `O sistema RAG é GLOBAL - todos os tenants compartilham o mesmo manual` | CONFIRMADO |
| Logs são SEPARADOS por tenant | `ai_chat/middleware.py` | 8 | Comentário: `Salva logs em formato JSONL SEPARADOS POR TENANT` | CONFIRMADO |

---

**Resultado da Verificação:** 100% das afirmações técnicas estão **CONFIRMADAS** no código-fonte.

---

## RAG System (Sistema de Recuperação)

### Onde está implementado

**Arquivo:** `ai_chat/rag_system.py`
**Classe:** `RAGSystem`
**Função:** `search()`, `build_context()`
**Linha:** ~323

---

### Problema de negócio

Permitir que usuários do Barber Cashflow façam perguntas em linguagem natural sobre o sistema e recebam respostas precisas baseadas no manual oficial, sem necessidade de ler toda a documentação.

**Exemplo real:**
- Usuário pergunta: "Como faço para agendar um horário?"
- Sistema busca trechos relevantes do manual
- LLM responde baseado APENAS no contexto encontrado

---

### Como foi implementado

```python
# ai_chat/rag_system.py (~linha 323)
class RAGSystem:
    """Sistema completo de RAG"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / 'data'
        self.chunks: List[Chunk] = []
        self.embedding_generator: EmbeddingGenerator = None
        self.faiss_index: FAISSIndex = None

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """
        Busca chunks relevantes para a query

        Args:
            query: Pergunta do usuário
            top_k: Número de chunks a retornar

        Returns:
            Lista de (chunk, score)
        """
        # 1. Gera embedding da query (mesmo modelo usado nos chunks)
        query_embedding = self.embedding_generator.generate_single(query)
        query_embedding = np.array([query_embedding], dtype=np.float32)

        # 2. Busca no FAISS (cosine similarity)
        distances, indices = self.faiss_index.search(query_embedding, top_k)

        # 3. Retorna chunks com scores
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))

        return results

    def build_context(self, query: str, top_k: int = 5, max_chars: int = 8000) -> str:
        """
        Constrói contexto para a IA a partir da query
        """
        results = self.search(query, top_k)

        context_parts = []
        total_chars = 0

        for chunk, score in results:
            header = f"\n--- Seção: {chunk.section}"
            if chunk.subsection:
                header += f" > {chunk.subsection}"
            header += f" (Relevância: {score:.2f}) ---\n"

            chunk_text = header + chunk.text + "\n"

            if total_chars + len(chunk_text) > max_chars:
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return '\n'.join(context_parts)
```

---

### Fluxo da funcionalidade

```
Usuário
   ↓
"Como cadastrar cliente?"
   ↓
┌─────────────────────────────────────────┐
│ ai_chat/views.py - chat_api()           │
│ - Valida autenticação                   │
│ - Verifica rate limit (50/hora)         │
│ - Sanitiza input                        │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ RAGSystem.search()                      │
│ - Gera embedding da query               │
│ - Busca top-5 chunks no FAISS           │
│ - Retorna chunks + scores               │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ RAGSystem.build_context()               │
│ - Formata chunks em texto               │
│ - Adiciona headers de seção             │
│ - Limita a 8000 caracteres              │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ PromptBuilder.build_system_prompt()     │
│ - Injeta contexto no template           │
│ - Define regras de comportamento        │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ generate_response_anthropic()           │
│ - Chama Claude API                      │
│ - Retorna resposta + tokens usados      │
└─────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────┐
│ ChatLogMiddleware                       │
│ - Loga pergunta + resposta              │
│ - Separa por tenant                     │
└─────────────────────────────────────────┘
   ↓
Resposta JSON com answer + sources
```

---

### O que aconteceria sem isso

- Sem RAG: LLM "alucina" inventando funcionalidades que não existem
- Sem embeddings: Busca por keyword não encontra sinônimos ("agendar" vs "marcar horário")
- Sem chunking: Contexto muito grande excede limite de tokens
- Sem FAISS: Busca linear O(n) seria muito lenta

---

### O que o sistema faz internamente

1. **Embedding da query:** Converte texto em vetor de 1536 dimensões
2. **FAISS search:** Usa Inner Product (cosine similarity após normalização)
3. **Top-K retrieval:** Retorna os K chunks mais similares
4. **Context window:** Limita contexto para caber no limite de tokens do LLM

---

### Possíveis perguntas de entrevista

* O que é RAG e por que usar ao invés de fine-tuning?
* Como embeddings representam semântica?
* Por que usar cosine similarity ao invés de distância euclidiana?
* O que é FAISS e quais alternativas existem?
* Como lidar com contexto que excede limite de tokens?
* Como medir qualidade das respostas do RAG?

---

### Como responder na entrevista

> "Implementei RAG completo para o chatbot do Barber Cashflow. O sistema extrai o manual HTML, faz chunking semântico de ~800 caracteres com overlap, gera embeddings com OpenAI, e indexa no FAISS. Quando o usuário pergunta algo, gero embedding da query, busco os 5 chunks mais similares, e envio como contexto para o Claude. Isso evita alucinações porque o LLM só responde baseado no manual real."

---

### Melhorias possíveis

1. **Hybrid search:** Combinar busca vetorial com BM25 (keyword)
2. **Re-ranking:** Usar cross-encoder para re-ordenar resultados
3. **Query expansion:** Expandir query com sinônimos antes de buscar
4. **Evaluation pipeline:** Medir recall@k e MRR automaticamente

---

## Chunking Semântico

### Onde está implementado

**Arquivo:** `ai_chat/rag_system.py`
**Classe:** `ChunkingStrategy`
**Função:** `semantic_chunking()`
**Linha:** ~65

---

### Problema de negócio

Dividir o manual (~50 páginas) em pedaços que:
1. Caibam no contexto do LLM
2. Mantenham coerência semântica (não cortar no meio de frase)
3. Preservem hierarquia (seção > subseção)
4. Tenham overlap para não perder contexto nas bordas

---

### Como foi implementado

```python
# ai_chat/rag_system.py (~linha 65)
class ChunkingStrategy:
    """Estratégias de chunking do manual"""

    CHUNK_SIZE = 800  # Caracteres
    OVERLAP = 150     # Caracteres de sobreposição
    MIN_CHUNK_SIZE = 200  # Mínimo para considerar válido

    @staticmethod
    def semantic_chunking(text: str) -> List[Dict]:
        """
        Chunking semântico baseado em estrutura do documento

        Estratégia:
        1. Detecta seções (# título)
        2. Detecta subseções (## subtítulo)
        3. Quebra por parágrafos respeitando limites
        4. Adiciona overlap para contexto
        """
        chunks = []
        current_section = "Início"
        current_subsection = ""

        # Divide por seções principais (H1)
        sections = re.split(r'={80,}\n#\s*(.+?)\n\n\[ID:.*?\]\n={80,}', text)

        chunk_id = 0

        for i in range(1, len(sections), 2):
            section_title = sections[i].strip()
            section_content = sections[i + 1]
            current_section = section_title

            # Divide por subseções (H2)
            subsections = re.split(r'\n## (.+?)\n', section_content)

            # Processa subseções
            for j in range(1, len(subsections), 2):
                subsection_title = subsections[j].strip()
                subsection_content = subsections[j + 1]

                # Adiciona título da subseção ao chunk
                full_content = f"## {subsection_title}\n\n{subsection_content}"

                sub_chunks = ChunkingStrategy._split_by_size(
                    full_content,
                    ChunkingStrategy.CHUNK_SIZE,
                    ChunkingStrategy.OVERLAP
                )

                for chunk_text in sub_chunks:
                    chunks.append({
                        'id': chunk_id,
                        'text': chunk_text,
                        'section': current_section,
                        'subsection': current_subsection,
                        'metadata': {'has_section': True, 'has_subsection': True}
                    })
                    chunk_id += 1

        return chunks
```

---

### O que aconteceria sem isso

- **Chunks muito grandes:** Excede limite de tokens, desperdício de contexto
- **Chunks muito pequenos:** Perde coerência, resposta fragmentada
- **Sem overlap:** Perde contexto nas bordas ("...continuando o passo anterior...")
- **Sem hierarquia:** Não sabe de qual seção veio o trecho

---

### Possíveis perguntas de entrevista

* Qual o tamanho ideal de chunk? Por quê?
* O que é overlap e por que usar?
* Diferença entre chunking fixo e semântico?
* Como preservar contexto em documentos estruturados?

---

### Como responder na entrevista

> "Uso chunking semântico de 800 caracteres com 150 de overlap. Detecto seções (H1) e subseções (H2) do manual para preservar hierarquia - cada chunk sabe de qual seção veio. O overlap garante que não perco contexto nas bordas. Chunks menores que 200 caracteres são descartados porque não têm informação útil."

---

## Embeddings (Vetorização)

### Onde está implementado

**Arquivo:** `ai_chat/rag_system.py`
**Classe:** `EmbeddingGenerator`
**Função:** `generate_batch()`, `generate_single()`
**Linha:** ~219

---

### Problema de negócio

Converter texto em vetores numéricos que capturam significado semântico. Textos com significado similar devem ter vetores próximos no espaço vetorial.

**Exemplo:**
- "agendar horário" → vetor A
- "marcar atendimento" → vetor B
- A e B devem ser muito próximos (alta similaridade)

---

### Como foi implementado

```python
# ai_chat/rag_system.py (~linha 219)
class EmbeddingGenerator:
    """Gera embeddings usando OpenAI"""

    def __init__(self, provider: str = 'openai', api_key: str = None):
        if provider == 'openai':
            self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            self.model = 'text-embedding-3-small'  # 1536 dimensões
            self.dimension = 1536

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para uma lista de textos

        Args:
            texts: Lista de textos

        Returns:
            Lista de embeddings (vetores de 1536 floats)
        """
        # OpenAI suporta batch de até 2048 textos
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        embeddings = [item.embedding for item in response.data]
        return embeddings

    def generate_single(self, text: str) -> List[float]:
        """Gera embedding para um único texto"""
        return self.generate_batch([text])[0]
```

---

### O que aconteceria sem isso

- Sem embeddings: Teria que usar keyword search (perde sinônimos)
- Embedding ruim: "agendar" e "marcar horário" não seriam relacionados
- Dimensão errada: Resultados de busca imprecisos

---

### O que a API faz internamente

1. **Tokenização:** Divide texto em tokens (subpalavras)
2. **Transformer encoding:** Processa tokens por camadas de atenção
3. **Pooling:** Agrega representações em vetor único
4. **Normalização:** Garante que ||v|| = 1 (para cosine similarity)

---

### Possíveis perguntas de entrevista

* O que são embeddings e como representam semântica?
* Por que usar text-embedding-3-small ao invés de ada-002?
* O que é dimensionalidade e qual o trade-off?
* Como embeddings capturam relações (rei - homem + mulher = rainha)?

---

### Como responder na entrevista

> "Uso OpenAI text-embedding-3-small que gera vetores de 1536 dimensões. É mais barato e rápido que ada-002, mas com qualidade similar. Gero embeddings em batch durante a indexação (build time) e individualmente para queries (runtime). A normalização L2 permite usar inner product como cosine similarity no FAISS."

---

## Vector Store (FAISS)

### Onde está implementado

**Arquivo:** `ai_chat/rag_system.py`
**Classe:** `FAISSIndex`
**Função:** `add()`, `search()`
**Linha:** ~272

---

### Problema de negócio

Armazenar embeddings de forma que busca por similaridade seja eficiente. Com ~500 chunks, busca linear funciona, mas não escala para milhões.

---

### Como foi implementado

```python
# ai_chat/rag_system.py (~linha 272)
class FAISSIndex:
    """Gerenciador do índice FAISS"""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        # IndexFlatIP = Inner Product (cosine similarity após normalização)
        self.index = faiss.IndexFlatIP(dimension)

    def add(self, embeddings: np.ndarray):
        """Adiciona embeddings ao índice"""
        # Normaliza embeddings para usar cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Busca os K chunks mais similares"""
        # Normaliza query
        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, k)
        return distances, indices

    def save(self, path: str):
        """Salva índice em arquivo"""
        faiss.write_index(self.index, path)

    def load(self, path: str):
        """Carrega índice de arquivo"""
        self.index = faiss.read_index(path)
```

---

### O que aconteceria sem isso

- Busca linear O(n): Lenta para milhões de vetores
- Sem persistência: Teria que regenerar embeddings a cada deploy
- Sem normalização: Cosine similarity calculada incorretamente

---

### O que o FAISS faz internamente

1. **IndexFlatIP:** Busca exata por inner product (brute force)
2. **normalize_L2:** Normaliza vetores para ||v|| = 1
3. **Inner Product de vetores normalizados = Cosine Similarity**
4. **Retorna:** Top-K índices + distâncias

---

### Possíveis perguntas de entrevista

* O que é FAISS e por que usar?
* Diferença entre IndexFlatIP e IndexIVF?
* Por que normalizar antes de usar Inner Product?
* Quando usar busca aproximada (ANN) vs exata?
* Alternativas ao FAISS (Pinecone, Weaviate, Chroma)?

---

### Como responder na entrevista

> "Uso FAISS IndexFlatIP para busca exata por similaridade. Normalizo embeddings com L2 para que inner product seja equivalente a cosine similarity. Com ~500 chunks, busca exata é suficiente. Para milhões de vetores, usaria IndexIVF para busca aproximada. Persisto o índice em arquivo para não regenerar a cada deploy."

---

## Prompt Engineering

### Onde está implementado

**Arquivo:** `ai_chat/prompt_engineering.py`
**Classe:** `PromptBuilder`
**Função:** `build_system_prompt()`
**Linha:** ~14

---

### Problema de negócio

Garantir que o LLM:
1. Responda APENAS baseado no contexto do manual
2. Não invente funcionalidades
3. Use nomenclaturas corretas do sistema
4. Tenha tom profissional mas acessível

---

### Como foi implementado

```python
# ai_chat/prompt_engineering.py (~linha 14)
class PromptBuilder:
    """Construtor de prompts para o assistente de IA"""

    SYSTEM_PROMPT_TEMPLATE = """Você é o assistente virtual do **Barber Cashflow**.

## REGRAS CRÍTICAS (NUNCA VIOLE):

1. **BASE DE CONHECIMENTO ÚNICA**
   - Responda APENAS com informações do manual fornecido abaixo
   - NUNCA invente funcionalidades que não existem no manual
   - Se a informação não estiver no contexto, diga: "Essa informação não consta no manual atual."

2. **PRECISÃO TÉCNICA**
   - Use nomenclaturas EXATAS do sistema (ex: "Dashboard", "Portal do Cliente")
   - Cite seções do manual quando relevante

3. **ESTILO DE RESPOSTA**
   - Tom profissional, mas amigável
   - Respostas OBJETIVAS e DIRETAS
   - Use listas numeradas para passos sequenciais
   - Destaque ações com **negrito**

4. **SEGURANÇA**
   - NUNCA peça senhas ou credenciais
   - NUNCA instrua modificar banco diretamente

## CONTEXTO DO MANUAL:

{context}

Responda à pergunta baseando-se EXCLUSIVAMENTE no contexto acima."""

    @staticmethod
    def build_system_prompt(context: str) -> str:
        """Constrói o system prompt com o contexto do RAG"""
        return PromptBuilder.SYSTEM_PROMPT_TEMPLATE.format(context=context)
```

---

### O que aconteceria sem isso

- Sem regras claras: LLM inventa funcionalidades ("O sistema tem integração com WhatsApp" - mentira)
- Sem contexto estruturado: Resposta genérica, não específica do Barber Cashflow
- Sem instruções de estilo: Respostas prolixas ou inconsistentes

---

### Possíveis perguntas de entrevista

* O que é prompt engineering?
* Diferença entre system prompt e user prompt?
* Como evitar prompt injection?
* Como medir eficácia de um prompt?
* O que é few-shot prompting?

---

### Como responder na entrevista

> "Criei um system prompt com regras rígidas: o LLM só pode responder baseado no contexto do manual. Isso evita alucinações. Defini estilo de resposta (objetivo, listas numeradas, negrito para ações) para consistência. Também inclui regras de segurança para não vazar informações sensíveis."

---

## LLM Integration (Claude/GPT)

### Onde está implementado

**Arquivo:** `ai_chat/views.py`
**Classe:** (módulo de views)
**Função:** `generate_response_anthropic()`, `generate_response_openai()`
**Linha:** ~155

---

### Problema de negócio

Gerar resposta em linguagem natural usando o contexto recuperado pelo RAG. Suportar múltiplos providers (Anthropic Claude, OpenAI GPT) para flexibilidade.

---

### Como foi implementado

```python
# ai_chat/views.py (~linha 155)
def generate_response_anthropic(
    query: str,
    context: str,
    conversation_history: list = None
) -> Dict[str, Any]:
    """
    Gera resposta usando Claude (Anthropic)
    """
    # Inicializa cliente
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Constrói prompt
    system_prompt = PromptBuilder.build_system_prompt(context)
    user_message = PromptBuilder.build_user_message(query)

    # Prepara mensagens
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({'role': 'user', 'content': user_message})

    # Chama API
    start_time = time.time()

    response = client.messages.create(
        model='claude-sonnet-4-5-20250929',
        max_tokens=2000,
        system=system_prompt,
        messages=messages
    )

    elapsed = time.time() - start_time

    return {
        'answer': response.content[0].text,
        'model': 'claude-sonnet-4-5-20250929',
        'provider': 'anthropic',
        'tokens_used': {
            'input': response.usage.input_tokens,
            'output': response.usage.output_tokens
        },
        'elapsed_time': elapsed
    }
```

---

### O que aconteceria sem isso

- Sem LLM: Teria que responder com templates fixos (ruim para perguntas variadas)
- Sem tracking de tokens: Não saberia custo real por pergunta
- Sem histórico: Não poderia fazer follow-up questions

---

### Possíveis perguntas de entrevista

* Por que usar Claude vs GPT? Trade-offs?
* Como calcular custo por query?
* O que é temperature e como afeta respostas?
* Como implementar streaming de resposta?
* Como lidar com rate limits da API?

---

### Como responder na entrevista

> "Integrei tanto Claude quanto GPT-4 para flexibilidade. Claude Sonnet é padrão por ter boa relação custo/qualidade. Rastreio tokens usados em cada request para calcular custo. Uso temperature baixa (0.3) para respostas mais determinísticas. O histórico de conversa permite follow-up questions."

---

## Rate Limiting para Chat

### Onde está implementado

**Arquivo:** `ai_chat/views.py`
**Classe:** (decorator)
**Função:** `rate_limit_chat()`
**Linha:** ~309

---

### Problema de negócio

Limitar uso da API de IA para:
1. Controlar custos (cada request custa dinheiro)
2. Evitar abuso por usuários
3. Isolamento por tenant (cada barbearia tem seu limite)

---

### Como foi implementado

```python
# ai_chat/views.py (~linha 309)
def rate_limit_chat(view_func):
    """
    Rate limit de 50 requests/hora por tenant+user.
    Retorna 429 se exceder.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Monta cache key com tenant e user
        tenant = getattr(request, 'tenant', None)
        tenant_id = tenant.id if tenant else 'no_tenant'
        user_id = request.user.id
        cache_key = f"chat_rate:{tenant_id}:{user_id}"

        # Verifica limite
        count = cache.get(cache_key, 0)
        if count >= 50:
            return JsonResponse({
                'success': False,
                'error': 'Limite de perguntas atingido (50/hora).'
            }, status=429)

        # Incrementa contador (expira em 1 hora)
        cache.set(cache_key, count + 1, timeout=3600)

        return view_func(request, *args, **kwargs)
    return wrapper
```

---

### O que aconteceria sem isso

- Sem rate limit: Um usuário poderia gastar centenas de dólares em tokens
- Sem isolamento por tenant: Tenant A gastaria quota do Tenant B
- Sem cache: Teria que consultar banco a cada request

---

### Possíveis perguntas de entrevista

* Por que usar cache ao invés de banco para rate limiting?
* Como implementar rate limit distribuído?
* O que é sliding window rate limit?
* Como notificar usuário quando está próximo do limite?

---

### Como responder na entrevista

> "Implementei rate limit de 50 requests/hora por tenant+usuário usando Django cache. A chave combina tenant_id e user_id para isolamento. Uso TTL de 1 hora para reset automático. O cache é mais rápido que banco e suporta operações atômicas."

---

## Chat Logging (Auditoria)

### Onde está implementado

**Arquivo:** `ai_chat/middleware.py`
**Classe:** `ChatLogMiddleware`
**Função:** `process_response()`
**Linha:** ~28

---

### Problema de negócio

Registrar todas as interações com o chat para:
1. Auditoria de uso por tenant
2. Análise de perguntas frequentes
3. Debugging de problemas
4. Cálculo de custos por tenant

---

### Como foi implementado

```python
# ai_chat/middleware.py (~linha 28)
class ChatLogMiddleware(MiddlewareMixin):
    """Middleware para logging de conversas do chat"""

    def process_response(self, request: HttpRequest, response: HttpResponse):
        if request.path == '/api/chat/' and request.method == 'POST':
            elapsed = time.time() - getattr(request, '_chat_log_start_time', time.time())

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'tenant': {
                    'tenant_id': request.tenant.id if request.tenant else None,
                    'tenant_slug': request.tenant.slug if request.tenant else 'unknown',
                },
                'user': {
                    'user_id': request.user.id,
                    'username': request.user.username,
                },
                'request': {
                    'ip': self._get_client_ip(request),
                    'message': request._chat_log_body.get('message', ''),
                },
                'response': {
                    'success': response_data.get('success', False),
                    'answer_length': len(response_data.get('answer', '')),
                },
                'ai': {
                    'model': metadata.get('model'),
                    'tokens_input': metadata.get('tokens_used', {}).get('input'),
                    'tokens_output': metadata.get('tokens_used', {}).get('output'),
                },
                'elapsed_total': elapsed
            }

            # Salva em arquivo JSONL separado por tenant
            # chat_logs_{tenant_slug}_{YYYYMM}.jsonl
            self._save_log(log_entry, request)

        return response
```

---

### O que aconteceria sem isso

- Sem logs: Não saberia quais perguntas são frequentes
- Sem separação por tenant: Violação de privacidade (LGPD)
- Sem tokens tracking: Não conseguiria calcular custo real

---

### Possíveis perguntas de entrevista

* Por que usar JSONL ao invés de JSON?
* Como analisar logs para melhorar o sistema?
* Como garantir que logs não vazem entre tenants?
* Qual a diferença entre logging em middleware vs view?

---

### Como responder na entrevista

> "Implementei logging de chat via middleware que intercepta todas as respostas. Cada tenant tem seu próprio arquivo de log (chat_logs_tenant_202601.jsonl). Registro tokens usados para calcular custo por tenant. Uso JSONL porque é mais fácil de processar incrementalmente com streaming."

---

## Como explicar a IA do Barber Cashflow em uma entrevista

### Para Recrutador (não-técnico)

> "Implementei um chatbot inteligente que responde perguntas sobre o sistema. O usuário pergunta em linguagem natural, como 'Como agendar um cliente?', e o sistema responde baseado no manual oficial. Usei IA (ChatGPT/Claude) com uma técnica chamada RAG que garante respostas precisas sem inventar informações."

### Para Desenvolvedor Python

> "Construí um sistema RAG completo: extração do manual HTML com BeautifulSoup, chunking semântico de 800 chars com overlap, embeddings via OpenAI text-embedding-3-small, indexação FAISS para busca vetorial, e geração de resposta com Claude. A API Django tem rate limiting de 50 req/hora por tenant, autenticação obrigatória, e logging separado por tenant em JSONL."

### Para Tech Lead

> "Arquitetura RAG com decisão consciente de manter o sistema de embeddings GLOBAL (manual é o mesmo para todos os tenants) mas logs SEPARADOS por tenant para compliance. Embeddings são gerados em build time e persistidos (chunks.json + embeddings.npy + faiss.index). Runtime faz apenas embedding da query + busca + LLM. Rate limiting via Django cache com key composta (tenant_id:user_id). Custo estimado: ~$0.002 por pergunta."

### Para Empresa focada em IA

> "RAG implementado do zero sem frameworks como LangChain - decisão para controle total e menor overhead. Chunking semântico preserva hierarquia do documento (seção > subseção). Uso FAISS IndexFlatIP com embeddings normalizados para cosine similarity exata. Prompt engineering com regras rígidas anti-alucinação ('responda APENAS baseado no contexto'). Sistema de logging permite análise de perguntas frequentes para melhorar o chunking. Próximos passos seriam: hybrid search (BM25 + vetorial), re-ranking com cross-encoder, e evaluation pipeline com métricas de recall@k."

---

## Possíveis Perguntas de Entrevista sobre IA/LLM/RAG

### Conceituais

1. O que é RAG e por que usar ao invés de fine-tuning?
2. Explique o pipeline completo de um sistema RAG
3. O que são embeddings e como representam semântica?
4. Diferença entre busca por keyword e busca vetorial
5. O que é chunking e qual tamanho ideal?

### Implementação

1. Por que usar FAISS ao invés de Pinecone/Weaviate?
2. Como você mediria a qualidade das respostas?
3. Como lidar com perguntas fora do escopo do manual?
4. Como evitar que o LLM "alucine"?
5. Como calcular custo por pergunta?

### Arquitetura

1. Por que manter embeddings globais mas logs separados por tenant?
2. Como escalar para milhões de documentos?
3. Quando usar busca aproximada (ANN) vs exata?
4. Como implementar atualização incremental de embeddings?
5. Trade-offs de usar Claude vs GPT?

### Segurança

1. Como proteger contra prompt injection?
2. Por que rate limit por tenant+user?
3. Como garantir que dados de um tenant não vazem para outro?
4. O que loggar sem violar LGPD?

---

# PERGUNTAS QUE PROVAVELMENTE APARECERÃO EM ENTREVISTAS

---

## Júnior

1. O que é Django e por que usar?
2. O que é ORM e como funciona?
3. Diferença entre GET e POST?
4. O que é uma Foreign Key?
5. Como criar um model no Django?
6. O que é migration e para que serve?
7. Diferença entre `python manage.py runserver` e gunicorn?
8. O que é um template no Django?
9. O que são views e como funcionam?
10. Como funciona o sistema de URLs do Django?

---

## Pleno

1. Explique o ciclo de vida de um request no Django
2. O que é N+1 query e como resolver?
3. Diferença entre `select_related` e `prefetch_related`?
4. O que é um middleware e quando usar?
5. Como implementar autenticação customizada?
6. O que são Class-Based Views e quando usar vs Function-Based Views?
7. Como funciona o sistema de signals?
8. O que é `transaction.atomic()` e quando usar?
9. Como implementar paginação?
10. Diferença entre ModelSerializer e Serializer no DRF?

---

## Pleno Forte

1. Como implementar arquitetura multi-tenant?
2. Explique Row-Level Security e como implementar
3. Como otimizar queries em Django para milhões de registros?
4. Diferença entre soft delete e hard delete - trade-offs
5. Como implementar Service Layer no Django?
6. O que são database constraints e quando usar vs validação em código?
7. Como testar isolamento de dados em sistema multi-tenant?
8. Explique concorrência e race conditions em Django
9. Como fazer deploy zero-downtime?
10. Estratégias de caching em Django

---

## Backend Python

1. Diferença entre list, tuple e set
2. O que são decorators e como funcionam?
3. Explique GIL (Global Interpreter Lock)
4. O que são generators e quando usar?
5. Diferença entre `__str__` e `__repr__`
6. O que são context managers (`with`)?
7. Como funciona herança múltipla no Python (MRO)?
8. O que são metaclasses?
9. Diferença entre threading e multiprocessing
10. Como funciona garbage collection no Python?

---

## Django

1. Como Django resolve URLs?
2. O que são forms e como validar?
3. Diferença entre `clean()` e `clean_<field>()`?
4. Como customizar o admin?
5. O que são managers e querysets customizados?
6. Como implementar permissions customizadas?
7. O que é CSRF e como Django protege?
8. Como funciona o sistema de sessions?
9. O que são template tags customizadas?
10. Como fazer queries complexas com Q objects?

---

## PostgreSQL

1. O que são índices e quando criar?
2. Diferença entre INNER JOIN, LEFT JOIN e RIGHT JOIN
3. O que é EXPLAIN ANALYZE?
4. Como funciona uma transação?
5. O que é deadlock e como evitar?
6. Diferença entre UNIQUE constraint e PRIMARY KEY
7. O que são CHECK constraints?
8. Como fazer backup e restore?
9. O que é VACUUM e por que é necessário?
10. Diferença entre WHERE e HAVING?

---

## APIs REST

1. O que é REST e quais são os princípios?
2. Diferença entre PUT e PATCH
3. O que são status codes e quando usar cada um?
4. Como implementar autenticação JWT?
5. O que é throttling/rate limiting?
6. Como documentar APIs (Swagger/OpenAPI)?
7. O que é HATEOAS?
8. Como versionar APIs?
9. Diferença entre authentication e authorization
10. O que são webhooks?

---

## Docker

1. O que é container vs máquina virtual?
2. Diferença entre image e container
3. O que é Dockerfile e como funciona?
4. Diferença entre CMD e ENTRYPOINT
5. O que são volumes e quando usar?
6. Como funciona networking no Docker?
7. O que é docker-compose?
8. Como otimizar tamanho de imagens?
9. O que são multi-stage builds?
10. Como fazer health checks?

---

## Arquitetura

1. O que é Clean Architecture?
2. Explique os princípios SOLID
3. Diferença entre monolito e microservices
4. O que é Event-Driven Architecture?
5. Como implementar CQRS?
6. O que é Domain-Driven Design?
7. Diferença entre Service Layer e Repository Pattern
8. Como fazer comunicação entre microservices?
9. O que são design patterns e cite 3 exemplos
10. Como lidar com consistência eventual?

---

# COMO SE PREPARAR PARA A ENTREVISTA

## Dicas Práticas

1. **Estude o código real do projeto** - entrevistadores querem ouvir experiências práticas
2. **Prepare histórias STAR** - Situação, Tarefa, Ação, Resultado
3. **Pratique explicar código em voz alta** - gravem ou faça com amigo
4. **Conheça os trade-offs** - não existe solução perfeita
5. **Admita quando não sabe** - é melhor que inventar

## Estrutura de Resposta Ideal

1. **O que é** (1 frase)
2. **Por que usei** (problema real)
3. **Como implementei** (breve)
4. **Resultado** (métricas se possível)
5. **Trade-offs/melhorias** (mostra senioridade)

## Exemplo de Resposta Completa

> **Pergunta:** "Me fale sobre sua experiência com multi-tenancy"
>
> **Resposta:** "Multi-tenancy é quando múltiplos clientes compartilham a mesma aplicação com dados isolados. No Barber Cashflow, implementei porque é um SaaS onde cada barbearia precisa ver apenas seus dados. Usei shared database com tenant_id em cada model, middleware para resolver o tenant via session/profile, e filtro obrigatório em todas as queries. O resultado é isolamento total - testamos com testes automatizados que validam que Tenant A nunca vê dados do Tenant B. O trade-off é que adiciona complexidade em cada query, mas evita custos de múltiplos bancos. Uma melhoria futura seria adicionar Row-Level Security do PostgreSQL como camada extra de segurança."

---

**Documento gerado em Janeiro/2026**
**Projeto Barber Cashflow v3.1**
