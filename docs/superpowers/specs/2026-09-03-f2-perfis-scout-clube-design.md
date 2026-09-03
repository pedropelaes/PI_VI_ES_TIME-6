# F2 Completo — Perfis de Scout e Clube

**Data:** 2026-09-03
**Status:** Aprovado
**Spec de origem:** `docs/superpowers/specs/2026-08-11-smartscout-rede-social-design.md` (§5.1)
**Continua:** `docs/superpowers/specs/2026-09-02-perfil-publico-atleta-design.md`

---

## 1. Por que esta fatia existe

A fatia anterior entregou `users.role` e o perfil de atleta, mas restringiu o cadastro a
`ATHLETE`: `POST /auth/register` rejeita `SCOUT` e `CLUB` com 422, porque suas tabelas de
perfil não existiam e um usuário sem perfil do seu papel é estado inválido (§5.1 da spec de
origem).

O resultado é incoerente do ponto de vista do produto: existe uma coluna `role` que o usuário
não pode escolher. Pior, o caso de uso central do SmartScout — **scout logado avaliando
atleta** — é impossível, porque não há como cadastrar um scout.

Esta fatia fecha isso.

---

## 2. Decisões

| # | Decisão | Alternativas descartadas | Razão |
|---|---|---|---|
| Q1 | Três rotas e três páginas: `/athletes/:id`, `/scouts/:id`, `/clubs/:id` | Rota única `/profiles/:id` com página que ramifica | Evita um `ProfilePage` gigante cheio de condicionais tentando servir três domínios diferentes. Cada tela fica simples e independente |
| Q2 | Três endpoints públicos, um por papel | Endpoint único polimórfico | Coerente com Q1. O papel está na URL, então o contrato de cada rota é fechado e tipado |
| Q3 | `GET`/`PUT /profiles/me` **são** polimórficos | Três variantes `/me/athlete` etc. | O recurso é identificado pelo usuário autenticado, não por URL pública tipada. O servidor descobre o papel pelo JWT; a URL não tem onde carregá-lo |
| Q4 | Resposta de `/me` no formato `{ role, profile: { ... } }` | Campos do perfil no topo, junto de `role` | Torna o contrato explícito e dá narrowing limpo no TypeScript |
| Q5 | Toda listagem de usuário navegável carrega `role` | Consultar o papel antes de montar cada link | Sem isso, todo card de feed ou resultado de busca precisaria de uma requisição extra só para saber para onde apontar |
| Q6 | `getProfilePath(user)` como ponto único de construção de rota | `if role` espalhado nos componentes | Se a estrutura de rotas mudar, muda em um lugar. Decisão do time |
| Q7 | Papéis em MAIÚSCULO (`ATHLETE`/`SCOUT`/`CLUB`) na API e no front | Minúsculo no front | É o enum nativo do Postgres e o que `UserResponse` já devolve desde a fatia 1. Traduzir caixa entre camadas cria um ponto de erro sem ganho |
| Q8 | Componente compartilhado para o cabeçalho visual comum | Triplicar cabeçalho, badges, localização e bio | Esse é o custo que três páginas cobram. Sem o compartilhado, cada ajuste visual vira três edições |

---

## 3. Modelo de dados

### 3.1 Migração — `scout_profiles`

1:1 com `users`, criada na mesma transação do cadastro.

| Coluna | Tipo | Nulo |
|---|---|---|
| `user_id` | UUID | não — PK **e** FK → `users.id` |
| `organization` | str | sim |
| `credential` | str | sim |
| `state` | char(2) | sim |
| `city` | str | sim |
| `bio` | text | sim |
| `avatar_path` | str | sim |
| `created_at` / `updated_at` | datetime | não |

### 3.2 Migração — `club_profiles`

| Coluna | Tipo | Nulo |
|---|---|---|
| `user_id` | UUID | não — PK **e** FK → `users.id` |
| `legal_name` | str | sim |
| `cnpj` | char(14) | sim |
| `categories` | JSON (array de strings) | não, default `[]` |
| `state` | char(2) | sim |
| `city` | str | sim |
| `bio` | text | sim |
| `avatar_path` | str | sim |
| `created_at` / `updated_at` | datetime | não |

`categories` guarda categorias de base (`SUB_15`, `SUB_17`, `SUB_20`, `PROFISSIONAL`). JSON
pelo mesmo motivo do `tags` da fatia anterior: lista curta, sempre lida junto do perfil.

**Sem backfill.** Todos os 17 usuários em produção são `ATHLETE` e já têm perfil. As duas
tabelas nascem vazias.

**`cnpj` não é validado nesta fatia** — só armazenado. Validação de dígito verificador é
regra de negócio que merece decisão própria; registrar como coluna livre agora não impede
apertar depois.

---

## 4. Contrato HTTP

Todos exigem JWT. Prefixo `/api/v1`.

### 4.1 Leitura pública, uma rota por papel

| Verbo | Rota |
|---|---|
| `GET` | `/profiles/athletes/{user_id}` (já existe) |
| `GET` | `/profiles/scouts/{user_id}` |
| `GET` | `/profiles/clubs/{user_id}` |

Cada uma devolve 404 quando o `user_id` não existe **ou** quando existe mas tem outro papel —
mesma semântica já estabelecida para atletas: não existe scout com aquele id, e a distinção
não interessa ao cliente.

`scouts/{id}` devolve `user_id`, `first_name`, `last_name`, `organization`, `credential`,
`city`, `state`, `bio`, `avatar_url`.
`clubs/{id}` devolve `user_id`, `first_name`, `last_name`, `legal_name`, `cnpj`,
`categories`, `city`, `state`, `bio`, `avatar_url`.

Nenhuma das duas tem `clips_count` nem `age` — são conceitos de atleta.

### 4.2 Próprio perfil, polimórfico

```json
GET /api/v1/profiles/me
{
  "role": "SCOUT",
  "profile": { "user_id": "…", "organization": "Cruzeiro", "credential": "CBF-1234", … }
}
```

`PUT /profiles/me` aceita os campos do papel do autenticado, com atualização parcial. Enviar
um campo que não pertence ao papel é 422.

### 4.3 Cadastro

`POST /auth/register` passa a aceitar os três papéis e cria o perfil correspondente na mesma
transação. A validação que hoje rejeita `SCOUT`/`CLUB` é **removida**.

### 4.4 Erros

Inalterado da fatia anterior: exceções de domínio traduzidas pelo handler único.
`NotFoundError` → 404, `ValidationError` → 422. Nenhum `HTTPException` nos routers novos.

---

## 5. Estrutura dos módulos

O módulo `profiles` cresce, mantendo a anatomia:

```
backend/app/modules/profiles/
├─ models.py       AthleteProfile · ScoutProfile · ClubProfile
├─ repository.py   um repositório por papel, cada um com seu Record
├─ service.py      ProfilesService por papel + provision_profile_for_role
├─ schemas.py      DTOs dos três
└─ router.py       as rotas por papel + /me polimórfico
```

`provision_athlete_profile(session, user_id)`, criado na fatia anterior para respeitar a regra
D3, generaliza para `provision_profile(session, user_id, role)` — `identity` continua
importando apenas de `profiles.service`.

**Se `models.py` ou `router.py` passarem de ~200 linhas, quebrar por papel** (`models/athlete.py`
etc.). Três domínios num arquivo é exatamente o que a Q1 evita nas telas; vale igual no backend.

---

## 6. Frontend

### 6.1 Rotas e o ponto único

```ts
// shared/lib/profileRoutes.ts
export function getProfilePath(user: { id: string; role: UserRole }): string
```

Decisão Q6. Nenhum componente monta URL de perfil por conta própria.

### 6.2 Estrutura

```
features/profiles/
├─ components/
│  ├─ ProfileShell.tsx      cabecalho, avatar, badges, localizacao, bio — os tres usam
│  ├─ AthleteStats.tsx      idade, pe, altura, clipes
│  ├─ ScoutDetails.tsx      organizacao, credencial
│  └─ ClubDetails.tsx       razao social, CNPJ, categorias
├─ hooks/  useAthleteProfile · useScoutProfile · useClubProfile · useMyProfile
└─ pages/  AthleteProfilePage · ScoutProfilePage · ClubProfilePage
```

`ProfileShell` é a decisão Q8: o que é idêntico nos três mora em um lugar.

### 6.3 Cadastro

`SignUp` ganha seleção de papel — os três habilitados. O papel é imutável após o cadastro
(§13 da spec de origem), então a tela deve deixar isso claro antes de submeter.

### 6.4 Botão de perfil no header

O modal do `Header` ganha "Ver meu perfil", usando `getProfilePath(getUser())`. Isso fecha a
lacuna deixada pela fatia anterior, em que a página só era alcançável digitando a URL.

---

## 7. Testes

Mesma estratégia da fatia anterior, que está funcionando:

| Camada | Como |
|---|---|
| service | unitário, repository fake, sem banco |
| router | integração, `TestClient` + Postgres com schema vindo das migrações |
| migrações | exercitadas a cada execução da suíte |
| mappers e hooks | vitest |

**Casos que não podem faltar:** `GET /profiles/scouts/{id}` com id de atleta → 404 (e a
recíproca); `PUT /profiles/me` de um scout rejeitando campo de atleta → 422; `register` com
cada um dos três papéis criando a tabela certa; e a atomicidade preservada nos três.

`getProfilePath` recebe teste próprio — é função pura e é o ponto que a Q6 existe para
proteger.

---

## 8. Fora de escopo

- Upload de avatar (a coluna existe nos três; o endpoint não).
- Validação de dígito verificador de CNPJ.
- Troca de papel após o cadastro — `role` é imutável (§13 da spec de origem).
- Busca e filtros por papel (M3).
- Seguir/salvar (fatia 3 da spec anterior) e videoteca (fatia 2).
