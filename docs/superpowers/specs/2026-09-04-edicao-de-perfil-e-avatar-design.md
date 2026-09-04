# Edição de Perfil e Avatar

**Data:** 2026-09-04
**Status:** Aprovado
**Continua:** `docs/superpowers/specs/2026-09-03-f2-perfis-scout-clube-design.md`

---

## 1. Por que esta fatia existe

Os três perfis existem e são legíveis, mas **ninguém consegue preencher os próprios dados**.
`PUT /profiles/me` já aceita todos os campos de cada papel desde a fatia anterior — o que
nunca foi construído é a tela. Na prática, todo perfil em produção está vazio: 17 atletas
com posição, altura e data de nascimento nulas.

Faltam também duas coisas que não existem no domínio:

- **Avatar.** A coluna `avatar_path` existe nos três perfis desde que foram criados, mas não
  há endpoint de upload — foi declarado fora de escopo nas duas fatias anteriores.
- **Histórico de clubes do atleta.** O modelo tem apenas `current_club`, um texto único.

---

## 2. Decisões

| # | Decisão | Alternativas descartadas | Razão |
|---|---|---|---|
| E1 | Histórico de clubes como **texto livre** | Tabela `athlete_club_history`; array JSON | Entrega agora, com zero modelagem. Custo aceito: quando virar estruturado, será preciso parsear o que os atletas escreveram ou pedir que reescrevam |
| E2 | Página própria em `/profiles/me/edit` | Edição inline no perfil; modal | O formulário de atleta tem 10 campos; não cabe inline sem duplicar cada bloco em modo leitura e edição nos três papéis, complicando o `ProfileShell` recém-extraído |
| E3 | Upload de avatar simples, sem corte | Corte e redimensionamento no cliente e servidor | Entrega a funcionalidade nos três papéis sem biblioteca de crop nem processamento de imagem. O enquadramento fica com CSS |
| E4 | Um endpoint de avatar para os três papéis | Um por papel | O papel vem do JWT, como já acontece em `PUT /profiles/me`. Três endpoints idênticos seriam duplicação |
| E5 | Limite de 2 MB e apenas `jpeg`/`png`/`webp` | Sem limite; aceitar qualquer imagem | Sem limite, um avatar de 8 MB é baixado em cada card do feed. Os três formatos cobrem o uso real |

---

## 3. Modelo de dados

### 3.1 Migração — `athlete_profiles.club_history`

| Coluna | Tipo | Nulo |
|---|---|---|
| `club_history` | text | sim |

Texto livre multilinha (decisão E1). Sem backfill: os 17 perfis existentes ficam com `NULL`.

Nada muda em `scout_profiles` e `club_profiles` — seus campos já cobrem o que cada papel
tem a dizer.

### 3.2 `avatar_path`

Já existe nos três. Passa a ser **escrito pelo endpoint de upload**, não pelo `PUT`
genérico — enviar `avatar_path` como campo de texto no update deve ser rejeitado, porque o
caminho é derivado do arquivo gravado, não escolhido pelo cliente.

---

## 4. Contrato HTTP

### 4.1 Upload de avatar

```
POST /api/v1/profiles/me/avatar     multipart/form-data, campo `file`
```

Grava via `StorageBackend` em `avatars/{user_id}{ext}`, atualiza `avatar_path` do perfil do
papel do autenticado, e devolve o perfil atualizado no mesmo formato de `GET /profiles/me`
(`{ role, profile }`).

| Caso | Resposta |
|---|---|
| Tipo fora de `image/jpeg`, `image/png`, `image/webp` | 422 |
| Arquivo acima de 2 MB | 422 |
| Usuário sem perfil do seu papel | 404 |
| Sem JWT | 401 |

```
DELETE /api/v1/profiles/me/avatar
```

Remove o arquivo pelo `StorageBackend` e zera `avatar_path`. Idempotente: sem avatar, 204.

**Substituir avatar apaga o anterior.** Sem isso, cada troca deixa um arquivo órfão em disco
para sempre.

### 4.2 Servir o arquivo

O `main.py` já monta `StaticFiles` em `/api/v1/uploads`. `avatar_path` é devolvido como
`avatar_url` relativo (`/uploads/avatars/…`), e o front concatena com `VITE_API_PATH`, que é
a convenção já usada para clipes e thumbnails.

### 4.3 `club_history`

Entra em `AthleteProfileResponse` e `AthleteProfileUpdate`. Nenhuma rota nova.

---

## 5. Frontend

### 5.1 Página de edição

`/profiles/me/edit`, dentro de `PrivateRoute`. Descobre o papel por `GET /profiles/me`
(polimórfico) e renderiza o formulário daquele papel:

| Papel | Campos |
|---|---|
| Atleta | posição, data de nascimento, altura, pé dominante, cidade, estado, clube atual, **histórico de clubes**, bio, status |
| Scout | organização, credencial, cidade, estado, bio |
| Clube | razão social, CNPJ, categorias, cidade, estado, bio |

Salva com `PUT /profiles/me`, envia **apenas os campos alterados** — o backend faz update
parcial e enviar tudo sobrescreveria com valores idênticos sem necessidade.

O `useMyProfile`, previsto na fatia anterior e nunca construído, nasce aqui.

### 5.2 Avatar

Componente próprio na página de edição: mostra o avatar atual (ou a inicial), botão para
escolher arquivo, e botão para remover quando houver. Valida tipo e tamanho **no cliente
também**, para dar erro imediato em vez de esperar o 422 — mas a validação do servidor é a
que vale.

`ProfileShell` passa a exibir a imagem quando `avatarUrl` existir, caindo para a inicial do
nome quando não.

### 5.3 Como se chega lá

Botão "Editar perfil" em dois lugares: no próprio perfil, visível apenas para o dono
(comparando o `userId` da rota com o do `localStorage`), e no modal do header ao lado de
"Ver meu perfil".

---

## 6. Testes

Mesma estratégia das fatias anteriores.

**Backend, casos que não podem faltar:** upload rejeita tipo inválido (422); rejeita acima de
2 MB (422); substituir avatar **apaga o arquivo anterior**; `DELETE` sem avatar é idempotente;
`avatar_path` enviado no `PUT /profiles/me` é rejeitado; `club_history` persiste e volta no
`GET`; upload por scout e por clube grava no perfil certo.

**Frontend:** o formulário envia apenas campos alterados; validação de tipo e tamanho antes do
envio; `ProfileShell` mostra imagem quando há `avatarUrl` e inicial quando não; "Editar perfil"
aparece para o dono e **não** aparece para visitante.

---

## 7. Fora de escopo

- Corte e redimensionamento de imagem (E3).
- Histórico de clubes estruturado (E1) — quando entrar, migrar o texto livre é trabalho próprio.
- Validação de dígito verificador de CNPJ, que segue como texto livre.
- Troca de papel após o cadastro — `role` continua imutável.
- Avatar em qualquer lugar além do perfil e da edição; feed e busca ficam para suas fatias.
