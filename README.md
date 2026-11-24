# SmartScout 🎯

> Plataforma de análise automatizada de vídeos esportivos com Inteligência Artificial e ecossistema de recrutamento que conecta **Atletas**, **Scouts (Olheiros)** e **Clubes**. Envie uma partida (arquivo local ou Google Drive), selecione o jogador pelo número da camisa e receba os clipes dos seus lances em tempo real para baixar, publicar no feed e participar de peneiras.

---

## Sumário

- [SmartScout 🎯](#smartscout-)
  - [Sumário](#sumário)
  - [Sobre o projeto](#sobre-o-projeto)
  - [Tecnologias](#tecnologias)
    - [Backend (API REST, Tempo Real \& Persistência)](#backend-api-rest-tempo-real--persistência)
    - [Worker de Visão Computacional \& IA](#worker-de-visão-computacional--ia)
    - [Frontend](#frontend)
  - [Arquitetura e Modelo de Dados](#arquitetura-e-modelo-de-dados)
    - [Diagrama de Arquitetura (PI VI)](#diagrama-de-arquitetura-pi-vi)
    - [Modelo Relacional do Banco de Dados (DER)](#modelo-relacional-do-banco-de-dados-der)
  - [Funcionalidades](#funcionalidades)
    - [Pipeline de Vídeo \& Visão Computacional](#pipeline-de-vídeo--visão-computacional)
    - [Perfis Multi-Papel (`ATHLETE`, `SCOUT`, `CLUB`)](#perfis-multi-papel-athlete-scout-club)
    - [Feed \& Descoberta](#feed--descoberta)
    - [Oportunidades (Peneiras)](#oportunidades-peneiras)
    - [Mensageria / Chat Interno](#mensageria--chat-interno)
  - [Pré-requisitos](#pré-requisitos)
  - [Instalação e execução](#instalação-e-execução)
    - [Opção 1 — Com Docker Compose (Recomendado)](#opção-1--com-docker-compose-recomendado)
    - [Opção 2 — Execução Local (Desenvolvimento Manual)](#opção-2--execução-local-desenvolvimento-manual)
  - [Variáveis de ambiente](#variáveis-de-ambiente)
    - [Backend — `backend/.env`](#backend--backendenv)
    - [Frontend — `frontend/.env`](#frontend--frontendenv)
  - [Estrutura de pastas](#estrutura-de-pastas)
  - [Fluxo da aplicação](#fluxo-da-aplicação)
    - [1. Pipeline de Análise de Vídeo e Clipes (HITL)](#1-pipeline-de-análise-de-vídeo-e-clipes-hitl)
    - [2. Plataforma Social, Peneiras e Chat](#2-plataforma-social-peneiras-e-chat)
  - [Rotas da API (`/api/v1`)](#rotas-da-api-apiv1)
    - [Autenticação — `/api/v1/auth`](#autenticação--apiv1auth)
    - [Jobs \& Vídeos — `/api/v1/jobs` e `/api/v1/videos`](#jobs--vídeos--apiv1jobs-e-apiv1videos)
    - [Clipes — `/api/v1/clips`](#clipes--apiv1clips)
    - [Perfis — `/api/v1/profiles`](#perfis--apiv1profiles)
    - [Feed — `/api/v1/feed`](#feed--apiv1feed)
    - [Oportunidades (Peneiras) — `/api/v1/opportunities`](#oportunidades-peneiras--apiv1opportunities)
    - [Mensageria \& Chat — `/api/v1/messages`](#mensageria--chat--apiv1messages)
    - [Uploads — `/api/v1/uploads`](#uploads--apiv1uploads)
  - [Testes, Qualidade de Código e Benchmark](#testes-qualidade-de-código-e-benchmark)
  - [Licença](#licença)

---

## Sobre o projeto

O **SmartScout** surgiu para eliminar o trabalho manual de analistas, treinadores e atletas na edição de partidas inteiras para destacar lances individuais. Na evolução para o **PI VI**, a aplicação foi reestruturada em uma arquitetura modular e distribuída, expandindo-se de um extrator de clipes para uma plataforma completa de **scouting e conexão esportiva**.

O sistema apoia-se em dois pilares principais:

1. **Extração Inteligente de Lances (HITL — *Human-in-the-Loop*)**:
   - O usuário envia o vídeo localmente ou importa direto do **Google Drive** (com suporte a recorte por tempo/*trim* via preview em streaming HTTP Range).
   - O worker assíncrono executa um **Fast Scan** (ou **Deep Scan** sob demanda) combinando detecção **YOLO**, leitura numérica especializada + *cross-check* via **EasyOCR** e extração de cor predominante do uniforme no espaço **LAB**.
   - Após a confirmação visual do atleta candidato na interface, o pipeline executa o rastreamento contínuo de jogadores (**DeepSort**), detecção da bola e análise cinemática para recortar automaticamente os clipes em MP4, entregando-os em tempo real via **Server-Sent Events (SSE)**.

2. **Ecossistema Esportivo Multi-Papel**:
   - Perfis dedicados para **Atletas** (`ATHLETE`), **Scouts** (`SCOUT`) e **Clubes** (`CLUB`).
   - **Feed** paginado com filtros avançados (posição, idade, disponibilidade e busca) e curtidas em clipes publicados.
   - Gestão e candidatura em **Oportunidades (Peneiras)** presenciais ou online com controle automático de elegibilidade e vagas.
   - **Chat 1:1 em tempo real** via **WebSocket** com confirmação de leitura e contador de mensagens não lidas.

---

## Tecnologias

### Backend (API REST, Tempo Real & Persistência)
| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.11+ | Linguagem principal da API e do Worker |
| FastAPI | 0.133.1 | Framework web REST, SSE e WebSockets |
| SQLModel + SQLAlchemy | 0.0.37 / 2.0.48 | ORM, modelos relacionais e validação |
| Alembic | 1.13+ | Migrações versionadas do schema PostgreSQL |
| PostgreSQL | 16 (Supabase em prod) | Banco de dados relacional principal |
| Celery + Redis | 5.3+ / 7-alpine | Fila assíncrona de jobs de vídeo e política de retenção |
| Python-Jose + Bcrypt | 3.3 / 4.0+ | Autenticação JWT, hash de senhas e cifra de tokens OAuth |
| HTTPX | 0.27+ | Cliente HTTP streaming (integração Google Drive API v3) |
| Resend | 2.29.0 | Envio transacional de e-mails (recuperação de senha) |
| Uvicorn + WebSockets | 0.41.0 / 16.0 | Servidor ASGI e comunicação bidirecional do chat |

### Worker de Visão Computacional & IA
| Tecnologia | Versão | Uso |
|---|---|---|
| PyTorch | 2.7.1+cu118 | Base de inferência acelerada por GPU (CUDA 11.8) |
| Ultralytics (YOLOv8) | 8.0+ | Detecção de jogadores (`yolov8s.pt`), dígitos (`best.pt`) e bola (`ball_tracker.pt`) |
| DeepSort Realtime | 1.3+ | Rastreamento multi-objeto contínuo |
| EasyOCR | 1.7+ | *Cross-check* e reforço óptico para leituras de baixa confiança do YOLO |
| OpenCV + Supervision | 4.8+ / 0.18+ | Processamento de frames, geometria e distância de cor (LAB) |
| FFmpeg (`imageio-ffmpeg`) | 0.6+ | Normalização automática para H.264 e geração de clipes MP4 |

### Frontend
| Tecnologia | Versão | Uso |
|---|---|---|
| React | 19.2 | Biblioteca de construção da interface |
| TypeScript | 5.9 | Tipagem estática |
| Vite | 7.3 | Build tool e dev server |
| TanStack React Query | 5.102 | Cache de requisições, paginação por cursor e estado assíncrono |
| React Router DOM | 7.13 | Roteamento SPA com `PrivateRoute` e `RoleRoute` |
| React Easy Crop | 6.2 | Recorte interativo de foto de perfil (avatar) |
| RC Slider | 11.1 | Slider de corte temporal (*trim*) de vídeos |
| Lucide React | 0.577 | Conjunto de ícones |
| Vitest + Testing Library | 3.2 / 16.3 | Suíte de testes unitários e de componentes |

---

## Arquitetura e Modelo de Dados

### Diagrama de Arquitetura (PI VI)

![Diagrama de Arquitetura do SmartScout — PI VI](./docs/arquitetura_pi_vi.png)

> Versão vetorial de alta resolução disponível em [`docs/arquitetura_pi_vi.svg`](./docs/arquitetura_pi_vi.svg). Mais detalhes sobre a reestruturação modular base podem ser consultados em [`docs/F0-reestruturacao-explicado.md`](./docs/F0-reestruturacao-explicado.md).

A arquitetura é organizada em **4 camadas principais** com separação estrita de responsabilidades:

1. **Camada de Interface (`frontend/src/`)**:
   - **Módulo Público**: Landing page, login, cadastro multi-papel (`ATHLETE`, `SCOUT`, `CLUB`) e recuperação de senha.
   - **App Core (Pipeline de Vídeo & Clipes)**: upload local ou seleção via **Google Picker OAuth**, player com recorte (*trim*), acompanhamento em tempo real via **SSE (`EventSource`)**, seleção HITL de candidatos (com opção de **Deep Scan**), download em lote e publicação no feed.
   - **Módulos Sociais & Plataforma**: `features/feed`, `features/profiles`, `features/opportunities` e `features/messaging`, apoiados por `httpClient.ts` + **TanStack Query** e um cliente **WebSocket** dedicado para o chat em tempo real.

2. **Camada de Backend (`backend/app/`)**:
   - Container leve (`api:8000`) **sem dependências de PyTorch/CUDA** — nunca carrega modelos de ML em memória.
   - **Infraestrutura transversal (`core/`)**: configurações, conexão SQLModel, dependências JWT, segurança (bcrypt/JWT/cifra AES-like + HMAC para tokens OAuth do Drive), tratamento único de `DomainError`, `StorageBackend` e envio de e-mail via **Resend**.
   - **Módulos de domínio (`modules/`)**: `identity`, `clips`, `profiles`, `feed`, `opportunities` e `messaging`, cada um encapsulando seus próprios modelos, schemas, repositórios/serviços e rotas sob `/api/v1`.

3. **Mensageria Assíncrona & Persistência**:
   - **Redis 7 + Celery (`celery_app.py`)**: desacopla o servidor HTTP do processamento pesado de vídeo (`download_and_process_drive_video`, `run_fast_scan`, `run_deep_scan`, `run_full_tracking` e `run_retention_policy`), configurado com `task_acks_late=True`, `task_reject_on_worker_lost=True`, retries com backoff exponencial (até 3x) e `worker_max_tasks_per_child=1` para liberar VRAM após cada tarefa.
   - **PostgreSQL (gerido via Alembic)**: fonte única da verdade para usuários, perfis, status dos jobs (consumidos pelo endpoint SSE), candidatos, clipes, curtidas, peneiras e mensagens.
   - **Armazenamento Compartilhado (`uploads/`)**: abstraído via `StorageBackend`, montado em volume compartilhado entre `api` e `worker` para vídeos enviados, clipes/thumbnails gerados e avatares servidos em `/api/v1/uploads`.

4. **Worker Assíncrono & Pipeline de IA (`ml/`) + Serviços Externos**:
   - Container dedicado (`Dockerfile.worker` baseado em `nvidia/cuda:11.8.0-runtime-ubuntu22.04`) que importa `ml/` sob demanda (*lazy import*), normaliza codecs incompatíveis (ex.: AV1/VP9) para H.264 via FFmpeg, executa o `VideoPipeline` em duas fases e retoma automaticamente jobs interrompidos ao subir (`worker_ready`).
   - Integrações externas com **Google Drive API v3** (validação de metadados, proxy HTTP Range para preview e download em streaming no worker) e **Resend API** para e-mails transacionais.

### Modelo Relacional do Banco de Dados (DER)

![Modelo Relacional do Banco de Dados (DER) — SmartScout](./docs/database_schema.png)

> Versão vetorial disponível em [`docs/database_schema.svg`](./docs/database_schema.svg).

O schema `public` no PostgreSQL é versionado integralmente pelo **Alembic** (`15 tabelas` + `alembic_version`), divididas em 5 domínios:
- **Identidade**: `users` (com `role` enum `ATHLETE`/`SCOUT`/`CLUB`), `password_reset_tokens`
- **Perfis (1:1 com `users`)**: `athlete_profiles`, `scout_profiles`, `club_profiles`
- **Vídeo, IA & Clipes**: `videos`, `processing_jobs`, `candidates`, `clips`, `clip_likes`
- **Oportunidades (Peneiras)**: `opportunities`, `opportunity_applications`
- **Mensageria**: `conversations`, `messages`

---

## Funcionalidades

### Pipeline de Vídeo & Visão Computacional
- **Upload local ou via Google Drive**: envio em streaming (chunks de 4 MB) ou importação direta via Google Picker OAuth com proxy HTTP Range (`206 Partial Content`) para pré-visualização instantânea.
- **Corte temporal (*trim*) e normalização de codec**: seleção de trecho inicial/final antes da análise e conversão automática para H.264 via FFmpeg quando necessário.
- **Fast Scan & Deep Scan (Refinamento)**: varredura inicial rápida (1 frame a cada 30) ou aprofundada sob demanda (1 frame a cada 10) combinando `best.pt` (YOLO especialista em números), validação/reforço **EasyOCR** para leituras de baixa confiança e cor predominante do uniforme no espaço LAB.
- **Seleção HITL (*Human-in-the-Loop*)**: exibição dos candidatos detectados com foto de confirmação, número e cor da camisa antes do processamento completo.
- **Tracking de Jogador, Bola e Eventos Cinemáticos**: rastreamento contínuo (`YoloDetector` + `BallDetector` + `PlayerTracker` + `BallTracker`), detecção de proximidade/toque na bola (`BallEventDetector`) e análise cinemática (`KinematicAnalyzer`) para gerar clipes precisos.
- **Acompanhamento em tempo real (SSE) & Download em lote**: exibição progressiva dos clipes conforme são gravados no disco, download individual ou em lote e histórico organizado por data.
- **Política de retenção automática (14 dias)**: rotina `run_retention_policy` remove vídeos brutos, thumbnails de candidatos e clipes `TEMPORARY` expirados, preservando clipes `PUBLISHED`.

### Perfis Multi-Papel (`ATHLETE`, `SCOUT`, `CLUB`)
- **Cadastro segmentado**: escolha do papel no registro com provisionamento atômico do perfil correspondente na mesma transação.
- **Páginas públicas dedicadas**:
  - **Atleta (`/athletes/:userId`)**: posição, altura, pé dominante, idade calculada, clube atual, histórico de clubes, disponibilidade e videoteca pública.
  - **Scout (`/scouts/:userId`)**: organização, credencial, cidade/estado e biografia.
  - **Clube (`/clubs/:userId`)**: razão social, CNPJ, categorias atendidas (`SUB_15`, `SUB_17`, `SUB_20`, `PROFISSIONAL`), localização e bio.
- **Edição unificada (`/profiles/me/edit`) & Upload de Avatar**: recorte interativo da imagem no frontend (`AvatarCropModal`) com armazenamento em `uploads/avatars`.

### Feed & Descoberta
- **Publicação de clipes**: atletas podem publicar ou despublicar clipes no feed diretamente do histórico de análises.
- **Feed paginado por cursor**: ordenação cronológica reversa, busca textual e filtros por posição, disponibilidade e faixa etária do atleta.
- **Interação**: curtidas em clipes (`clip_likes`) e acesso direto ao perfil público do atleta ou ao chat.

### Oportunidades (Peneiras)
- **Gestão por Clubes e Scouts**: criação, edição, cancelamento e exclusão de peneiras presenciais (`PRESENCIAL`) ou online (`ONLINE`), com definição de data do evento, prazo de inscrição, faixa etária, posições aceitas e limite de vagas.
- **Inscrição de Atletas**: validação automática de elegibilidade (idade e posição), proteção transacional (`FOR UPDATE`) contra disputa pela última vaga e cancelamento de inscrição enquanto `PENDENTE`.
- **Avaliação e Privacidade**: organizadores aprovam ou recusam candidatos (`PENDENTE` → `APROVADA` / `RECUSADA`); o `meeting_url` de peneiras online é revelado apenas ao organizador e aos atletas aprovados.

### Mensageria / Chat Interno
- **Conversas 1:1**: criação idempotente de conversa diretamente a partir de qualquer perfil público.
- **Tempo real via WebSocket (`/api/v1/messages/ws`)**: entrega instantânea de novas mensagens (`new_message`), recibos de leitura (`conversation_read`), paginação retroativa (`before`) e contador global de mensagens não lidas no cabeçalho.

---

## Pré-requisitos

- **Docker e Docker Compose** (para execução recomendada com containers isolados)
- Ou, para execução local manual:
  - **Python 3.11+**
  - **Node.js 20+** (ou 18+) e **npm**
  - **PostgreSQL 16** (ou projeto no **Supabase**)
  - **Redis 7** (broker do Celery)
  - **FFmpeg** instalado no sistema (necessário para o worker converter codecs e fatiar clipes)
  - **GPU NVIDIA com CUDA 11.8+** (altamente recomendado para o worker de IA)
- Conta no [Resend](https://resend.com) para envio de e-mails de redefinição de senha
- *(Opcional)* Projeto no Google Cloud com **Google Drive API** e **Google Picker API** habilitados para importação via Google Drive

---

## Instalação e execução

### Opção 1 — Com Docker Compose (Recomendado)

O `docker-compose.yml` na raiz orquestra todos os serviços do sistema: `redis`, `api` (FastAPI sem PyTorch), `worker` (Celery + PyTorch/CUDA), `web` (Vite/React) e `postgres-test` (banco isolado para testes de integração).

1. **Configure as variáveis de ambiente** em `backend/.env` e `frontend/.env` conforme a seção [Variáveis de ambiente](#variáveis-de-ambiente).

2. *(Opcional — GPU NVIDIA)* Caso esteja em uma máquina com GPU NVIDIA e NVIDIA Container Toolkit, descomente o bloco `deploy.resources.reservations.devices` do serviço `worker` no arquivo [`docker-compose.yml`](./docker-compose.yml).

3. **Suba os containers a partir da raiz do repositório:**
   ```bash
   docker compose up --build
   ```

4. **Aplique as migrações do banco de dados:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

Serviços disponíveis após subir:
- **Frontend**: `http://localhost:5173`
- **API FastAPI**: `http://localhost:8000`
- **Documentação interativa (Swagger)**: `http://localhost:8000/docs`

---

### Opção 2 — Execução Local (Desenvolvimento Manual)

#### 1. Backend (API)

```bash
cd backend

# Crie e ative o ambiente virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
# source venv/bin/activate

# Instale apenas as dependências da API (leve, sem PyTorch)
pip install -r requirements/api.txt
```

Configure o arquivo `backend/.env`, aplique as migrações e suba a API:

```bash
# Ainda dentro de backend/
alembic upgrade head
python -m uvicorn app.main:app --reload
```

> **Importante:** O schema é gerido exclusivamente por **Alembic** (não há `create_all` no startup). Sempre que alterar um model, gere e aplique a migração:
> `alembic revision --autogenerate -m "descricao"` && `alembic upgrade head`.

#### 2. Redis & Worker Celery (Visão Computacional)

Em outro terminal, garanta um servidor **Redis** rodando em `localhost:6379` (ex.: `docker compose up -d redis`), instale as dependências de ML e inicie o worker com a raiz do repositório no `PYTHONPATH` (para que `app.*` e `ml.*` sejam importáveis):

```bash
cd backend
pip install -r requirements/worker.txt
```

```bash
# Linux / macOS (a partir de backend/, apontando PYTHONPATH para backend e raiz)
PYTHONPATH=.:.. celery -A app.celery_app worker --concurrency=1 --max-tasks-per-child=1 --loglevel=info

# Windows PowerShell (Celery requer --pool=solo no Windows)
$env:PYTHONPATH=".;.."; celery -A app.celery_app worker --pool=solo --loglevel=info
```

#### 3. Frontend

```bash
cd frontend
npm install
```

Configure o arquivo `frontend/.env` e inicie o servidor de desenvolvimento:

```bash
npm run dev
```

A interface ficará disponível em `http://localhost:5173`.

---

## Variáveis de ambiente

### Backend — `backend/.env`

```env
# Banco de dados PostgreSQL (ex.: Supabase ou instância local)
DATABASE_URL=postgresql://usuario:senha@host:5432/smartscout

# Autenticação JWT e cifra de tokens do Google Drive no broker
JWT_SECRET_KEY=sua_chave_secreta_forte_aqui

# Broker Celery (no Docker Compose é sobrescrito para redis://redis:6379/0)
REDIS_URL=redis://localhost:6379/0

# Limite máximo de upload/importação de vídeo em MB (opcional; padrão: 20048)
MAX_VIDEO_SIZE_MB=20048

# Envio de e-mails (Resend)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
FRONTEND_URL=http://localhost:5173

# Banco descartável para testes de integração (o nome do banco DEVE terminar em _test)
TEST_DATABASE_URL=postgresql://smartscout:smartscout@localhost:5433/smartscout_test
```

### Frontend — `frontend/.env`

```env
# URL base da API REST e WebSocket
VITE_API_PATH=http://localhost:8000/api/v1

# Opcional — necessários apenas para habilitar a importação via Google Drive Picker
VITE_GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
VITE_GOOGLE_API_KEY=sua_google_api_key
VITE_GOOGLE_APP_ID=seu_numero_de_projeto_google
```

---

## Estrutura de pastas

```
PI_VI_ES_TIME-6/
├── backend/
│   ├── app/
│   │   ├── core/                        # Infraestrutura transversal compartilhada
│   │   │   ├── config.py                # Paths, JWT_SECRET_KEY e limites de upload
│   │   │   ├── database.py              # Engine SQLModel e get_session()
│   │   │   ├── deps.py                  # Dependência de autenticação (get_current_user)
│   │   │   ├── email.py                 # Envio transacional de e-mails (Resend)
│   │   │   ├── exceptions.py            # Hierarquia DomainError → HTTP status único
│   │   │   ├── security.py              # Bcrypt, JWT e cifra autenticada do token Drive
│   │   │   └── storage.py               # StorageBackend / LocalStorageBackend
│   │   ├── modules/                     # Módulos organizados por domínio
│   │   │   ├── identity/                # Auth, User (multi-papel) e PasswordResetToken
│   │   │   ├── clips/                   # Vídeos, Jobs, Candidatos, Clipes, Tasks Celery e Drive
│   │   │   ├── profiles/                # Perfis 1:1 (Athlete, Scout, Club) e Upload de Avatar
│   │   │   ├── feed/                    # Feed paginado de clipes publicados e curtidas
│   │   │   ├── opportunities/           # Peneiras (CRUD, elegibilidade, inscrições)
│   │   │   └── messaging/               # Chat 1:1 (REST + ConnectionManager WebSocket)
│   │   ├── celery_app.py                # Instância Celery compartilhada entre API e Worker
│   │   └── main.py                      # Montagem de routers, CORS, StaticFiles e erro global
│   ├── alembic/                         # Migrações versionadas do banco de dados
│   ├── requirements/                    # base.txt · api.txt · worker.txt · dev.txt
│   ├── tests/                           # Testes unitários e de integração da API/backend
│   ├── uploads/                         # Volume compartilhado (videos/, clips/, avatars/)
│   ├── Dockerfile                       # Imagem leve da API (sem PyTorch)
│   └── Dockerfile.worker                # Imagem CUDA 11.8 do Worker de IA
│
├── ml/                                  # Pacote de Visão Computacional & Pipeline de IA
│   ├── detector.py                      # YoloDetector e BallDetector
│   ├── models/                          # Pesos treinados (best.pt, ball_tracker.pt)
│   └── scripts/
│       ├── video_pipeline.py            # Orquestrador Fast/Deep Scan e Full Tracking
│       ├── jersey_reader.py             # Leitor YOLO especialista em números de camisa
│       ├── ocr_reader.py                # Validação/reforço EasyOCR para leituras de baixa confiança do YOLO
│       ├── color_extractor.py           # Extração e comparação de cor de uniforme (LAB)
│       ├── ball_event_detector.py       # Proximidade e toque na bola
│       ├── kinematic_analyzer.py        # Detecção de anomalias de velocidade/aceleração
│       ├── clip_writer.py               # Recorte e escrita dos clipes MP4
│       └── trackers/                    # PlayerTracker (DeepSort) e BallTracker
│
├── frontend/
│   ├── src/
│   │   ├── components/                  # Header, PrivateRoute, RoleRoute, ClipCard, PlayerCard, Grid
│   │   ├── features/                    # Módulos de domínio no front (hooks, api, mappers, types)
│   │   │   ├── clips/                   # Hook useGoogleDrivePicker
│   │   │   ├── feed/                    # Hooks useFeed e useToggleLike
│   │   │   ├── messaging/               # Hooks de conversas, unread-count e useMessagingSocket
│   │   │   ├── opportunities/           # Queries e mutations de peneiras
│   │   │   └── profiles/                # Formulários, abas de perfil e AvatarCropModal
│   │   ├── layouts/                     # MainLayout
│   │   ├── pages/                       # Landing, Auth, Input, Processing, Feed, Profiles, Inbox, Opportunities
│   │   ├── services/                    # api.ts (fluxo legado de auth/jobs/clips)
│   │   └── shared/lib/                  # httpClient.ts, queryClient.ts, profileRoutes.ts, userRole.ts
│   └── Dockerfile
│
├── docs/                                # Diagramas e documentação arquitetural
│   ├── arquitetura_pi_vi.png            # Diagrama de arquitetura (PNG)
│   ├── arquitetura_pi_vi.svg            # Diagrama de arquitetura (SVG)
│   ├── database_schema.png              # Diagrama entidade-relacionamento (PNG)
│   ├── database_schema.svg              # Diagrama entidade-relacionamento (SVG)
│   └── F0-reestruturacao-explicado.md   # Guia explicativo da modularização do backend
│
├── benchmark/                           # Script de benchmark de performance do modelo de IA
├── tests/                               # Suíte de testes unitários e de integração do pipeline ML
├── docker-compose.yml                   # Orquestração completa (redis, api, worker, web, postgres-test)
└── run_all_tests.py                     # Orquestrador de testes (ML pytest, ESLint, tsc, benchmark)
```

---

## Fluxo da aplicação

### 1. Pipeline de Análise de Vídeo e Clipes (HITL)

```
Usuário autenticado acessa /app
        │
        ├─ Upload local (MP4/MOV/AVI/WebM) ──► POST /api/v1/jobs/ (PENDING)
        │
        └─ Google Picker OAuth ──────────────► POST /api/v1/jobs/import/google-drive
                                                       │
                                                       ▼
                                               DOWNLOADING (streaming → disco)
                                                       │
                                                       ▼
                                       CONVERTING (H.264, se necessário)
                                                       │
                                                       ▼
                                       FAST_SCAN (YOLO + Cor + OCR leve)
                                                       │
                                                       ▼
                                       WAITING_USER (Seleção visual HITL)
                                        │              │
                     [Não encontrou?] ──┘              └── [Confirmou atleta]
                            │                                      │
                            ▼                                      ▼
                POST /jobs/{id}/refine                  POST /jobs/{id}/confirm
                     (DEEP_SCAN)                                   │
                                                                   ▼
                                                TRACKING → EXTRACTING → COMPLETED
                                                (SSE exibe clipes em tempo real)
                                                                   │
                                                                   ▼
                                                /clips-history: Download em lote ou
                                                Publicar no Feed (TEMPORARY → PUBLISHED)
```

### 2. Plataforma Social, Peneiras e Chat

```
Cadastro multi-papel (/signup: ATHLETE | SCOUT | CLUB)
        │
        ├──► /feed ──────────────────► Filtrar clipes, curtir e visitar perfis
        │
        ├──► /athletes/:id           ► Ver histórico, videoteca e editar (/profiles/me/edit)
        │    /scouts/:id  /clubs/:id ► Iniciar conversa 1:1 ──► /messages (REST + WebSocket)
        │
        └──► /opportunities
               ├─ ATHLETE ───────────► Filtrar elegíveis, candidatar-se e ver /opportunities/applications
               └─ CLUB / SCOUT ──────► Criar/editar peneiras (/opportunities/new, /mine) e aprovar inscritos
```

---

## Rotas da API (`/api/v1`)

### Autenticação — `/api/v1/auth`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/register` | Cadastro multi-papel (`ATHLETE`, `SCOUT`, `CLUB`) com criação atômica de perfil e retorno de JWT |
| `POST` | `/login` | Login com e-mail/senha e geração de token JWT |
| `POST` | `/logout` | Encerramento de sessão autenticada (`204`) |
| `POST` | `/forgot-password` | Solicita envio de token de redefinição de senha via Resend |
| `POST` | `/reset-password` | Redefine a senha utilizando o token recebido |

### Jobs & Vídeos — `/api/v1/jobs` e `/api/v1/videos`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/jobs/` | Upload de vídeo local em streaming + criação do job (`202`, dispara `run_fast_scan`) |
| `POST` | `/jobs/import/google-drive` | Importa vídeo do Google Drive e dispara download assíncrono (`202`, espelhada em `/videos/import/google-drive`) |
| `GET` | `/jobs/drive-preview/{file_id}` | Proxy streaming com `206 Partial Content` para preview e trim (espelhada em `/videos/drive-preview/{file_id}`) |
| `GET` | `/jobs/{job_id}/stream` | **SSE** — envia status (`DOWNLOADING`, `CONVERTING`, `FAST_SCAN`, `WAITING_USER`, `DEEP_SCAN`, `TRACKING`, `EXTRACTING`, `COMPLETED`, `ERROR`), candidatos e clipes em tempo real |
| `POST` | `/jobs/{job_id}/confirm` | Confirma o candidato escolhido (HITL) e inicia `run_full_tracking` |
| `POST` | `/jobs/{job_id}/refine` | Dispara busca aprofundada (`DEEP_SCAN`) quando o candidato não apareceu no Fast Scan |
| `DELETE` | `/jobs/{job_id}/clips` | Exclui todos os clipes de um job (e remove o vídeo original se órfão) |

### Clipes — `/api/v1/clips`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/clips/` | Lista histórico de jobs concluídos e clipes do usuário autenticado |
| `DELETE` | `/clips/{clip_id}` | Exclui um clipe específico |
| `POST` | `/clips/{clip_id}/publish` | Publica um clipe de atleta no Feed (torna-o isento da retenção de 14 dias) |
| `DELETE` | `/clips/{clip_id}/publish` | Remove o clipe do Feed e retorna para `TEMPORARY` |
| `GET` | `/clips/athletes/{user_id}` | Lista clipes públicos de um atleta para sua videoteca de perfil |

### Perfis — `/api/v1/profiles`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/profiles/me` | Retorna papel e perfil do usuário autenticado (`{ role, profile }`) |
| `PUT` | `/profiles/me` | Atualização parcial polimórfica do próprio perfil conforme o papel no JWT |
| `POST` | `/profiles/me/avatar` | Upload da imagem de avatar recortada |
| `DELETE` | `/profiles/me/avatar` | Remove o avatar atual |
| `GET` | `/profiles/athletes/{user_id}` | Perfil público de um atleta |
| `GET` | `/profiles/scouts/{user_id}` | Perfil público de um scout |
| `GET` | `/profiles/clubs/{user_id}` | Perfil público de um clube |

### Feed — `/api/v1/feed`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/feed` | Lista clipes publicados com paginação por cursor e filtros (`position`, `status`, `min_age`, `max_age`, `q`) |
| `POST` | `/feed/clips/{clip_id}/like` | Curte um clipe publicado |
| `DELETE` | `/feed/clips/{clip_id}/like` | Remove a curtida de um clipe |

### Oportunidades (Peneiras) — `/api/v1/opportunities`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/opportunities` | Lista peneiras abertas com paginação por cursor e filtros (`mode`, `state`, `position`, `eligible`, `q`) |
| `POST` | `/opportunities` | Cria uma nova peneira (restrito a `CLUB` e `SCOUT`) |
| `GET` | `/opportunities/mine` | Lista peneiras criadas pelo organizador com contagem por status |
| `GET` | `/opportunities/applications/me` | Lista candidaturas do atleta autenticado |
| `GET` | `/opportunities/{opportunity_id}` | Detalhes da peneira (exibe `meeting_url` apenas ao dono e atletas `APROVADA`) |
| `PATCH` | `/opportunities/{opportunity_id}` | Atualiza dados de uma peneira ativa do organizador |
| `POST` | `/opportunities/{opportunity_id}/cancel` | Cancela uma peneira |
| `DELETE` | `/opportunities/{opportunity_id}` | Exclui uma peneira do organizador |
| `POST` | `/opportunities/{opportunity_id}/apply` | Inscreve o atleta autenticado validando elegibilidade e vagas |
| `DELETE` | `/opportunities/{opportunity_id}/apply` | Cancela inscrição ainda em análise (`PENDENTE`) |
| `GET` | `/opportunities/{opportunity_id}/applications` | Lista atletas inscritos na peneira (dono) |
| `PATCH` | `/opportunities/{opportunity_id}/applications/{athlete_id}` | Aprova ou recusa um atleta inscrito (`APROVADA` / `RECUSADA`) |

### Mensageria & Chat — `/api/v1/messages`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/messages/conversations` | Lista conversas do usuário ordenadas pela última mensagem |
| `POST` | `/messages/conversations` | Abre ou reutiliza uma conversa 1:1 com `recipient_id` |
| `GET` | `/messages/conversations/{conversation_id}/messages` | Paginação retroativa (`before`, `limit`) das mensagens da conversa |
| `POST` | `/messages/conversations/{conversation_id}/messages` | Persiste nova mensagem e dispara push em tempo real via WebSocket |
| `POST` | `/messages/conversations/{conversation_id}/read` | Marca mensagens recebidas como lidas e notifica o remetente via WebSocket |
| `GET` | `/messages/unread-count` | Retorna o total de mensagens não lidas do usuário |
| `WS` | `/messages/ws?token=<jwt>` | Canal WebSocket para recebimento instantâneo de eventos `new_message` e `conversation_read` |

### Uploads — `/api/v1/uploads`

Servido como diretório de arquivos estáticos pelo FastAPI (`videos/`, `clips/` e `avatars/`).

---

## Testes, Qualidade de Código e Benchmark

O repositório possui suítes separadas por camada. **Importante:** as suítes `pytest` da raiz (ML/pipeline) e de `backend/tests/` (API/banco) devem ser executadas separadamente (não passe ambas no mesmo comando `pytest`, pois compartilham o nome de pacote `tests`).

```bash
# 1. Backend — Testes unitários e de integração (dentro do container api, usando postgres-test)
docker compose up -d postgres-test api
docker compose exec api pytest                        # suíte completa do backend
docker compose exec api pytest tests/unit             # apenas testes unitários (sem banco)
docker compose exec api pytest tests/integration      # testes de integração (exige postgres-test)

# 2. Pipeline de ML — Na raiz do projeto
pytest

# 3. Frontend — Testes Vitest, Typecheck e Lint
cd frontend
npm test          # executa tsc --noEmit + vitest run
npm run lint      # ESLint

# 4. Orquestrador geral (ML pytest + ESLint + tsc) e Benchmark de IA (na raiz)
python run_all_tests.py
python run_all_tests.py --benchmark caminho/do/video.mp4 10
```

---

## Licença

Consulte o arquivo [`LICENSE`](./LICENSE) para informações sobre direitos autorais e termos de uso.
