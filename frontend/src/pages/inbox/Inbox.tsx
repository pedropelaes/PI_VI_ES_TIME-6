import { useState } from 'react';
import { Search, Send, Paperclip, MoreVertical, CheckCheck } from 'lucide-react';
import './Inbox.css';

// Mocks simulando o retorno da sua API (F2)
const MOCK_CONVERSATIONS = [
  {
    id: '1',
    name: 'Carlos Eduardo',
    role: 'Olheiro Chefe - Clube A',
    lastMessage: 'Gostei muito dos seus clipes de recuperação de posse. Tem disponibilidade para...',
    time: '10:42',
    unread: 2,
    initial: 'C'
  },
  {
    id: '2',
    name: 'Ponte Negra (Base)',
    role: 'Clube Oficial',
    lastMessage: 'Podemos agendar uma avaliação na próxima semana?',
    time: 'Ontem',
    unread: 0,
    initial: 'V'
  },
  {
    id: '3',
    name: 'Marcos Silva',
    role: 'Agente Esportivo',
    lastMessage: 'Te enviei os detalhes do contrato por e-mail.',
    time: 'Segunda',
    unread: 0,
    initial: 'M'
  }
];

const MOCK_MESSAGES = [
  { id: 1, sender: 'them', text: 'Olá Daniel, tudo bem? Vi seu perfil no Feed da plataforma e os vídeos de análise técnica gerados pela IA chamaram muita atenção da nossa comissão.', time: '10:30' },
  { id: 2, sender: 'them', text: 'Gostaria de saber como está sua situação contratual no momento.', time: '10:31' },
  { id: 3, sender: 'me', text: 'Olá Carlos! Tudo ótimo. Fico feliz que tenham gostado do material.', time: '10:35' },
  { id: 4, sender: 'me', text: 'Atualmente estou livre no mercado, buscando novas oportunidades para a próxima temporada.', time: '10:36' },
  { id: 5, sender: 'them', text: 'Excelente. Gostei muito dos seus clipes de recuperação de posse. Tem disponibilidade para fazermos uma chamada de vídeo hoje à tarde?', time: '10:42' },
];

export default function Inbox() {
  const [activeChat, setActiveChat] = useState(MOCK_CONVERSATIONS[0]);
  const [messageText, setMessageText] = useState('');

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim()) return;
    // Aqui você conectaria com o Axios/WebSocket para enviar ao Backend
    console.log("Enviando:", messageText);
    setMessageText('');
  };

  return (
    <div className="inbox-root">
      <div className="inbox-container">
        
        {/* BARRA LATERAL ESQUERDA */}
        <div className="inbox-sidebar">
          <div className="sidebar-header">
            <h2>Mensagens</h2>
            <div className="search-bar">
              <Search size={18} color="rgba(255,255,255,0.4)" />
              <input type="text" placeholder="Buscar conversas..." />
            </div>
          </div>

          <div className="chat-list">
            {MOCK_CONVERSATIONS.map((chat) => (
              <div 
                key={chat.id} 
                className={`chat-item ${activeChat.id === chat.id ? 'active' : ''}`}
                onClick={() => setActiveChat(chat)}
              >
                <div className="chat-avatar">{chat.initial}</div>
                <div className="chat-item-info">
                  <div className="chat-item-header">
                    <span className="chat-item-name">{chat.name}</span>
                    <span className="chat-item-time">{chat.time}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="chat-item-message">{chat.lastMessage}</span>
                    {chat.unread > 0 && <span className="unread-badge">{chat.unread}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ÁREA CENTRAL DO CHAT */}
        <div className="inbox-chat-area">
          {/* Cabeçalho do Chat Ativo */}
          <div className="chat-area-header">
            <div className="active-chat-info">
              <div className="chat-avatar" style={{ width: '42px', height: '42px', fontSize: '1rem' }}>
                {activeChat.initial}
              </div>
              <div>
                <h3 className="chat-item-name" style={{ marginBottom: '2px' }}>{activeChat.name}</h3>
                <span className="active-chat-role">{activeChat.role}</span>
              </div>
            </div>
            <button className="btn-icon">
              <MoreVertical size={20} />
            </button>
          </div>

          {/* Lista de Mensagens */}
          <div className="chat-messages-container">
            {MOCK_MESSAGES.map((msg) => (
              <div key={msg.id} className={`message-wrapper ${msg.sender === 'me' ? 'mine' : 'theirs'}`}>
                <div className="message-bubble">
                  {msg.text}
                </div>
                <span className="message-time">
                  {msg.time}
                  {msg.sender === 'me' && <CheckCheck size={14} color="#5BADDA" />}
                </span>
              </div>
            ))}
          </div>

          {/* Campo de Digitação */}
          <div className="chat-input-area">
            <form className="input-container" onSubmit={handleSendMessage}>
              <button type="button" className="btn-icon">
                <Paperclip size={20} />
              </button>
              
              <input 
                type="text" 
                placeholder="Escreva sua mensagem..." 
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
              />
              
              <button type="submit" className="btn-send">
                <Send size={18} style={{ marginLeft: '2px' }} />
              </button>
            </form>
          </div>

        </div>
      </div>
    </div>
  );
}