import React, { useState } from 'react';
import { api, previewEmail } from '../api.js';
import { Field, Notice, UniversitySelect, roles } from '../components/ui.jsx';

const emptyAccount = { role: 'student', first_name: '', first_surname: '', second_surname: '', university: '', academic_program: '', password: '' };

export default function Users({ universities, programs, users, refresh, goUniversities }) {
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
  return <>
    <div className="page-heading"><div><p className="eyebrow">ADMINISTRACIÓN</p><h1>Creación de usuarios</h1><p className="muted">Da la bienvenida a docentes y estudiantes. Las cuentas existentes están en Registros.</p></div></div>
    <Notice error>{error}</Notice>
    {created && <Notice><strong>Cuenta creada: {created.first_name} {created.first_surname}</strong><br />Correo: {created.email} · Código: {created.code}<br />{defaultPassword ? 'La contraseña inicial es el código de esta cuenta.' : 'La contraseña es la indicada al crear la cuenta.'}</Notice>}
    {!universities.length && <div className="notice"><p>Para crear usuarios, primero afilia una universidad.</p><button className="secondary" onClick={goUniversities}>Afiliar universidad ↗</button></div>}
    <div className="form-shell"><form className="panel" onSubmit={submit}>
      <h2>Nueva cuenta</h2>
      <div className="segmented" aria-label="Tipo de usuario">{['student', 'teacher'].map(role => <button key={role} type="button" aria-pressed={form.role === role} className={form.role === role ? 'selected' : ''} onClick={() => update('role', role)}>{roles[role]}</button>)}</div>
      <Field label="Nombres" placeholder="Andres Julian" required maxLength={150} value={form.first_name} onChange={e => update('first_name', e.target.value)} />
      <div className="form-row"><Field label="Primer apellido" placeholder="Ortiz" required maxLength={100} value={form.first_surname} onChange={e => update('first_surname', e.target.value)} /><Field label="Segundo apellido" placeholder="Jaimes" required maxLength={100} value={form.second_surname} onChange={e => update('second_surname', e.target.value)} /></div>
      <UniversitySelect universities={universities} value={form.university} onChange={e => update('university', e.target.value)} />
      {form.role === 'student' && <><Field label="Programa académico"><select required value={form.academic_program} onChange={e => update('academic_program', e.target.value)}><option value="">Selecciona un programa</option>{availablePrograms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>{form.university && !availablePrograms.length && <p className="hint">Crea primero un programa para esta universidad en la sección Universidades.</p>}</>}
      <div className="email-preview"><span>VISTA PREVIA DEL CORREO</span><strong>{email || 'Completa los nombres y selecciona una universidad'}</strong><p className="hint">Si ya existe, se añadirá un número al guardar. El resultado final aparecerá al crear la cuenta.</p></div>
      <Field label="Contraseña personalizada (opcional)" type="password" autoComplete="new-password" maxLength={128} value={form.password} onChange={e => update('password', e.target.value)} placeholder="Por defecto: código de la cuenta" />
      <p className="hint">El código se asigna automáticamente. El primer inicio de sesión requiere cambiar la contraseña.</p>
      <button disabled={busy || !universities.length} className="primary full">{busy ? 'Creando cuenta…' : 'Crear cuenta'} <span aria-hidden="true">↗</span></button>
    </form></div>
  </>;
}
