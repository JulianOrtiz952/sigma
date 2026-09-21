import React, { useState } from 'react';
import { api, previewEmail } from '../api.js';
import { Field, Notice, UniversitySelect, roles } from '../components/ui.jsx';

export default function Login({ onLogin, onBack }) {
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
