import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api.js';
import { Notice } from './components/ui.jsx';
import Login from './pages/Login.jsx';
import AdminDashboard from './pages/AdminDashboard.jsx';
import MemberDashboard from './pages/MemberDashboard.jsx';
import FirstAccess from './pages/FirstAccess.jsx';
import './style.css';

function App() {
  const [user, setUser] = useState(null);
  const [screen, setScreen] = useState('welcome');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  async function loadSession() { setError(''); try { const result = await api('auth/session/'); setUser(result.user); setReady(true); } catch (error) { setError('No se pudo conectar con SIGMA. Comprueba que el servidor esté activo.'); } }
  useEffect(() => {
    loadSession();
    const refreshSession = () => loadSession();
    window.addEventListener('sigma:password-required', refreshSession);
    return () => window.removeEventListener('sigma:password-required', refreshSession);
  }, []);
  async function logout() { try { await api('auth/logout/', { method: 'POST' }); setUser(null); setScreen('welcome'); await loadSession(); } catch (error) { setError(error.message); } }
  if (!ready) return <main className="public-shell"><p role="status">Conectando con SIGMA…</p><Notice error>{error}</Notice>{error && <button onClick={loadSession} className="primary">Reintentar</button>}</main>;
  if (user) {
    const props = { user, logout, onUserChange: setUser };
    return <><Notice error>{error}</Notice>{user.must_change_password
      ? <FirstAccess {...props} />
      : user.role === 'administrator' ? <AdminDashboard {...props} /> : <MemberDashboard {...props} />}</>;
  }
  return <main className="public-shell"><header><a href="/" className="brand">σ <span>SIGMA</span></a><span className="label">TU COMUNIDAD, CONECTADA</span></header><Notice error>{error}</Notice>{screen === 'login' ? <Login onLogin={setUser} onBack={() => setScreen('welcome')} /> : <section className="welcome"><div><p className="eyebrow">SISTEMA INTEGRAL DE GESTIÓN DE MATRÍCULAS ACADÉMICAS</p><h1>Un lugar para<br />conectar tu<br /><em>futuro académico.</em></h1><p className="description">Bienvenido a SIGMA. Universidades, docentes y estudiantes,<br className="desktop-break" /> unidos en un mismo espacio.</p><button className="primary" onClick={() => setScreen('login')}>Iniciar sesión <span aria-hidden="true">↗</span></button><p className="hint">Acceso para miembros de instituciones afiliadas.</p></div><div className="welcome-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="sigma-symbol">σ</div><span className="art-caption">CONOCIMIENTO QUE CONECTA</span><span className="art-node node-one">Universidades</span><span className="art-node node-two">Docentes</span><span className="art-node node-three">Estudiantes</span></div></section>}<footer><span>SIGMA</span><span>Una comunidad. Infinitas posibilidades.</span></footer></main>;
}
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
