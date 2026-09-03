# Perfil Público do Atleta — Integração com o Backend

**Data:** 2026-09-02
**Status:** Aprovado
**Spec de origem:** `docs/superpowers/specs/2026-08-11-smartscout-rede-social-design.md`
**Cobre:** F2 (fatia ATHLETE) + acréscimos sociais aprovados pela equipe

---

## Sumário

- [1. Contexto e objetivo](#1-contexto-e-objetivo)
- [2. Estado atual e achados](#2-estado-atual-e-achados)
- [3. Decisões](#3-decisões)
- [4. Modelo de dados](#4-modelo-de-dados)
- [5. Contrato HTTP](#5-contrato-http)
- [6. Estrutura dos módulos](#6-estrutura-dos-módulos)
- [7. Frontend](#7-frontend)
- [8. Estratégia de testes](#8-estratégia-de-testes)
- [9. Fatiamento da entrega](#9-fatiamento-da-entrega)
- [10. Riscos](#10-riscos)
- [11. Fora de escopo](#11-fora-de-escopo)

---

## 1. Contexto e objetivo

A página `PublicProfile` existe no frontend com **dados inteiramente mockados**. O objetivo
é integrá-la ao backend real.

O enquadramento importa: isto **não é "trocar mock por fetch"**. Com exceção de nome e
sobrenome, nenhum campo exibido na tela tem tabela, endpoint ou coluna correspondente
hoje. A página depende do módulo `profiles`, que não existe. Esta entrega é, portanto, a
fatia ATHLETE do sub-projeto **F2 (Identidade multi-papel)** do roadmap, mais dois
acréscimos sociais decididos pela equipe.

---

## 2. Estado atual e achados

### 2.1 O que a página mostra e onde o dado vive

| Campo no mock | Situação |
|---|---|
| `first_name`, `last_name` | existe em `users` |
| `position`, `height`, `foot`, `bio`, cidade/estado | **não existe** — dependem de `athlete_profiles` |
| `age` | **não existe** — derivado de `birth_date` (§5.7 da spec de origem) |
| `stats.clips` | derivável via `clips → processing_jobs → videos.user_id` |
| `title` e `tags` do clipe | **não existem** em `clips` |
| `status` ("Disponível para Clube") | **não existe** no domínio nem no roadmap |
| Seguir / Salvar Atleta | **não existem** no domínio nem no roadmap |

### 2.2 Divergências entre a spec de origem e o código

Registradas porque afetaram decisões deste design:

1. **Existem duas árvores de teste de backend, mutuamente incompatíveis.** A §10.3 está
   correta: `tests/unit`, `tests/integration` e `conftest.py` existem na **raiz** do
   repositório, com 33 testes de backend verdes (14 deles cobrindo register, login,
   logout e reset de senha em `tests/unit/backend/test_auth.py`), além de testes de ML.
   Essa suíte usa SQLite em memória com `create_all` e roda no host.

   Esta entrega cria uma segunda suíte em `backend/tests/`, com Postgres real e schema
   vindo das migrações, rodando dentro do container. As duas **não coexistem numa mesma
   execução do pytest**: ambas declaram um pacote `tests` de topo e a coleta conjunta
   falha com `ImportPathMismatchError`. O `pytest.ini` da raiz tem `testpaths = tests`,
   então quem roda pytest na raiz vê apenas a antiga.

   **Decisão:** consolidar em `backend/tests/`, adaptando os testes de backend existentes
   ao Postgres com migrações e reescopando o `pytest.ini` da raiz para ML e integração.
   Não há cobertura de frontend em lugar nenhum — vitest continua sendo criado do zero.

2. **Nenhum módulo tem `service.py` ou `repository.py`.** `identity` e `clips` têm apenas
   `router/models/schemas`, com a regra de negócio dentro do router — o problema #4 da
   spec de origem, que o F0 não chegou a resolver. `profiles` será o primeiro módulo com a
   anatomia completa da §4.2.

3. **`identity/router.py` levanta `HTTPException` diretamente**, contrariando a §10.2.
   `clips/router.py` já usa exceções de domínio. O código está parcialmente migrado.

4. **O F3 (base do frontend) não foi feito.** Não há TanStack Query, Tailwind, `features/`
   nem `httpClient`; o front é `pages/` + `services/api.ts`.

### 2.3 Estado utilizável

- Alembic está adotado, com uma migração baseline (`dc5867a2d8e8`).
- `core/exceptions.py` tem a hierarquia da §10.2 completa, e o handler único está no `main.py`.
- `core/deps.py` fornece `get_current_user` por JWT Bearer.
- `VITE_API_PATH` já inclui `/api/v1`; o front concatena `${VITE_API_PATH}${fileUrl}`.
- Nada referencia a rota `/public-profile` além da própria definição em `App.tsx`.

---

## 3. Decisões

| # | Decisão | Alternativas descartadas | Razão |
|---|---|---|---|
| P1 | Fatia vertical só `ATHLETE` | F2 completo (3 papéis); só leitura sem CRUD | Entrega a página ponta a ponta sem construir perfil de scout/clube que nenhuma tela consome |
| P2 | Perfil exige autenticação | Totalmente público; público com dados reduzidos | `athlete_profiles` guarda data de nascimento, cidade e foto de atletas de base, potencialmente menores. O caso de uso real é scout logado avaliando atleta, então nada de produto se perde |
| P3 | Módulo `social` novo para seguir/salvar | Colocar em `profiles` | Perfil é dado do atleta; seguir é relação entre usuários. Misturar viola a coesão que a D3 protege |
| P4 | `profiles` estreia `service.py` + `repository.py` | Seguir o padrão atual (regra no router) | O teste unitário de service com repository fake (§10.3) é impossível sem essa separação |
| P5 | Postgres de teste no Compose, com schema montado por `alembic upgrade head` | SQLite em memória com `create_all`; SQLite rodando migrações; testcontainers | Faz cada execução da suíte exercitar as migrações, sem depender de ninguém lembrar de rodá-las. Mesmo banco da produção, então enum, JSON e `server_default` são testados como se comportam de verdade |
| P6 | Adoção incremental do F3 | Seguir `services/api.ts`; fazer o F3 inteiro antes | Alinha com o alvo da §9 sem o custo de um sub-projeto tamanho G, e não engorda o arquivo que o F3 vai desmanchar |
| P7 | `tags` como coluna JSON | `ARRAY` do Postgres; tabela `clip_tags` | Lista curta de rótulos, sempre lida junto com o clipe e nunca consultada isoladamente — tabela separada seria over-engineering. `ARRAY` seria igualmente viável sob P5; JSON é escolhido por ser o tipo que o SQLModel expressa sem `sa_column` customizado |
| P8 | `PUT` idempotente para seguir/salvar | `POST` | Casa com a PK composta e evita 409 em clique duplo |

### 3.1 Acréscimos fora da spec de origem

Seguir e Salvar Atleta **não constam** na spec de origem nem em nenhum módulo do roadmap
(M1–M7). Foram incluídos por decisão explícita da equipe, com a ressalva registrada de que
introduzem duas tabelas não previstas. Enviar Mensagem foi mantido fora: pertence ao M5.

---

## 4. Modelo de dados

### 4.1 Migração 1 — `users` ganha `role`

```
users.role ∈ {ATHLETE, SCOUT, CLUB}   NOT NULL, imutável após o cadastro
```

Backfill dos usuários existentes como `ATHLETE`.

**`plan` não entra e `max_clips_allowed` não sai.** Ambos pertencem ao M6 (Entitlements);
antecipá-los criaria coluna sem consumidor.

### 4.2 Migração 2 — `athlete_profiles`

Relação 1:1 com `users`, criada na mesma transação do cadastro (§5.1 da spec de origem:
usuário sem perfil do seu papel é estado inválido).

| Coluna | Tipo | Nulo | Nota |
|---|---|---|---|
| `user_id` | UUID | não | PK **e** FK → `users.id` |
| `position` | enum | sim | `GOLEIRO, ZAGUEIRO, LATERAL, VOLANTE, MEIA, ATACANTE` |
| `birth_date` | date | sim | fonte da idade |
| `height_cm` | int | sim | inteiro em cm; `"1,78 m"` é formatação de view |
| `dominant_foot` | enum | sim | `DESTRO, CANHOTO, AMBIDESTRO` |
| `state` | char(2) | sim | |
| `city` | str | sim | |
| `current_club` | str | sim | |
| `bio` | text | sim | alimenta a aba "Sobre" |
| `avatar_path` | str | sim | coluna nasce; upload fica fora (§11) |
| `status` | enum | não | `DISPONIVEL, CONTRATADO, NAO_DISPONIVEL`, default `DISPONIVEL` |

Índices: `(position, state)` e `birth_date`, conforme §5.7 da spec de origem, que os
antecipa para a busca do M3.

`position` é enum e não texto livre precisamente porque o M3 vai indexar e filtrar por ela.

O backfill cria perfil vazio para cada usuário existente, preservando o invariante 1:1.

### 4.3 Migração 3 — `clips` ganha `title` e `tags`

| Coluna | Tipo | Nulo |
|---|---|---|
| `title` | str | sim |
| `tags` | JSON (array de strings) | não, default `[]` |

### 4.4 Migração 4 — tabelas sociais

```
follows (follower_user_id, followed_user_id, created_at)
  PK composta (follower_user_id, followed_user_id)
  CHECK (follower_user_id <> followed_user_id)

saved_athletes (user_id, athlete_user_id, created_at)
  PK composta (user_id, athlete_user_id)
```

A PK composta é o que torna seguir/salvar idempotente no nível do banco.

### 4.5 Invariantes

- **Idade nunca é coluna.** Derivada de `birth_date` na leitura. Guardar idade é bug que
  envelhece sozinho (§5.7 da spec de origem).
- **Contagem de clipes** sai do join `clips → processing_jobs → videos.user_id`. O
  `user_id` direto em `processing_jobs` previsto na §5.3 pertence ao F1 e não é antecipado.

---

## 5. Contrato HTTP

Todos os endpoints exigem JWT (`get_current_user`). Prefixo global `/api/v1`.

### 5.1 `profiles`

| Verbo | Rota | Retorno |
|---|---|---|
| `GET` | `/profiles/athletes/{user_id}` | perfil do atleta |
| `GET` | `/profiles/me` | próprio perfil, para o formulário de edição |
| `PUT` | `/profiles/me` | perfil atualizado |

`GET /profiles/athletes/{user_id}`:

```json
{
  "user_id": "…",
  "first_name": "Jeh",
  "last_name": "Rodrigues",
  "position": "ATACANTE",
  "status": "DISPONIVEL",
  "age": 19,
  "height_cm": 178,
  "dominant_foot": "DESTRO",
  "city": "Campinas",
  "state": "SP",
  "current_club": null,
  "bio": null,
  "avatar_url": null,
  "clips_count": 42,
  "is_followed_by_me": false,
  "is_saved_by_me": false
}
```

`age` é derivada no service. `is_followed_by_me` e `is_saved_by_me` vêm de
`social_service.is_following(...)` e `social_service.is_saved(...)` — chamada de service
para service, que é o que a D3 permite. Ficam nesta resposta, e não em endpoint próprio,
para a página não disparar três requisições em cascata só para pintar dois botões.

**Esses dois campos entram no contrato apenas na fatia 3**, junto com o módulo `social`.
Nas fatias 1 e 2 eles simplesmente não existem na resposta, e os botões correspondentes
ficam desabilitados no front. A alternativa — devolvê-los com `false` fixo desde a fatia 1
— foi descartada: um campo que sempre mente é pior que um campo ausente, porque o cliente
não tem como distinguir "não segue" de "ainda não implementado".

`PUT /profiles/me` aceita atualização **parcial**: apenas os campos enviados são alterados.
Aceita `position`, `birth_date`, `height_cm`, `dominant_foot`, `city`, `state`,
`current_club`, `bio`, `status`. Nome e e-mail pertencem a `identity` e não são editáveis
por esta rota.

### 5.2 `identity` — mudança no registro

`POST /auth/register` passa a receber `role` e a criar o `athlete_profile` na mesma
transação.

**Nesta entrega, `role` só aceita `ATHLETE`.** `SCOUT` e `CLUB` são rejeitados com
`ValidationError` (422) até que suas tabelas de perfil existam. A razão é o invariante da
§5.1 da spec de origem: usuário sem perfil correspondente ao seu papel é estado inválido.
Aceitar `SCOUT` agora criaria exatamente esse estado, e a dívida apareceria como perfil
órfão em produção, não como erro no cadastro. O enum de `role` já nasce com os três
valores no banco (§4.1) — o que a fatia 1 restringe é apenas o que o endpoint aceita.

### 5.3 `clips`

| Verbo | Rota |
|---|---|
| `GET` | `/clips/athletes/{user_id}?limit=&offset=` |

Cada item: `id`, `title`, `tags`, `duration_seconds`, `file_url`, `created_at`.

`file_url` continua no formato relativo `/uploads/clips/{job_id}/{arquivo}`, que é a
convenção já usada pelo front (`${VITE_API_PATH}${fileUrl}`).

Atleta sem clipes devolve lista vazia com 200 — não 404.

### 5.4 `social`

| Verbo | Rota |
|---|---|
| `PUT` / `DELETE` | `/social/follows/{user_id}` |
| `PUT` / `DELETE` | `/social/saved-athletes/{user_id}` |

### 5.5 Erros

Sempre por exceção de domínio, traduzida pelo handler único do `main.py`. **Nenhum
`HTTPException` nos routers novos** (§10.2).

| Caso | Exceção | HTTP |
|---|---|---|
| `user_id` inexistente, ou usuário sem perfil de atleta | `NotFoundError` | 404 |
| Seguir ou salvar a si mesmo | `ValidationError` | 422 |
| Token ausente no header `Authorization` | `HTTPBearer` | 401 |
| Token presente porém inválido ou expirado | `get_current_user` | 401 |

Verificado no FastAPI 0.133.1 instalado: header ausente devolve `401 {"detail": "Not authenticated"}`.
Versoes antigas devolviam 403, e e por isso que `test_auth.py:190` e `test_jobs.py:86` usam
`assert status_code in (401, 403)`. Testes novos podem fixar 401.

Usuário existente porém com `role != ATHLETE` devolve **404**, não 403: não existe perfil
de atleta para aquele id, e a distinção não interessa ao cliente.

---

## 6. Estrutura dos módulos

Anatomia da §4.2 da spec de origem, estreando de fato:

```
backend/app/modules/profiles/
├─ router.py       HTTP: rota, validação, serialização. Sem regra.
├─ service.py      regra de negócio; único ponto de entrada para outros módulos
├─ repository.py   acesso a dados; só o próprio módulo usa
├─ models.py       AthleteProfile
└─ schemas.py      DTOs de entrada e saída

backend/app/modules/social/
└─ (mesma anatomia)
```

`repository.py` expõe um `Protocol` (`AthleteProfileRepository`), com implementação real
sobre `Session` e uma fake em dicionário nos testes. Essa abstração não é cerimônia: é o
que permite testar o cálculo de idade e as regras de erro sem subir banco, e é a razão de
P4.

**Fronteira preservada:** `profiles` consome `social` apenas via `social_service`. Nenhum
módulo lê tabela alheia.

---

## 7. Frontend

### 7.1 Estrutura

```
frontend/src/
├─ shared/lib/
│  ├─ httpClient.ts       JWT, timeout, tratamento de 401, erro tipado
│  └─ queryClient.ts      configuração do TanStack Query
└─ features/profiles/
   ├─ api.ts              getAthleteProfile · getMyProfile · updateMyProfile
   ├─ types.ts            DTO da API e view model da tela
   ├─ mappers.ts          funções puras — alvo dos testes
   ├─ hooks/              useAthleteProfile · useAthleteClips · useFollowAthlete
   └─ components/         ProfileHeader · QuickStats · ClipsTab · AboutTab
```

`httpClient` nasce absorvendo o que já existe em `services/api.ts` (`fetchWithTimeout`,
injeção de JWT), como peça isolada e testável. `services/api.ts` **não é tocado**; migrar
as outras páginas é trabalho do F3.

### 7.2 Rota

`/public-profile` passa a `/athletes/:userId`, dentro de `PrivateRoute` + `MainLayout`,
coerente com P2. A renomeação é gratuita: nada referenciava a rota antiga.

### 7.3 O que muda em `PublicProfile.tsx`

O arquivo tem ~190 linhas concentrando mock, layout, abas e estilos inline. Passa a ser um
contêiner fino que lê `useParams`, chama os hooks e distribui para os quatro componentes.

- `mockAthlete` e `mockClips` saem.
- **Entram estados que hoje não existem:** carregando, erro e "atleta não encontrado". A
  página atual assume que o dado sempre chega — com API real, isso é tela quebrada na
  primeira falha de rede.
- Videoteca vazia ganha estado próprio, em vez de grade vazia sem explicação.
- Os `style={{...}}` espalhados migram para o CSS, já que o JSX está sendo reescrito.

### 7.4 Abas e botões

| Elemento | Destino |
|---|---|
| Aba "Sobre" | passa a exibir `bio` |
| "Histórico" dentro de "Sobre" | **removido** — texto inventado, sem lastro no domínio |
| Aba "Análise Cinemática" | mantida como placeholder; já se declara em desenvolvimento |
| `Seguir`, `Salvar Atleta` | ligados às mutations da fatia 3, com atualização otimista e rollback no erro |
| `Enviar Mensagem` | visível e **desabilitado**; pertence ao M5 |

Nas fatias 1 e 2, `Seguir` e `Salvar` ficam desabilitados. Cada fatia termina numa tela
coerente, sem controle que finge funcionar.

### 7.5 Thumbnail de clipe

Nenhuma tabela guarda thumbnail de clipe. Em vez de inventar coluna, o card usa
`<video preload="metadata">`, que exibe o primeiro quadro sem custo de backend.

---

## 8. Estratégia de testes

### 8.1 Estrutura

```
backend/tests/
├─ conftest.py          fixtures: engine de teste, session, TestClient, usuário + JWT
├─ unit/                service com repository fake — sem banco, sem HTTP
└─ integration/         TestClient + banco de teste
```

### 8.2 Banco de teste

Serviço `postgres-test` no `docker-compose.yml`, isolado do banco de desenvolvimento
(Supabase). A fixture de sessão monta o schema executando **`alembic upgrade head`**, não
`SQLModel.metadata.create_all`.

Essa escolha é deliberada e é o ponto central do P5: **as migrações passam a ser
exercitadas a cada execução da suíte.** Uma migração que não aplica, um backfill que
quebra ou um modelo que divergiu do schema versionado falham no teste, e não em produção.
Com `create_all`, o schema de teste nasceria dos modelos e as migrações nunca rodariam —
exatamente o cenário em que o teste passa e o deploy quebra.

`backend/alembic/env.py:31` já lê a URL de `os.environ["DATABASE_URL"]`, sem nada
hardcoded no `alembic.ini`, então apontar a suíte para o banco de teste é só variável de
ambiente.

**O loop rápido do TDD não paga por isso.** Os testes unitários usam repository fake e não
tocam banco nenhum — rodam em milissegundos. O Postgres só é exigido pelos testes de
integração, que são o loop externo. Uma versão anterior deste spec usava SQLite
justificando velocidade de TDD; a justificativa era falsa, porque otimizava um loop que
nunca teve banco.

Cada migração ganha `downgrade()` implementado e testado — subir e descer o schema é o que
garante que a migração é reversível quando algo dá errado em produção.

### 8.3 Casos por fatia

**Fatia 1 — profiles**

| Camada | Casos |
|---|---|
| unit | idade a partir de `birth_date`, incluindo aniversário ainda não ocorrido no ano; `birth_date` nulo → `age: null`; perfil inexistente → `NotFoundError`; `role != ATHLETE` → `NotFoundError`; `PUT` parcial altera só os campos enviados |
| integração | `GET` sem JWT → 401; com JWT → 200 e shape do contrato; id inexistente → 404; `PUT /me` reflete no `GET` seguinte; `register` com `role = ATHLETE` cria perfil na mesma transação; `register` com `SCOUT` ou `CLUB` → 422 |

**Fatia 2 — videoteca:** duração derivada de `end - start`; ordenação decrescente por
`created_at`; `limit`/`offset`; atleta sem clipes → lista vazia com 200.

**Fatia 3 — social:** seguir a si mesmo → `ValidationError`; seguir duas vezes é
idempotente; deixar de seguir quem não se segue não falha; reflexo em `is_followed_by_me`.

**Testes de caracterização:** `POST /auth/register` é alterado pela fatia 1 e hoje não tem
teste nenhum. Seus testes de caracterização são escritos **antes** da alteração — do
contrário a fatia mexe num fluxo de autenticação sem rede de proteção.

### 8.4 Frontend

Vitest, com alvo em funções puras e hooks — não em marcação:

- Mappers: `formatHeight(178) → "1,78 m"`, `formatLocation("Campinas", "SP")`,
  `formatDuration(45) → "0:45"`. Hoje isso está embutido no JSX como literal; extrair é
  ganho de clean code por si só.
- `useAthleteProfile` com `httpClient` mockado: carregando, sucesso, erro e 404.

**Fora do escopo de teste, deliberadamente:** CSS, estrutura de marcação e as abas
"Análise" e "Sobre". Testar marcação trava refatoração visual sem pegar bug real.

### 8.5 Ciclo

Cada fatia roda vermelho → verde → refatorar, com commit nos verdes.

| Loop | Comando | Banco |
|---|---|---|
| unitário (interno) | `docker compose exec api pytest tests/unit` | nenhum — repository fake |
| integração (externo) | `docker compose exec api pytest tests/integration` | `postgres-test`, schema via `alembic upgrade head` |
| frontend | `npm test` | — |

O código está montado como volume, então nenhum dos comandos exige rebuild da imagem.

---

## 9. Fatiamento da entrega

Três fatias verticais sequenciais. Cada uma termina com a página funcionando e testada —
nada fica pela metade se o prazo apertar.

| Fatia | Escopo | Entrega visível |
|---|---|---|
| **1** | Infra de testes (pytest + vitest + serviço `postgres-test` no Compose), migrações 1 e 2, módulo `profiles`, `role` no registro, adoção incremental do F3 no front | Página renderiza identidade e estatísticas reais |
| **2** | Migração 3, endpoint de videoteca, `ClipsTab` | Aba Videoteca com clipes reais |
| **3** | Migração 4, módulo `social`, campos `is_followed_by_me` e `is_saved_by_me` entrando no contrato (§5.1), mutations no front | Seguir e Salvar funcionando |

O custo aceito: `PublicProfile.tsx` é tocado três vezes. Em troca, o feedback de que o
contrato serve à tela chega na fatia 1, e não no fim — que é exatamente o risco R2 que a
spec de origem já identificou.

---

## 10. Riscos

| # | Risco | Mitigação |
|---|---|---|
| **PR1** | Suíte de integração mais lenta por exigir Postgres no ar | Aceito: o loop rápido do TDD são os unitários com repository fake, que não tocam banco (§8.2). Contêiner sobe uma vez e é reaproveitado entre execuções |
| **PR2** | Alterar `POST /auth/register` quebra login/cadastro em produção | Testes de caracterização escritos antes da alteração (§8.3) |
| **PR3** | Videoteca lista clipes que a retenção (§7 da spec de origem) apagará em 14 dias | Não resolvível aqui: a coluna `clips.status` nasce no F1/M2. Registrado como dependência conhecida |
| **PR4** | `follows` e `saved_athletes` são tabelas fora do roadmap e podem conflitar com um módulo social futuro | Isoladas em módulo `social` próprio, acessível só por service (P3) |
| **PR5** | Backfill de `role` e de perfis vazios em base com dados reais | Migração idempotente e testada em cópia antes de aplicar |

---

## 11. Fora de escopo

Registrado para evitar reabertura:

- Perfis de `SCOUT` e `CLUB` (P1) — entram quando houver tela que os consuma.
- Upload de avatar. A coluna `avatar_path` nasce, o endpoint não; a página segue exibindo
  a inicial do nome.
- Enviar Mensagem — pertence ao M5.
- `plan` e a remoção de `max_clips_allowed` — pertencem ao M6.
- Gráficos da aba "Análise Cinemática".
- Histórico estruturado de clubes e conquistas do atleta.
- Migração das demais páginas para `features/` e TanStack Query — pertence ao F3.
- Coluna `clips.status` (`TEMPORARY`/`PERMANENT`) — pertence ao F1/M2.
