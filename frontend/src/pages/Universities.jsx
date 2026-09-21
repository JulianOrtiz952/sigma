import React, { useState } from 'react';
import { api } from '../api.js';
import { Field, Notice, UniversitySelect } from '../components/ui.jsx';

export default function Universities({ universities, programs, refresh, canAffiliate }) {
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
  return <>
    <div className="page-heading"><div><p className="eyebrow">COMUNIDAD ACADÉMICA</p><h1>Universidades</h1><p className="muted">Afiliación institucional y creación de programas. Consulta los existentes en Registros.</p></div></div>
    <Notice error>{error}</Notice><Notice>{success}</Notice>
    <div className="two-columns creation-grid">
      {canAffiliate && <form className="panel" onSubmit={e => submit(e, 'university')}><span className="step">01 / AFILIACIÓN</span><h2>Afiliar universidad</h2><Field label="Nombre de la universidad" placeholder="UFPS" maxLength={150} required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /><Field label="Dominio del correo institucional" placeholder="ufps.edu.co" maxLength={253} required value={form.email_domain} onChange={e => setForm({ ...form, email_domain: e.target.value })} /><p className="hint">Solo el dominio, sin @ ni https://. Se utilizará para generar los correos.</p><button disabled={!!busy} className="primary">{busy === 'university' ? 'Guardando…' : 'Afiliar universidad'}</button></form>}
      <form className="panel" onSubmit={e => submit(e, 'program')}><span className="step">02 / OFERTA ACADÉMICA</span><h2>Crear programa</h2><UniversitySelect universities={universities} value={program.university} onChange={e => setProgram({ ...program, university: e.target.value })} /><Field label="Nombre del programa" placeholder="Ingeniería de Sistemas" maxLength={150} required value={program.name} onChange={e => setProgram({ ...program, name: e.target.value })} /><button disabled={!!busy || !universities.length} className="primary">{busy === 'program' ? 'Guardando…' : 'Crear programa'}</button>{!universities.length && <p className="hint">Primero afilia una universidad.</p>}</form>
    </div>
  </>;
}
