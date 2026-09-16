import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Check, CheckCheck, MessageCircle, Search, Send } from 'lucide-react';
import { useConversationMessages } from '../../features/messaging/hooks/useConversationMessages';
import { useConversations } from '../../features/messaging/hooks/useConversations';
import { useStartConversation } from '../../features/messaging/hooks/useStartConversation';
import { getUser } from '../../services/api';
import './Inbox.css';

export default function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams();
  const myUserId = getUser()?.id;

  // O socket em si e aberto uma unica vez pelo Header (montado em toda pagina
  // privada via MainLayout) -- escreve no mesmo cache do React Query que esta tela
  // le, entao a Inbox recebe os eventos sem precisar da sua propria conexao.
  const { conversations, isLoading, isError } = useConversations();
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [messageText, setMessageText] = useState('');

  // Entrada vinda do botao "Enviar Mensagem" de um perfil (`/messages?to=<userId>`):
  // abre (ou reaproveita) a conversa com essa pessoa e limpa o parametro, para que um
  // F5 na Inbox nao tente abrir a mesma conversa de novo.
  const { start: startConversation, isStarting } = useStartConversation((conversation) => {
    setActiveConversationId(conversation.id);
    setSearchParams({}, { replace: true });
  });

  const paraUserId = searchParams.get('to');
  useEffect(() => {
    if (paraUserId) {
      startConversation(paraUserId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paraUserId]);

  // A primeira conversa da lista abre sozinha assim que carrega, contanto que nada
  // mais (nem o usuario, nem o `?to=`) ja tenha escolhido uma.
  useEffect(() => {
    if (!activeConversationId && !paraUserId && conversations.length > 0) {
      setActiveConversationId(conversations[0].id);
    }
  }, [activeConversationId, paraUserId, conversations]);

  const termoBusca = searchTerm.trim().toLowerCase();
  const conversasFiltradas = useMemo(
    () =>
      termoBusca
        ? conversations.filter((c) => c.fullName.toLowerCase().includes(termoBusca))
        : conversations,
    [conversations, termoBusca]
  );

  const activeConversation = conversations.find((c) => c.id === activeConversationId) ?? null;

  const {
    messages,
    isLoading: messagesLoading,
    isError: messagesError,
    send,
    isSending,
    sendErrorMessage,
  } = useConversationMessages(activeConversationId, myUserId);

  function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    const texto = messageText.trim();
    if (!texto || !activeConversationId) return;
    send(texto);
    setMessageText('');
  }

  return (
    <div className="inbox-root">
      <div className="inbox-container">
        {/* BARRA LATERAL ESQUERDA */}
        <div className="inbox-sidebar">
          <div className="sidebar-header">
            <h2>Mensagens</h2>
            <div className="search-bar">
              <Search size={18} color="rgba(255,255,255,0.4)" />
              <input
                type="text"
                placeholder="Buscar conversas..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          <div className="chat-list">
            {isLoading && <p className="inbox-state-text">Carregando conversas...</p>}

            {!isLoading && isError && (
              <p className="inbox-state-text inbox-state-error">
                Não foi possível carregar suas conversas.
              </p>
            )}

            {!isLoading && !isError && conversations.length === 0 && (
              <div className="inbox-empty-state">
                <MessageCircle size={32} />
                <p>Você ainda não tem conversas.</p>
                <span>Visite o perfil de um atleta, scout ou clube para começar.</span>
              </div>
            )}

            {!isLoading && !isError && conversations.length > 0 && conversasFiltradas.length === 0 && (
              <p className="inbox-state-text">Nenhuma conversa encontrada.</p>
            )}

            {conversasFiltradas.map((chat) => (
              <div
                key={chat.id}
                className={`chat-item ${activeConversationId === chat.id ? 'active' : ''}`}
                onClick={() => setActiveConversationId(chat.id)}
              >
                <div className="chat-avatar">
                  {chat.avatarUrl ? (
                    <img src={chat.avatarUrl} alt="" className="chat-avatar-image" />
                  ) : (
                    chat.initial
                  )}
                </div>
                <div className="chat-item-info">
                  <div className="chat-item-header">
                    <span className="chat-item-name">{chat.fullName}</span>
                    <span className="chat-item-time">{chat.timeLabel}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="chat-item-message">{chat.lastMessagePreview}</span>
                    {chat.unreadCount > 0 && (
                      <span className="unread-badge">{chat.unreadCount}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ÁREA CENTRAL DO CHAT */}
        <div className="inbox-chat-area">
          {isStarting && (
            <div className="inbox-chat-placeholder">
              <p>Abrindo conversa...</p>
            </div>
          )}

          {!isStarting && !activeConversation && (
            <div className="inbox-chat-placeholder">
              <MessageCircle size={40} />
              <p>Selecione uma conversa para começar.</p>
            </div>
          )}

          {!isStarting && activeConversation && (
            <>
              {/* Cabeçalho do Chat Ativo */}
              <div className="chat-area-header">
                <div className="active-chat-info">
                  <div
                    className="chat-avatar"
                    style={{ width: '42px', height: '42px', fontSize: '1rem' }}
                  >
                    {activeConversation.avatarUrl ? (
                      <img
                        src={activeConversation.avatarUrl}
                        alt=""
                        className="chat-avatar-image"
                      />
                    ) : (
                      activeConversation.initial
                    )}
                  </div>
                  <div>
                    <h3 className="chat-item-name" style={{ marginBottom: '2px' }}>
                      {activeConversation.fullName}
                    </h3>
                    <span className="active-chat-role">{activeConversation.roleLabel}</span>
                  </div>
                </div>
              </div>

              {/* Lista de Mensagens */}
              <div className="chat-messages-container">
                {messagesLoading && <p className="inbox-state-text">Carregando mensagens...</p>}

                {!messagesLoading && messagesError && (
                  <p className="inbox-state-text inbox-state-error">
                    Não foi possível carregar as mensagens.
                  </p>
                )}

                {!messagesLoading && !messagesError && messages.length === 0 && (
                  <p className="inbox-state-text">
                    Nenhuma mensagem ainda. Diga oi para {activeConversation.fullName.split(' ')[0]}!
                  </p>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`message-wrapper ${msg.mine ? 'mine' : 'theirs'}`}
                  >
                    <div className="message-bubble">{msg.body}</div>
                    <span className="message-time">
                      {msg.timeLabel}
                      {msg.mine &&
                        (msg.read ? (
                          <CheckCheck size={14} color="#5BADDA" />
                        ) : (
                          <Check size={14} color="rgba(255,255,255,0.4)" />
                        ))}
                    </span>
                  </div>
                ))}
              </div>

              {/* Campo de Digitação */}
              <div className="chat-input-area">
                <form className="input-container" onSubmit={handleSendMessage}>
                  <input
                    type="text"
                    placeholder="Escreva sua mensagem..."
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    disabled={isSending}
                  />

                  <button
                    type="submit"
                    className="btn-send"
                    disabled={isSending || !messageText.trim()}
                  >
                    <Send size={18} style={{ marginLeft: '2px' }} />
                  </button>
                </form>
                {sendErrorMessage && (
                  <p className="inbox-send-error" role="alert">
                    Não foi possível enviar: {sendErrorMessage}
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
