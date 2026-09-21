import React, { useState } from 'react';
import { api } from '../api.js';
import { Field, Notice } from './ui.jsx';

const emptyForm = { current_password: '', new_password: '', confirm_password: '' };

export default function PasswordForm({ mandatory = false, onChanged }) {
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  function update(key, value) { setForm(current => ({ ...current, [key]: value })); }
  async function submit(event) {
    event.preventDefault();
    setError(''); setSuccess('');
    if (form.new_password !== form.confirm_password) {
      setError('Las contraseñas nuevas no coinciden.');
      return;
    }
    setBusy(true);
    try {
      const result = await api('auth/change-password/', { method: 'POST', body: form });
      setForm(emptyForm);
      setSuccess('Tu contraseña se actualizó correctamente.');
      onChanged(result.user);
    } catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  return (
    <form className="panel password-panel" onSubmit={submit} aria-busy={busy}>
      <span className="step">{mandatory ? 'PRIMER ACCESO / PASO 01 DE 01' : 'SEGURIDAD DE TU CUENTA'}</span>
      <h2>{mandatory ? 'Crea tu contraseña personal' : 'Cambiar contraseña'}</h2>
      <p className="muted small">Elige una contraseña que solo tú conozcas.</p>
      <Field label="Contraseña actual" type="password" autoComplete="current-password" required maxLength={128}
        value={form.current_password} onChange={e => update('current_password', e.target.value)} />
      {mandatory && <p className="hint password-hint">Usa la contraseña que te entregó la administración. Por defecto, es tu código.</p>}
      <Field label="Nueva contraseña" type="password" autoComplete="new-password" required minLength={8} maxLength={128}
        aria-describedby="password-rules" value={form.new_password} onChange={e => update('new_password', e.target.value)} />
      <p id="password-rules" className="hint password-hint">Al menos 8 caracteres. Debe ser diferente a la actual, no ser común ni contener solo números.</p>
      <Field label="Confirmar nueva contraseña" type="password" autoComplete="new-password" required minLength={8} maxLength={128}
        value={form.confirm_password} onChange={e => update('confirm_password', e.target.value)} />
      <Notice error>{error}</Notice>
      <Notice>{success}</Notice>
      <button className="primary full" disabled={busy}>
        {busy ? 'Guardando…' : mandatory ? 'Guardar y acceder a mi espacio' : 'Actualizar contraseña'}
        <span aria-hidden="true">↗</span>
      </button>
    </form>
  );
}
