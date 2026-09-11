Para que essa tela de Inbox funcione perfeitamente, o seu backend em **FastAPI** precisa de uma estrutura sólida que suporte tanto o carregamento histórico (via rotas normais) quanto a comunicação em tempo real (para as mensagens chegarem sem precisar recarregar a página).  
Aqui está a especificação passo a passo do que precisa ser implementado no F2 (Backend) usando a sua stack (FastAPI \+ PostgreSQL).

### **Fase 1: Modelagem do Banco de Dados (Tabelas)**

Você precisará criar (ou atualizar) seus modelos no SQLAlchemy. O ideal para um chat flexível é ter três tabelas:

> 1. **Tabela conversations (As salas de chat):**  
   * id (UUID, PK)  
   * created\_at (DateTime)  
   * updated\_at (DateTime) \- *Sempre atualizado quando uma nova mensagem chega, para ordenar a sidebar.*  
> 2. **Tabela conversation\_participants (Quem está na conversa):**  
   * conversation\_id (FK)  
   * user\_id (FK)  
   * *(Ter essa tabela permite escalar no futuro para chats em grupo, em vez de limitar a apenas Usuário A e Usuário B).*  
> 3. **Tabela messages (O conteúdo):**  
   * id (UUID, PK)  
   * conversation\_id (FK)  
   * sender\_id (FK)  
   * content (Text)  
   * is\_read (Boolean, default: False)  
   * created\_at (DateTime)

### **Fase 2: Criar as Rotas REST (Endpoints HTTP)**

Estas são as rotas clássicas para carregar a tela quando o usuário entra na página.

* **GET /api/v1/conversations**  
  * **O que faz:** Retorna a lista para a *Barra Lateral* (Sidebar).  
  * **Regra:** Buscar todas as conversations onde o user\_id logado está em conversation\_participants.  
  * **Payload de Retorno:** Deve incluir os dados do *outro* usuário (nome, foto, cargo), o texto da *última mensagem* e a *contagem de mensagens não lidas*.  
* **GET /api/v1/conversations/{conversation\_id}/messages**  
  * **O que faz:** Carrega o histórico da conversa quando o usuário clica em um contato.  
  * **Regra:** Aplicar paginação (ex: carregar as últimas 50 mensagens). O frontend mandará a página atual.  
  * **Segurança:** Verificar se o usuário logado é um participante dessa conversation\_id. Se não for, retornar erro 403 Forbidden.  
* **POST /api/v1/conversations**  
  * **O que faz:** Inicia um novo chat. É acionado quando alguém clica em "Enviar Mensagem" no Perfil do Atleta.  
  * **Regra:** Verificar se já existe uma conversa entre os dois usuários. Se existir, retorna o ID da existente. Se não, cria uma nova no banco.  
* **PATCH /api/v1/conversations/{conversation\_id}/read**  
  * **O que faz:** Marca as mensagens como lidas (aqueles *dois risquinhos azuis*).  
  * **Regra:** Atualiza is\_read \= True para todas as mensagens daquela conversa onde o sender\_id for *diferente* do usuário logado.

### **Fase 3: Implementar o Tempo Real (WebSockets)**

Para que o chat pareça o WhatsApp, as mensagens novas não podem depender de a pessoa ficar atualizando a página. O FastAPI tem suporte nativo maravilhoso para isso.

> 1. **Criar o Connection Manager:**  
   * Fazer uma classe no Python que guarde um dicionário dos usuários conectados. Exemplo: active\_connections \= { "user\_id\_123": websocket\_object }.  
> 2. **Criar a Rota WebSocket: ws://api/ws/chat**  
   * Quando o frontend carregar a página Inbox, ele conecta neste endpoint.  
   * O FastAPI aceita a conexão e salva o usuário no Manager.  
> 3. **Fluxo de Envio de Mensagem (Via WS ou POST):**  
   * O Usuário A digita a mensagem e aperta Enter.  
   * O Backend salva a mensagem na tabela messages do PostgreSQL.  
   * O Backend verifica no Connection Manager: *O Usuário B está online agora?*  
   * Se **Sim**: O Backend dispara a mensagem via WebSocket direto para a tela do Usuário B (atualizando a UI instantaneamente).  
   * Se **Não**: A mensagem apenas fica salva no banco. (Bônus: Disparar uma notificação push ou e-mail avisando *"Você tem uma nova mensagem de Carlos"*).

### **Fase 4: Integração com o Redis (Opcional, mas recomendado)**

Eu notei nos seus logs do Docker que vocês já têm um contêiner do **Redis** e do **Celery** rodando\!

* Se vocês tiverem vários "Workers" do FastAPI rodando ao mesmo tempo (escalabilidade), o WebSocket de uma pessoa pode cair no Worker 1 e o da outra no Worker 2\.  
* **O uso perfeito:** Quando salvar a mensagem, mande um evento para o canal *Pub/Sub* do Redis. Todos os Workers escutam o Redis e repassam a mensagem para o websocket correto.

### **Resumo para o seu Frontend (F3)**

Quando esse backend estiver pronto, o fluxo do seu Inbox.tsx será:

> 1. Ao abrir a tela: Roda o axios.get('/conversations') usando o useQuery (React Query).  
> 2. Conecta no WebSocket: new WebSocket('ws://localhost:8000/ws/chat').  
> 3. Ao clicar num contato: Roda o axios.get('/conversations/{id}/messages').  
> 4. Ao mandar mensagem: Emite pelo WebSocket ou dá um POST.

Você quer que eu te mande um **exemplo de código do FastAPI** de como estruturar essa rota de WebSocket ou os modelos do SQLAlchemy para o chat?