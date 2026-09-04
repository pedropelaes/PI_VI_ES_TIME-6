import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import logoSmartScout from '../../assets/logo-smartscout.png';
import { clearSession, getToken, getUser } from '../../services/api';
import { getProfilePath, PROFILE_EDIT_PATH } from '../../shared/lib/profileRoutes';
import { isUserRole } from '../../shared/lib/userRole';
import {
  SquarePlay,
  Compass,
  CircleUserRound,
  X,
  Mail
} from 'lucide-react';
import './Header.css';

export function Header() {
  const [showProfileModal, setShowProfileModal] = useState(false);
  const navigate = useNavigate();

  const storedUser = getUser() ?? {};

  // Sessao gravada antes do papel existir (ou dado corrompido) nao tem para
  // onde navegar: melhor esconder o botao do que quebrar o modal inteiro.
  const canOpenProfile = Boolean(storedUser.id) && isUserRole(storedUser.role);

  const user = {
    name: storedUser.first_name && storedUser.last_name
      ? `${storedUser.first_name} ${storedUser.last_name}`
      : 'Usuário',
    email: storedUser.email || 'sem e-mail',
  };

  function handleOpenProfileModal() {
    setShowProfileModal(true);
  }

  function handleCloseProfileModal() {
    setShowProfileModal(false);
  }

  function handleOpenMyProfile() {
    setShowProfileModal(false);
    // getProfilePath e o unico lugar que monta rota de perfil (decisao Q6).
    navigate(getProfilePath(storedUser));
  }

  function handleEditProfile() {
    setShowProfileModal(false);
    navigate(PROFILE_EDIT_PATH);
  }

  async function handleLogout() {
    try {
      const token = getToken();
      if (token) {
        await fetch(`${import.meta.env.VITE_API_PATH}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error('Erro ao chamar logout no backend:', error);
    }

    // clearSession() apaga as chaves reais (access_token/user). A versao anterior
    // removia 'token', chave que nao existe, deixando a sessao viva apos o logout.
    clearSession();
    setShowProfileModal(false);
    navigate('/login');
  }

  useEffect(() => {
    function handleEsc(event) {
      if (event.key === 'Escape') {
        setShowProfileModal(false);
      }
    }

    if (showProfileModal) {
      window.addEventListener('keydown', handleEsc);
    }

    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [showProfileModal]);

  return (
    <>
      <header className="header">
        <Link to="/" className="brand">
          <img src={logoSmartScout} alt="SmartScout" className="brand-logo" />
        </Link>

        <div className="actionsGroup">
          <Link to="/clips-history">
            <button
              className="iconButton"
              aria-label="Meus Clipes"
              title="Meus Clipes"
            >
              <SquarePlay size={40} />
            </button>
          </Link>

          <Link to="/feed">
            <button className="iconButton" aria-label="Feed de talentos" title="Feed de talentos">
              <Compass size={34} />
            </button>
          </Link>

            <button
                className="iconButton headerAvatarButton"
                aria-label="Perfil do Usuário"
                title="Perfil"
                onClick={handleOpenProfileModal}
              >
                <div className="headerAvatar">
                  {user.name.charAt(0).toUpperCase()}
                </div>
            </button>
        </div>
      </header>

      {showProfileModal && (
        <div className="profileOverlay" onClick={handleCloseProfileModal}>
          <div
            className="profileModal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="closeModalButton"
              onClick={handleCloseProfileModal}
              aria-label="Fechar modal"
            >
              <X size={20} />
            </button>

            <div className="profileTop">
              <div className="profileAvatar">
                {user.name.charAt(0).toUpperCase()}
              </div>

              <h2 className="profileName">{user.name}</h2>
              <p className="profileSubtitle">Informações da conta</p>
            </div>

            <div className="profileInfoCard">
              <div className="profileInfoRow">
                <Mail size={18} />
                <div>
                  <span className="infoLabel">E-mail</span>
                  <strong>{user.email}</strong>
                </div>
              </div>
            </div>

            <div className="profileActions">
              {canOpenProfile && (
                <button className="primaryButton" onClick={handleOpenMyProfile}>
                  Ver meu perfil
                </button>
              )}

              {/* Edicao nao depende do papel: o /profiles/me descobre sozinho. */}
              <button className="secondaryButton" onClick={handleEditProfile}>
                Editar perfil
              </button>

              <button className="logoutButton" onClick={handleLogout}>
                Sair da conta
              </button>

              <button
                className="secondaryButton"
                onClick={handleCloseProfileModal}
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}