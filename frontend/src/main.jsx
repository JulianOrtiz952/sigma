import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api, previewEmail } from './api.js';
import './style.css';

const roles = { administrator: 'Administrador', teacher: 'Docente', student: 'Estudiante' };
const emptyAccount = { role: 'student', first_name: '', first_surname: '', second_surname: '', university: '', academic_program: '', password: '' };

function Field({ label, children, ...props }) {
  return <label className="field"><span>{label}</span>{children || <input {...props} />}</label>;
}
function Notice({ error, children }) {
  return children ? <div className={`notice ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>{children}</div> : null;
}
function UniversitySelect({ universities, value, onChange, label = 'Universidad' }) {
  return <Field label={label}><select required value={value} onChange={onChange}><option value="">Selecciona una universidad</option>{universities.map(university => <option key={university.id} value={university.id}>{university.name}</option>)}</select></Field>;
}
function Login({ onLogin, onBack }) {
  const [form, setForm] = useState({ username: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { const result = await api('auth/login/', { method: 'POST', body: form }); onLogin(result.user); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  return <section className="login-layout"><div><p className="eyebrow">TU COMUNIDAD ACADÉMICA</p><h1>Todo comienza<br />con una conexión.</h1><p className="description">Ingresa para acceder a tu espacio en SIGMA.</p></div><form className="panel login-panel" onSubmit={submit}><p className="eyebrow">BIENVENIDO DE NUEVO</p><h2>Iniciar sesión</h2><p className="muted">Usa tu usuario o correo institucional.</p><Field label="Usuario o correo" autoComplete="username" required value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /><Field label="Contraseña" type="password" autoComplete="current-password" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /><Notice error>{error}</Notice><button className="primary full" disabled={busy}>{busy ? 'Ingresando…' : 'Iniciar sesión'} <span aria-hidden="true">↗</span></button><p className="hint">Las cuentas son creadas por la administración de SIGMA.</p><button className="text-button" type="button" onClick={onBack}>Volver a la bienvenida</button></form></section>;
}
function Universities({ universities, programs, refresh, canAffiliate }) {
  const [form, setForm] = useState({ name: '', email_domain: '' });
  const [program, setProgram] = useState({ name: '', university: '' });
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  async function submit(event, type) {
    event.preventDefault(); setBusy(type); setError(''); setSuccess('');
    try {
      await api(type === 'university' ? 'universities/' : 'programs/', { method: 'POST', body: type === 'university' ? form : { ...program, university: Number(program.university) } });
      if (type === 'university') setForm({ name: '', email_domain: '' }); else setProgram({ name: '', university: '' });
      await refresh(); setSuccess(type === 'university' ? 'Universidad afiliada. Ya puedes crear sus programas y usuarios.' : 'Programa académico creado.');
    } catch (error) { setError(error.message); } finally { setBusy(''); }
  }
  return <><div className="page-heading"><div><p className="eyebrow">COMUNIDAD ACADÉMICA</p><h1>Universidades</h1><p className="muted">Afiliación institucional y programas académicos.</p></div><span className="count">{universities.length} afiliadas</span></div><Notice error>{error}</Notice><Notice>{success}</Notice><div className="two-columns"><div className="stack">{canAffiliate && <form className="panel" onSubmit={e => submit(e, 'university')}><span className="step">01 / AFILIACIÓN</span><h2>Afiliar universidad</h2><Field label="Nombre de la universidad" placeholder="UFPS" maxLength={150} required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /><Field label="Dominio del correo institucional" placeholder="ufps.edu.co" maxLength={253} required value={form.email_domain} onChange={e => setForm({ ...form, email_domain: e.target.value })} /><p className="hint">Solo el dominio, sin @ ni https://. Se utilizará para generar los correos.</p><button disabled={!!busy} className="primary">{busy === 'university' ? 'Guardando…' : 'Afiliar universidad'}</button></form>}<form className="panel" onSubmit={e => submit(e, 'program')}><span className="step">02 / OFERTA ACADÉMICA</span><h2>Crear programa</h2><UniversitySelect universities={universities} value={program.university} onChange={e => setProgram({ ...program, university: e.target.value })} /><Field label="Nombre del programa" placeholder="Ingeniería de Sistemas" maxLength={150} required value={program.name} onChange={e => setProgram({ ...program, name: e.target.value })} /><button disabled={!!busy || !universities.length} className="primary">{busy === 'program' ? 'Guardando…' : 'Crear programa'}</button>{!universities.length && <p className="hint">Primero afilia una universidad.</p>}</form></div><section className="panel"><h2>Instituciones afiliadas</h2>{!universities.length ? <div className="empty"><span aria-hidden="true">▧</span><h3>Una comunidad por construir</h3><p>Las universidades que afilies aparecerán aquí.</p></div> : <div className="institution-list">{universities.map(university => <article key={university.id} className="institution"><div className="institution-title"><span className="institution-icon" aria-hidden="true">{university.name.slice(0, 2).toUpperCase()}</span><div><h3>{university.name}</h3><p>@{university.email_domain}</p></div></div><div className="tags">{programs.filter(p => p.university === university.id).map(p => <span key={p.id}>{p.name}</span>)}{!programs.some(p => p.university === university.id) && <p className="hint">Aún no tiene programas registrados.</p>}</div></article>)}</div>}</section></div></>;
}
function Users({ universities, programs, users, refresh, goUniversities }) {
  const [form, setForm] = useState(emptyAccount);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState(null);
  const [defaultPassword, setDefaultPassword] = useState(true);
  const university = universities.find(u => u.id === Number(form.university));
  const availablePrograms = programs.filter(p => p.university === Number(form.university));
  const email = previewEmail(form.first_name, form.first_surname, form.second_surname, university?.email_domain);
  function update(key, value) { setForm(current => ({ ...current, [key]: value, ...(['university', 'role'].includes(key) ? { academic_program: '' } : {}) })); }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); setCreated(null);
    const body = { ...form, university: Number(form.university), academic_program: form.role === 'student' ? Number(form.academic_program) : null };
    try {
      const result = await api('auth/signup/', { method: 'POST', body });
      setDefaultPassword(!form.password); setCreated(result); setForm(emptyAccount); await refresh();
    } catch (error) { setError(error.message); } finally { setBusy(false); }
  }
  return <><div className="page-heading"><div><p className="eyebrow">ADMINISTRACIÓN</p><h1>Creación de usuarios</h1><p className="muted">Da la bienvenida a docentes y estudiantes.</p></div><span className="count">{users.length} usuarios</span></div><Notice error>{error}</Notice>{created && <Notice><strong>Cuenta creada: {created.first_name} {created.first_surname}</strong><br />Correo: {created.email} · Código: {created.code}<br />{defaultPassword ? 'La contraseña inicial es el código de esta cuenta.' : 'La contraseña es la indicada al crear la cuenta.'}</Notice>}{!universities.length && <div className="notice"><p>Para crear usuarios, primero afilia una universidad.</p><button className="secondary" onClick={goUniversities}>Afiliar universidad ↗</button></div>}<div className="two-columns users-grid"><form className="panel" onSubmit={submit}><h2>Nueva cuenta</h2><div className="segmented" aria-label="Tipo de usuario">{['student', 'teacher'].map(role => <button key={role} type="button" aria-pressed={form.role === role} className={form.role === role ? 'selected' : ''} onClick={() => update('role', role)}>{roles[role]}</button>)}</div><Field label="Nombres" placeholder="Andres Julian" required maxLength={150} value={form.first_name} onChange={e => update('first_name', e.target.value)} /><div className="form-row"><Field label="Primer apellido" placeholder="Ortiz" required maxLength={100} value={form.first_surname} onChange={e => update('first_surname', e.target.value)} /><Field label="Segundo apellido" placeholder="Jaimes" required maxLength={100} value={form.second_surname} onChange={e => update('second_surname', e.target.value)} /></div><UniversitySelect universities={universities} value={form.university} onChange={e => update('university', e.target.value)} />{form.role === 'student' && <><Field label="Programa académico"><select required value={form.academic_program} onChange={e => update('academic_program', e.target.value)}><option value="">Selecciona un programa</option>{availablePrograms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>{form.university && !availablePrograms.length && <p className="hint">Crea primero un programa para esta universidad en la sección Universidades.</p>}</>}<div className="email-preview"><span>CORREO GENERADO</span><strong>{email || 'Completa los nombres y selecciona una universidad'}</strong></div><Field label="Contraseña personalizada (opcional)" type="password" autoComplete="new-password" maxLength={128} value={form.password} onChange={e => update('password', e.target.value)} placeholder="Por defecto: código de la cuenta" /><p className="hint">El código se asigna automáticamente al guardar. El correo es un identificador local; no se crea un buzón de correo.</p><button disabled={busy || !universities.length} className="primary full">{busy ? 'Creando cuenta…' : 'Crear cuenta'} <span aria-hidden="true">↗</span></button></form><section className="panel"><h2>Usuarios registrados</h2><p className="muted small">Cuentas creadas por la administración.</p>{!users.length ? <div className="empty"><span aria-hidden="true">♧</span><h3>Aquí comienza la comunidad</h3><p>Crea tu primera cuenta para verla en esta lista.</p></div> : <div className="user-list">{users.map(user => <article className="user-card" key={user.id}><div className="user-card-top"><h3>{user.first_name} {user.first_surname} {user.second_surname}</h3><span className={`badge ${user.role}`}>{roles[user.role]}</span></div><p className="user-email">{user.email}</p><p className="hint">Código {user.code} · {user.university}</p>{user.academic_program && <p className="hint">{user.academic_program}</p>}</article>)}</div>}</section></div></>;
}
function Dashboard({ user, logout }) {
  const [section, setSection] = useState('users');
  const [data, setData] = useState({ universities: [], programs: [], users: [] });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  async function refresh() {
    const [universities, programs, users] = await Promise.all([api('universities/'), api('programs/'), api('users/')]);
    setData({ universities, programs, users }); setError('');
  }
  useEffect(() => {
    if (user.role !== 'administrator') { setLoading(false); return; }
    refresh().catch(error => setError(error.message)).finally(() => setLoading(false));
  }, [user.id]);
  return <><header className="app-header"><a href="/" className="brand">σ <span>SIGMA</span></a>{user.role === 'administrator' && <nav aria-label="Navegación principal"><button className={section === 'users' ? 'active' : ''} onClick={() => setSection('users')}>Creación de usuarios</button><button className={section === 'universities' ? 'active' : ''} onClick={() => setSection('universities')}>Universidades</button></nav>}<div className="session"><span><strong>{user.first_name || user.username}</strong><small>{roles[user.role]}</small></span><button className="secondary" onClick={logout}>Salir</button></div></header><div className="workspace"><Notice error>{error}</Notice>{loading ? <p role="status">Cargando tu espacio…</p> : user.role === 'administrator' ? section === 'users' ? <Users {...data} refresh={refresh} goUniversities={() => setSection('universities')} /> : <Universities {...data} refresh={refresh} canAffiliate={user.is_global_admin} /> : <section className="member-welcome"><p className="eyebrow">{roles[user.role].toUpperCase()} / {user.university}</p><h1>Bienvenido,<br />{user.first_name}.</h1><p className="description">Este es tu espacio académico en SIGMA.</p><div className="panel"><p><strong>Correo institucional</strong><br />{user.email}</p><p><strong>Código</strong><br />{user.code}</p>{user.academic_program && <p><strong>Programa académico</strong><br />{user.academic_program}</p>}</div></section>}</div></>;
}
function App() {
  const [user, setUser] = useState(null);
  const [screen, setScreen] = useState('welcome');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  async function loadSession() { setError(''); try { const result = await api('auth/session/'); setUser(result.user); setReady(true); } catch (error) { setError('No se pudo conectar con SIGMA. Comprueba que el servidor esté activo.'); } }
  useEffect(() => { loadSession(); }, []);
  async function logout() { try { await api('auth/logout/', { method: 'POST' }); setUser(null); setScreen('welcome'); await loadSession(); } catch (error) { setError(error.message); } }
  if (!ready) return <main className="public-shell"><p role="status">Conectando con SIGMA…</p><Notice error>{error}</Notice>{error && <button onClick={loadSession} className="primary">Reintentar</button>}</main>;
  if (user) return <><Notice error>{error}</Notice><Dashboard user={user} logout={logout} /></>;
  return <main className="public-shell"><header><a href="/" className="brand">σ <span>SIGMA</span></a><span className="label">TU COMUNIDAD, CONECTADA</span></header><Notice error>{error}</Notice>{screen === 'login' ? <Login onLogin={setUser} onBack={() => setScreen('welcome')} /> : <section className="welcome"><div><p className="eyebrow">SISTEMA INTEGRAL DE GESTIÓN DE MATRÍCULAS ACADÉMICAS</p><h1>Un lugar para<br />conectar tu<br /><em>futuro académico.</em></h1><p className="description">Bienvenido a SIGMA. Universidades, docentes y estudiantes,<br className="desktop-break" /> unidos en un mismo espacio.</p><button className="primary" onClick={() => setScreen('login')}>Iniciar sesión <span aria-hidden="true">↗</span></button><p className="hint">Acceso para miembros de instituciones afiliadas.</p></div><div className="welcome-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="sigma-symbol">σ</div><span className="art-caption">CONOCIMIENTO QUE CONECTA</span><span className="art-node node-one">Universidades</span><span className="art-node node-two">Docentes</span><span className="art-node node-three">Estudiantes</span></div></section>}<footer><span>SIGMA</span><span>Una comunidad. Infinitas posibilidades.</span></footer></main>;
}
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
