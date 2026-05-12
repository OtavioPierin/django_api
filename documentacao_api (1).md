# Documentação da API — Django REST

> Base URL: `/api/` (prefixo configurado no projeto)  
> Autenticação: **JWT Bearer Token** — inclua o header `Authorization: Bearer <access_token>` em todas as rotas protegidas.

---

## Sumário

1. [Autenticação](#1-autenticação)
2. [Categorias](#2-categorias)
3. [Produtos](#3-produtos)
4. [Imagens de Produto](#4-imagens-de-produto)
5. [Pagamentos](#5-pagamentos)
6. [Clientes](#6-clientes)
7. [Endereços](#7-endereços)
8. [Pedidos](#8-pedidos)
9. [Itens do Pedido](#9-itens-do-pedido)
10. [Avaliações](#10-avaliações)
11. [Tabelas M2M (Admin)](#11-tabelas-m2m-admin)
12. [Permissões e Roles](#permissões-e-roles)

---

## 1. Autenticação

### `POST /auth/registro/`

Cria um novo usuário e o respectivo perfil de cliente.

**Permissão:** Pública  
**Body (JSON):**

| Campo      | Tipo   | Obrigatório | Descrição                   |
|------------|--------|-------------|------------------------------|
| `username` | string | ✅          | Nome de usuário único        |
| `email`    | string | ✅          | E-mail único                 |
| `password` | string | ✅          | Mínimo 8 caracteres          |
| `nome`     | string | ✅          | Nome completo do cliente     |
| `cpf`      | string | ✅          | CPF único (formato livre)    |

**Resposta `201`:**
```json
{ "mensagem": "Usuário criado com sucesso." }
```

**Resposta `400`:** Erros de validação por campo.

---

### `POST /auth/login/`

Autentica o usuário e retorna o par de tokens JWT.

**Permissão:** Pública  
**Body (JSON):**

| Campo      | Tipo   | Descrição        |
|------------|--------|------------------|
| `username` | string | Nome de usuário  |
| `password` | string | Senha            |

**Resposta `200`:**
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

> O `access_token` contém os claims: `username`, `email`, `cliente_id`, `nome`, `role`.

---

### `POST /auth/refresh/`

Gera um novo `access_token` a partir do `refresh_token`.

**Permissão:** Pública  
**Body (JSON):**

| Campo     | Tipo   | Descrição      |
|-----------|--------|----------------|
| `refresh` | string | Refresh token  |

**Resposta `200`:**
```json
{ "access": "<novo_access_token>" }
```

**Resposta `401`:** Token inválido ou expirado.

---

### `POST /auth/logout/`

Invalida (blacklist) o refresh token, encerrando a sessão.

**Permissão:** Autenticado  
**Body (JSON):**

| Campo     | Tipo   | Descrição      |
|-----------|--------|----------------|
| `refresh` | string | Refresh token  |

**Resposta `200`:**
```json
{ "mensagem": "Logout realizado com sucesso." }
```

---

### `POST /auth/verify/`

Verifica se um `access_token` ainda é válido.

**Permissão:** Pública  
**Body (JSON):**

| Campo   | Tipo   | Descrição     |
|---------|--------|---------------|
| `token` | string | Access token  |

**Resposta `200`:** `{}` (token válido)  
**Resposta `401`:** Token inválido ou expirado.

---

## 2. Categorias

### `GET /categorias/`

Lista todas as categorias. Suporta busca por nome com `?search=<termo>`.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  { "id": 1, "nome": "Eletrônicos" }
]
```

---

### `POST /categorias/`

Cria uma nova categoria.

**Permissão:** Admin  
**Body (JSON):**

| Campo  | Tipo   | Obrigatório | Descrição              |
|--------|--------|-------------|------------------------|
| `nome` | string | ✅          | Máximo 20 caracteres   |

**Resposta `201`:** Objeto da categoria criada.

---

### `GET /categorias/{id}/`

Retorna os detalhes de uma categoria específica.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
{ "id": 1, "nome": "Eletrônicos" }
```

---

### `PUT /categorias/{id}/` · `PATCH /categorias/{id}/`

Atualiza total ou parcialmente uma categoria.

**Permissão:** Admin  
**Body:** Mesmo schema do `POST`.

---

### `DELETE /categorias/{id}/`

Remove uma categoria.

**Permissão:** Admin  
**Resposta `204`:** Sem conteúdo.

---

### `GET /categorias/{id}/produtos/`

Lista todos os produtos pertencentes à categoria.

**Permissão:** Autenticado  
**Resposta `200`:** Array de produtos no formato de card (ver [Listagem de Produtos](#get-produtos)).

---

## 3. Produtos

### `GET /produtos/`

Lista todos os produtos em formato de card (imagem principal, sem galeria). Suporta:

- `?search=<termo>` — busca por nome do produto ou nome da categoria
- `?ordering=preco` | `estoque` | `nome_produto` (prefixe com `-` para decrescente)

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "nome_produto": "Notebook X",
    "preco": "3500.00",
    "estoque": 10,
    "em_estoque": true,
    "categoria": 2,
    "categoria_nome": "Eletrônicos",
    "media_avaliacoes": 4.5,
    "imagem_principal": {
      "id": 3,
      "imagem_url": "http://example.com/media/produtos/1/foto.jpg",
      "alt": "Notebook aberto"
    }
  }
]
```

---

### `POST /produtos/`

Cria um novo produto. Imagens são gerenciadas separadamente via `/produtos/{id}/imagens/`.

**Permissão:** Gestor de estoque ou Admin  
**Body (JSON):**

| Campo         | Tipo    | Obrigatório | Descrição                     |
|---------------|---------|-------------|-------------------------------|
| `nome_produto`| string  | ✅          | Máximo 50 caracteres          |
| `preco`       | decimal | ✅          | Ex.: `"199.90"`               |
| `estoque`     | integer | ✅          | Quantidade disponível         |
| `categoria`   | integer | ✅          | ID da categoria               |

**Resposta `201`:** Objeto do produto criado.

---

### `GET /produtos/{id}/`

Retorna os detalhes completos do produto, incluindo a galeria de imagens.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
{
  "id": 1,
  "nome_produto": "Notebook X",
  "preco": "3500.00",
  "estoque": 10,
  "em_estoque": true,
  "categoria": 2,
  "categoria_nome": "Eletrônicos",
  "media_avaliacoes": 4.5,
  "imagens": [
    {
      "id": 3,
      "imagem_url": "http://example.com/media/produtos/1/foto.jpg",
      "principal": true,
      "ordem": 0,
      "alt": "Notebook aberto"
    }
  ]
}
```

---

### `PUT /produtos/{id}/` · `PATCH /produtos/{id}/`

Atualiza total ou parcialmente um produto.

**Permissão:** Gestor de estoque ou Admin  
**Body:** Mesmo schema do `POST`.

---

### `DELETE /produtos/{id}/`

Remove um produto.

**Permissão:** Gestor de estoque ou Admin  
**Resposta `204`:** Sem conteúdo.

---

### `GET /produtos/{id}/avaliacoes/`

Lista todas as avaliações de um produto.

**Permissão:** Autenticado  
**Resposta `200`:** Array de objetos de avaliação (ver [Avaliações](#10-avaliações)).

---

### `POST /produtos/{id}/reduzir-estoque/`

Reduz o estoque de um produto manualmente.

**Permissão:** Gestor de estoque ou Admin  
**Body (JSON):**

| Campo       | Tipo    | Obrigatório | Descrição                  |
|-------------|---------|-------------|----------------------------|
| `quantidade`| integer | ✅          | Valor positivo a subtrair  |

**Resposta `200`:**
```json
{ "mensagem": "Novo estoque: 7." }
```

**Resposta `400`:** Quantidade inválida ou estoque insuficiente.

---

## 4. Imagens de Produto

Rota aninhada sob `/produtos/{produto_pk}/imagens/`.

### `GET /produtos/{produto_pk}/imagens/`

Lista todas as imagens do produto, ordenadas por `ordem` e depois por `id`.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 3,
    "imagem_url": "http://example.com/media/produtos/1/foto.jpg",
    "principal": true,
    "ordem": 0,
    "alt": "Notebook aberto"
  }
]
```

---

### `POST /produtos/{produto_pk}/imagens/`

Faz upload de uma nova imagem para o produto.

**Permissão:** Gestor de estoque ou Admin  
**Content-Type:** `multipart/form-data`

| Campo       | Tipo    | Obrigatório | Descrição                                   |
|-------------|---------|-------------|---------------------------------------------|
| `imagem`    | file    | ✅          | Arquivo JPG, PNG ou WEBP, máx. 5 MB         |
| `principal` | boolean | ❌          | `true` para definir como principal          |
| `ordem`     | integer | ❌          | Posição no carrossel (padrão: 0)            |
| `alt`       | string  | ❌          | Texto alternativo (máx. 120 caracteres)     |

> A primeira imagem enviada a um produto é automaticamente marcada como principal.

**Resposta `201`:** Objeto da imagem criada.

---

### `PATCH /produtos/{produto_pk}/imagens/{id}/`

Atualiza metadados da imagem (ordem, alt, principal). Não substitui o arquivo.

**Permissão:** Gestor de estoque ou Admin

---

### `DELETE /produtos/{produto_pk}/imagens/{id}/`

Remove a imagem e seu arquivo físico do servidor.

**Permissão:** Gestor de estoque ou Admin  
**Resposta `204`:** Sem conteúdo.

---

### `POST /produtos/{produto_pk}/imagens/{id}/tornar-principal/`

Define esta imagem como principal, desmarcando automaticamente as demais.

**Permissão:** Gestor de estoque ou Admin  
**Resposta `200`:**
```json
{ "mensagem": "Imagem definida como principal." }
```

---

## 5. Pagamentos

### `GET /pagamentos/`

Lista todos os pagamentos registrados.

**Permissão:** Admin  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "metodo": "pix",
    "metodo_display": "PIX",
    "valor": "250.00"
  }
]
```

---

### `POST /pagamentos/`

Registra um novo pagamento.

**Permissão:** Autenticado  
**Body (JSON):**

| Campo    | Tipo    | Obrigatório | Descrição                                                               |
|----------|---------|-------------|-------------------------------------------------------------------------|
| `metodo` | string  | ✅          | `pix`, `cartao_credito`, `cartao_debito` ou `boleto`                    |
| `valor`  | decimal | ✅          | Valor do pagamento                                                       |

**Resposta `201`:** Objeto do pagamento criado.

---

### `GET /pagamentos/{id}/`

Retorna um pagamento específico.

**Permissão:** Autenticado

---

### `PUT /pagamentos/{id}/` · `PATCH /pagamentos/{id}/`

Atualiza um pagamento.

**Permissão:** Admin

---

### `DELETE /pagamentos/{id}/`

Remove um pagamento.

**Permissão:** Admin  
**Resposta `204`:** Sem conteúdo.

---

## 6. Clientes

### `GET /clientes/`

Lista clientes. Admins veem todos; clientes comuns veem apenas o próprio perfil.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "nome": "João Silva",
    "cpf": "123.456.789-00",
    "email": "joao@email.com",
    "role": "cliente",
    "enderecos": [...],
    "total_gasto": "1500.00",
    "pedido_mais_recente": {
      "id": 5,
      "status": "enviado",
      "data": "2024-11-10"
    }
  }
]
```

---

### `GET /clientes/{id}/`

Retorna os dados de um cliente. Clientes comuns só podem acessar o próprio perfil.

**Permissão:** Autenticado + dono ou Admin

---

### `PUT /clientes/{id}/` · `PATCH /clientes/{id}/`

Atualiza dados do cliente.

**Permissão:** Autenticado + dono ou Admin

---

### `DELETE /clientes/{id}/`

Remove um cliente.

**Permissão:** Admin  
**Resposta `204`:** Sem conteúdo.

---

### `GET /clientes/me/`

Atalho que retorna o perfil do próprio usuário autenticado, sem precisar saber o `id`.

**Permissão:** Autenticado  
**Resposta `200`:** Objeto do cliente (mesmo schema acima).

---

### `GET /clientes/{id}/pedidos/`

Lista os pedidos de um cliente. Aceita filtro opcional: `?status=enviado`.

**Permissão:** Autenticado + dono ou Admin  
**Valores válidos para `status`:** `pendente`, `processando`, `enviado`, `entregue`, `cancelado`

---

### `GET /clientes/{id}/enderecos/`

Lista os endereços de um cliente.

**Permissão:** Autenticado + dono ou Admin

---

### `GET /clientes/{id}/avaliacoes/`

Lista as avaliações feitas por um cliente.

**Permissão:** Autenticado + dono ou Admin

---

### `PATCH /clientes/{id}/alterar-role/`

Altera o papel (role) de um cliente.

**Permissão:** Admin  
**Body (JSON):**

| Campo  | Tipo   | Obrigatório | Descrição                                 |
|--------|--------|-------------|-------------------------------------------|
| `role` | string | ✅          | `cliente`, `admin` ou `estoque`           |

**Resposta `200`:**
```json
{ "mensagem": "Role de João Silva atualizado para 'estoque'." }
```

---

## 7. Endereços

Rota aninhada sob `/clientes/{cliente_pk}/enderecos/`.

### `GET /clientes/{cliente_pk}/enderecos/`

Lista os endereços do cliente.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "rua": "Rua das Flores, 123",
    "cidade": "Belo Horizonte",
    "estado": "MG",
    "cep": "30000-000"
  }
]
```

---

### `POST /clientes/{cliente_pk}/enderecos/`

Adiciona um endereço ao cliente.

**Permissão:** Autenticado  
**Body (JSON):**

| Campo    | Tipo   | Obrigatório | Descrição                     |
|----------|--------|-------------|-------------------------------|
| `rua`    | string | ✅          | Máximo 50 caracteres          |
| `cidade` | string | ✅          | Máximo 30 caracteres          |
| `estado` | string | ✅          | Sigla UF (2 caracteres)       |
| `cep`    | string | ✅          | Máximo 10 caracteres          |

**Resposta `201`:** Objeto do endereço criado.

---

### `GET /clientes/{cliente_pk}/enderecos/{id}/`

Retorna um endereço específico.

**Permissão:** Autenticado

---

### `PUT /clientes/{cliente_pk}/enderecos/{id}/` · `PATCH /clientes/{cliente_pk}/enderecos/{id}/`

Atualiza total ou parcialmente um endereço.

**Permissão:** Autenticado

---

### `DELETE /clientes/{cliente_pk}/enderecos/{id}/`

Remove um endereço.

**Permissão:** Autenticado  
**Resposta `204`:** Sem conteúdo.

---

## 8. Pedidos

### `GET /pedidos/`

Lista pedidos. Admins veem todos; clientes veem apenas os próprios. Suporta ordenação: `?ordering=data_pedido` | `valor_total` | `status`.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "cliente_nome": "João Silva",
    "pagamento_info": { "id": 2, "metodo": "pix", "metodo_display": "PIX", "valor": "250.00" },
    "data_pedido": "2024-11-10",
    "valor_total": "250.00",
    "status": "enviado",
    "status_display": "Enviado",
    "itens": [...]
  }
]
```

---

### `POST /pedidos/`

Cria um novo pedido com seus itens. O `valor_total` é calculado automaticamente. O estoque de cada produto é reduzido automaticamente.

**Permissão:** Autenticado  
**Body (JSON):**

| Campo      | Tipo    | Obrigatório | Descrição                            |
|------------|---------|-------------|--------------------------------------|
| `cliente`  | integer | ✅          | ID do cliente                        |
| `pagamento`| integer | ✅          | ID do pagamento                      |
| `senha`    | string  | ✅          | Mínimo 4 caracteres (salva em SHA-256)|
| `itens`    | array   | ✅          | Lista de itens (ver abaixo)          |

**Estrutura de cada item em `itens`:**

| Campo            | Tipo    | Obrigatório | Descrição                   |
|------------------|---------|-------------|------------------------------|
| `produto`        | integer | ✅          | ID do produto                |
| `quantidade`     | integer | ✅          | Quantidade (> 0)             |
| `preco_unitario` | decimal | ✅          | Preço no momento da compra   |

**Resposta `201`:** Objeto do pedido criado.

---

### `GET /pedidos/{id}/`

Retorna os detalhes de um pedido, incluindo todos os itens.

**Permissão:** Autenticado + dono ou Admin

---

### `PUT /pedidos/{id}/` · `PATCH /pedidos/{id}/`

Atualiza dados do pedido (ex.: status). Pedidos cancelados não podem ser alterados.

**Permissão:** Autenticado

---

### `DELETE /pedidos/{id}/`

Remove um pedido.

**Permissão:** Autenticado  
**Resposta `204`:** Sem conteúdo.

---

### `GET /pedidos/{id}/itens/`

Lista os itens de um pedido específico.

**Permissão:** Autenticado  
**Resposta `200`:** Array de itens com `produto_nome`, `produto_imagem`, `quantidade`, `preco_unitario` e `subtotal`.

---

### `POST /pedidos/{id}/cancelar/`

Cancela o pedido e devolve o estoque de todos os itens ao inventário.

**Permissão:** Autenticado (dono ou Admin)  
**Restrição:** Pedidos com status `entregue` não podem ser cancelados.  
**Resposta `200`:**
```json
{ "mensagem": "Pedido cancelado com sucesso." }
```

---

### `POST /pedidos/{id}/avancar/`

Avança o status do pedido no fluxo: `pendente` → `processando` → `enviado` → `entregue`.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
{ "mensagem": "Status atualizado.", "status": "processando" }
```

**Resposta `400`:** Se o status não puder ser avançado (ex.: já `entregue` ou `cancelado`).

---

## 9. Itens do Pedido

Rota aninhada sob `/pedidos/{pedido_pk}/itens/`.

### `GET /pedidos/{pedido_pk}/itens/`

Lista os itens de um pedido.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "produto": 3,
    "produto_nome": "Notebook X",
    "produto_imagem": "http://example.com/media/produtos/3/foto.jpg",
    "quantidade": 2,
    "preco_unitario": "3500.00",
    "subtotal": "7000.00"
  }
]
```

---

### `POST /pedidos/{pedido_pk}/itens/`

Adiciona um item ao pedido e recalcula o `valor_total` automaticamente.

**Permissão:** Autenticado  
**Body (JSON):**

| Campo            | Tipo    | Obrigatório | Descrição                         |
|------------------|---------|-------------|-----------------------------------|
| `produto`        | integer | ✅          | ID do produto                     |
| `quantidade`     | integer | ✅          | Quantidade (> 0)                  |
| `preco_unitario` | decimal | ✅          | Preço no momento da adição        |

> O estoque do produto é reduzido automaticamente ao adicionar o item.

---

### `DELETE /pedidos/{pedido_pk}/itens/{id}/`

Remove um item do pedido e recalcula o `valor_total` automaticamente.

**Permissão:** Autenticado  
**Resposta `204`:** Sem conteúdo.

---

## 10. Avaliações

### `GET /avaliacoes/`

Lista todas as avaliações. Suporta ordenação: `?ordering=nota`.

**Permissão:** Autenticado  
**Resposta `200`:**
```json
[
  {
    "id": 1,
    "cliente_nome": "João Silva",
    "produto_nome": "Notebook X",
    "nota": 4.5,
    "comentario": "Ótimo produto!",
    "categorias": [{ "id": 2, "nome": "Eletrônicos" }]
  }
]
```

---

### `POST /avaliacoes/`

Cria uma avaliação. O cliente é definido automaticamente pelo token JWT.

**Permissão:** Autenticado  
**Restrições:**
- O cliente só pode avaliar produtos que já comprou.
- Apenas uma avaliação por cliente/produto (`unique_together`).

**Body (JSON):**

| Campo        | Tipo    | Obrigatório | Descrição                          |
|--------------|---------|-------------|-------------------------------------|
| `produto`    | integer | ✅          | ID do produto                       |
| `nota`       | float   | ✅          | Entre `0.0` e `5.0`                 |
| `comentario` | string  | ✅          | Máximo 100 caracteres               |

**Resposta `201`:** Objeto da avaliação criada.

---

### `GET /avaliacoes/{id}/`

Retorna os detalhes de uma avaliação.

**Permissão:** Autenticado (dono ou Admin)

---

### `PUT /avaliacoes/{id}/` · `PATCH /avaliacoes/{id}/`

Atualiza uma avaliação.

**Permissão:** Autenticado (dono ou Admin)

---

### `DELETE /avaliacoes/{id}/`

Remove uma avaliação.

**Permissão:** Autenticado (dono ou Admin)  
**Resposta `204`:** Sem conteúdo.

---

## 11. Tabelas M2M (Admin)

Endpoints de uso interno para gerenciar as relações many-to-many explícitas.

### `/produto-avaliacoes/`

Vincula avaliações a produtos manualmente.

**Permissão:** Admin (todas as operações)  
**Campos:** `produto` (ID), `avaliacao` (ID)

---

### `/avaliacao-categorias/`

Vincula avaliações a categorias.

**Permissão:** Admin (todas as operações)  
**Campos:** `avaliacao` (ID), `categoria` (ID)

Ambos os endpoints suportam os métodos padrão REST: `GET`, `POST`, `GET /{id}/`, `PUT /{id}/`, `PATCH /{id}/`, `DELETE /{id}/`.

---

## Permissões e Roles

| Role      | Descrição                                        |
|-----------|--------------------------------------------------|
| `cliente` | Acesso aos próprios dados, pode comprar e avaliar|
| `estoque` | Gerencia produtos e imagens                      |
| `admin`   | Acesso total a todos os recursos                 |

| Permissão        | Quem tem acesso                    |
|------------------|------------------------------------|
| `IsAdminRole`    | Apenas `role = admin`              |
| `IsGestorEstoque`| `role = admin` ou `role = estoque` |
| `IsOwnerOrAdmin` | Dono do recurso ou `role = admin`  |
| `IsAuthenticated`| Qualquer usuário autenticado       |

---

## Fluxo de Status do Pedido

```
pendente → processando → enviado → entregue
    ↓           ↓           ↓
 cancelado  cancelado   cancelado
```

> Pedidos com status `entregue` **não podem** ser cancelados.
