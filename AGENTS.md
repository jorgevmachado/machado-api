# machado-api

## Package Identity
RESTful API built with Python 3.13, FastAPI (async), SQLAlchemy async, Pydantic v2,
Alembic migrations, Redis cache, and PostgreSQL. Domain-driven layered architecture.

## Setup & Run
```bash
make init            # install all dependencies
make dev                  # start dev server (fastapi dev app/main.py)
make test                 # lint + pytest + coverage report
make lint                 # ruff check only
make format               # ruff fix + format
make create-migration message="describe change"  # autogenerate Alembic migration
make migrate              # apply pending migrations (alembic upgrade head)
make test-file file=tests/app/domain/<domain>/test_service.py  # single file
```

## Architecture: 5-Layer Stack
```
route.py  →  service.py  →  repository.py  →  models.py
                ↘ business.py (pure domain rules)
                ↘ schema.py   (Pydantic DTOs)
```
- Entry point: `app/main.py`
- Domain code: `app/domain/<domain>/`
- Shared infrastructure: `app/core/` (cache, db, security, logging, pagination)
- Shared schemas/utils: `app/shared/`
- DB models (cross-domain): `app/models/`
- Tests mirror source: `tests/app/domain/<domain>/`, `tests/app/core/<module>/`

## Patterns & Conventions

**Layer rules (strict)**
- `route.py` — delegates only; no business logic; explicit `response_model`; auth via `Depends(get_current_user)`
- `service.py` — orchestrates logic, cache, and errors; use `log_service_success` / `handle_service_exception`
- `repository.py` — SQLAlchemy queries only; extend `BaseRepository`; no business logic
- `business.py` — pure rules, calculations; no infra dependencies; highly testable
- `schema.py` — Pydantic DTOs; input/output contracts; no ORM coupling

**DOs**
- DO: Extend `BaseService` for standard CRUD — see `app/core/service/base.py`
- DO: Use `list_all_cached` / `find_one_cached` when caching a resource — see `app/core/service/base.py`
- DO: Use `handle_service_exception` in every service try/except — see `app/core/exceptions/exceptions.py`
- DO: Use `BaseRepository` for list/find/paginate — see `app/core/repository/base.py`
- DO: Add `get_current_user` dependency on protected endpoints — see `app/core/security/security.py`

**DON'Ts**
- DON'T: Put business logic in `route.py`
- DON'T: Query the DB directly in a router
- DON'T: Duplicate logic already in `BaseService` / `BaseRepository`
- DON'T: Modify historical Alembic migrations already applied in shared environments
- DON'T: Introduce external libraries without clear necessity

## Key Files
- App entry: `app/main.py`
- Settings: `app/core/settings.py`
- Auth: `app/core/security/security.py` (`get_current_user`, `create_access_token`)
- Cache: `app/core/cache/service.py` (`CacheService`)
- Base service: `app/core/service/base.py`
- Base repo: `app/core/repository/base.py`
- Shared schemas: `app/shared/schemas.py` (`FilterPage`, `Message`)
- Error handler: `app/core/exceptions/exceptions.py`
- Logging helpers: `app/core/logging/logging.py`

## JIT Index Hints
```bash
# Find all domain routes
rg -n "@router\.(get|post|put|delete|patch)" app/domain/

# Find service methods
rg -n "async def " app/domain/*/service.py

# Find repository queries
rg -n "async def " app/core/repository/base.py app/domain/*/repository.py

# Find all models
find app/models -name "*.py" ! -name "__init__.py"

# Run tests for one domain
make test-file file=tests/app/domain/<domain>/test_service.py
```

## Task Playbooks

### Add a route to an existing domain
1. `app/domain/<domain>/schema.py` — define input/output schemas
2. `app/domain/<domain>/service.py` — implement use case, reuse `BaseService` methods
3. `app/domain/<domain>/repository.py` — add query if needed
4. `app/domain/<domain>/route.py` — expose endpoint with `response_model`
5. `tests/app/domain/<domain>/test_route.py` + `test_service.py` — cover success + error

### Add a new DB entity
1. Create/alter model in `app/models/`
2. Update repository/service of owning domain
3. `make create-migration message="add <entity>"` — generate Alembic migration
4. `make migrate` — apply migration
5. Add tests for repository and service


# machado-api

## Package Identity
RESTful API Python 3.13, FastAPI async, SQLAlchemy, Pydantic v2, Alembic, Redis, PostgreSQL.

## Setup & Run
```bash
poetry install
make dev
make test
make lint
make format
make create-migration message="msg"
make migrate
```

## Patterns & Conventions
- 5 camadas: `route.py` → `service.py` → `repository.py` → `models.py`/`business.py`/`schema.py`
- Nunca coloque lógica de negócio em `route.py`
- Use `BaseService`/`BaseRepository` para CRUD
- Use cache via `CacheService` quando aplicável
- Testes espelham estrutura do código

## Key Files
- Entry: `app/main.py`
- Settings: `app/core/settings.py`
- Auth: `app/core/security/security.py`
- Cache: `app/core/cache/service.py`
- Base service: `app/core/service/base.py`
- Base repo: `app/core/repository/base.py`
- Shared schemas: `app/shared/schemas.py`

## JIT Index Hints
```bash
rg -n "@router\\.(get|post|put|delete|patch)" app/domain/
find app/models -name "*.py" ! -name "__init__.py"
```

## Common Gotchas
- Nunca altere migrations já aplicadas
- Sempre use variáveis de ambiente para configs sensíveis
- Testes devem cobrir todos os fluxos alterados

## Pre-PR Checklist
```bash
make lint && make test
```
- [ ] Mudança na camada correta
- [ ] Contrato HTTP e schemas/testes atualizados
- [ ] Logs/contexto adicionados
- [ ] Testes verdes
- [ ] Migration criada/revisada se DB mudou

## Repository boundaries

- Cada `repository.py` deve acessar somente os models pertencentes ao próprio domain.
- É proibido importar ou consultar models de outros domains dentro de um repository.
- Exemplo proibido: `domain/pokedex/repository.py` importar ou consultar `Pokemon` de `domain/pokemon`.
- Quando um domain precisar de dados de outro domain, a integração deve acontecer na camada de service/use case, usando o service/repository público do outro domain.
- O repository deve ser responsável apenas pela persistência do agregado/modelo principal daquele domain.
- Joins entre tabelas de domains diferentes só podem existir se forem explicitamente aprovados na especificação da feature.
- Antes de implementar qualquer método novo em um repository, sempre verificar primeiro se o `BaseRepository` já possui uma implementação reutilizável.
- O desenvolvedor/IA deve reutilizar métodos existentes do `BaseRepository` sempre que possível.
- É proibido duplicar lógica já existente no `BaseRepository`.
- Só é permitido criar um novo método no repository caso:
  - o comportamento realmente não exista no `BaseRepository`
  - a necessidade seja específica do domain
  - não seja possível parametrizar/reaproveitar um método já existente 
  - Antes de criar novos métodos, analisar especialmente operações comuns como:
    - `total`
    - `save`
    - `update`
    - `list_all`
    - `find_by` 
    - `soft_delete`
    - `exists` 
    - filtros genéricos
    - ordenação
    - eager loading
- Sempre preferir extensão/composição do `BaseRepository` ao invés de duplicação.

## Import rules

- Todos os imports devem ficar obrigatoriamente no topo do arquivo.
- É proibido realizar imports dentro de:
  - funções
  - métodos
  - condicionais
  - loops
  - context managers
  - blocos try/except
- Nunca utilizar lazy imports ou dynamic imports para resolver dependências entre domains.
- Nunca escrever imports inline como:
```python
if trainer_service is None:
    from app.domain.trainer.service import TrainerService
```
- O correto é sempre importar do topo do arquivo:
 ```python
    from app.domain.trainer.service import TrainerService
```

## Workflow obrigatório

Ao criar ou alterar um repository:

1. Ler o `BaseRepository`
2. Identificar métodos reutilizáveis
3. Reutilizar os métodos existentes
4. Somente criar novos métodos se realmente necessário

Ao criar ou alterar um service:

1. Ler o `BaseService`
2. Identificar métodos reutilizáveis
3. Reutilizar os métodos existentes
4. Somente criar novos métodos se realmente necessário

## Trainer Boundaries

- `app/domain/trainer/trainer_party/` é o domínio canônico para party.
- Endpoints canônicos de party:
  - `GET /trainer/party`
  - `PUT /trainer/party`
- `TrainerPartyService` é responsável por validar limite/duplicidade, carregar `MyPokemon`, aplicar soft delete da party ativa e invalidar `trainer:party:{trainer_id}` e `trainer:home:{trainer_id}`.

- `app/domain/trainer/service.py` é o agregador canônico da Home.
- Endpoint canônico de home:
  - `GET /trainer/home`
- `TrainerService.get_home()` deve apenas orquestrar `trainer_party_service.get_party_by_trainer_id()`, `trainer_exploration_service.get_active_encounter_by_trainer_id()` e `pokedex_service.list_latest_discoveries()`.

- `app/domain/trainer/trainer_exploration/` deve permanecer restrito a encounter/event/walk.
- Rotas antigas `/trainer/exploration/home` e `/trainer/exploration/party` não são mais canônicas e não devem voltar sem spec explícito.
