import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Notice, roles } from '../components/ui.jsx';

function ProfileItem({ label, children }) {
  return <div className="profile-item"><dt>{label}</dt><dd>{children || 'No registrado'}</dd></div>;
}
export default function MemberProfile() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api('profile/').then(data => { if (active) setProfile(data); })
      .catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  }, []);
  if (error) return <Notice error>{error}</Notice>;
  if (!profile) return <p role="status">Cargando tu información…</p>;
  const joined = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long' }).format(new Date(profile.date_joined));
  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">TU IDENTIDAD ACADÉMICA</p><h1>Mi información</h1><p className="muted">Todos los datos registrados en tu cuenta, en un solo lugar.</p></div></div>
      <div className="profile-layout">
        <aside className="profile-summary panel">
          <div className="profile-avatar" aria-hidden="true">{profile.first_name[0]}{profile.first_surname[0]}</div>
          <span className={`badge ${profile.role}`}>{roles[profile.role]}</span>
          <h2>{profile.first_name}<br />{profile.first_surname} {profile.second_surname}</h2>
          <p>{profile.university}</p>
          <span className="profile-code">Código {profile.code}</span>
        </aside>
        <div className="stack">
          <section className="panel"><span className="step">01 / DATOS PERSONALES</span><h2>Sobre ti</h2>
            <dl className="profile-details">
              <ProfileItem label="Nombres">{profile.first_name}</ProfileItem>
              <ProfileItem label="Primer apellido">{profile.first_surname}</ProfileItem>
              <ProfileItem label="Segundo apellido">{profile.second_surname}</ProfileItem>
              <ProfileItem label="Correo institucional">{profile.email}</ProfileItem>
            </dl>
          </section>
          <section className="panel"><span className="step">02 / VÍNCULO INSTITUCIONAL</span><h2>Tu comunidad</h2>
            <dl className="profile-details">
              <ProfileItem label="Universidad">{profile.university}</ProfileItem>
              <ProfileItem label="Dominio institucional">{profile.university_domain}</ProfileItem>
              <ProfileItem label="Rol">{roles[profile.role]}</ProfileItem>
              <ProfileItem label="Código">{String(profile.code)}</ProfileItem>
              {profile.role === 'student' && <ProfileItem label="Programa académico">{profile.academic_program}</ProfileItem>}
              <ProfileItem label="Fecha de registro">{joined}</ProfileItem>
              <ProfileItem label="Estado de la cuenta">{profile.is_active ? 'Activa' : 'Inactiva'}</ProfileItem>
            </dl>
          </section>
          <p className="hint">Si algún dato necesita una corrección, comunícate con la administración de tu institución.</p>
        </div>
      </div>
    </>
  );
}
