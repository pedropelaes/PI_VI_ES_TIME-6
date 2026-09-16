import { Link, useNavigate } from 'react-router-dom';
import { SearchX, Home, ArrowLeft, Compass, SquarePlay, LogIn } from 'lucide-react';
import logoSmartScout from '../../assets/logo-smartscout.png';
import { isAuthenticated } from '../../services/api';
import './NotFound.css';

export default function NotFound() {
  const navigate = useNavigate();
  const loggedIn = isAuthenticated();

  // Destino principal baseado na autenticação do usuário
  const homePath = loggedIn ? '/app' : '/';

  function handleGoBack() {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(homePath);
    }
  }

  return (
    <div className="not-found-page" data-testid="not-found-page">
      <header className="not-found-header">
        <Link to={homePath} className="not-found-brand" aria-label="Ir para a página inicial">
          <img src={logoSmartScout} alt="SmartScout" className="not-found-logo" />
        </Link>
      </header>

      <main className="not-found-content">
        <div className="not-found-card">
          <div className="not-found-badge-wrapper">
            <div className="not-found-icon-container" aria-hidden="true">
              <SearchX size={44} />
            </div>
          </div>

          <span className="not-found-error-code">404</span>
          <h1 className="not-found-title">Página não encontrada</h1>
          <p className="not-found-description">
            Ops! O endereço que você tentou acessar não existe, 
            foi removido ou está temporariamente indisponível.
          </p>

          <div className="not-found-actions">
            <Link to={homePath} className="not-found-btn not-found-btn-primary">
              <Home size={18} />
              Voltar ao Início
            </Link>

            <button
              type="button"
              onClick={handleGoBack}
              className="not-found-btn not-found-btn-secondary"
            >
              <ArrowLeft size={18} />
              Página Anterior
            </button>
          </div>

          <div className="not-found-extra-links">
            <span className="not-found-extra-text">Sugestões rápidas:</span>
            {loggedIn ? (
              <>
                <Link to="/feed" className="not-found-link">
                  <Compass size={16} /> Feed de Talentos
                </Link>
                <Link to="/clips-history" className="not-found-link">
                  <SquarePlay size={16} /> Meus Clipes
                </Link>
              </>
            ) : (
              <>
                <Link to="/login" className="not-found-link">
                  <LogIn size={16} /> Fazer Login
                </Link>
                <Link to="/signup" className="not-found-link">
                  Criar Conta
                </Link>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

