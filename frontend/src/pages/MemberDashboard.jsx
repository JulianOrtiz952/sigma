import React, { useState } from 'react';
import AppHeader from '../components/AppHeader.jsx';
import PasswordForm from '../components/PasswordForm.jsx';
import { roles } from '../components/ui.jsx';
import MemberProfile from './MemberProfile.jsx';
import StudentCourses from './StudentCourses.jsx';
import Schedule from './Schedule.jsx';
import Notifications from './Notifications.jsx';

const baseNavigation = [
  { id: 'home', label: 'Mi espacio' },
  { id: 'profile', label: 'Mi información' },
  { id: 'security', label: 'Seguridad' },
];
export default function MemberDashboard({ user, logout, onUserChange }) {
  const [section, setSection] = useState('home');
  const navigation = user.role === 'student'
    ? [...baseNavigation.slice(0, 1), { id: 'courses', label: 'Cursos' }, { id: 'schedule', label: 'Horario' }, { id: 'notifications', label: 'Notificaciones' }, ...baseNavigation.slice(1)]
    : [...baseNavigation.slice(0, 1), { id: 'schedule', label: 'Horario' }, ...baseNavigation.slice(1)];
  return (
    <>
      <AppHeader user={user} logout={logout} items={navigation} section={section} onNavigate={setSection} />
      <main className="workspace">
        <div key={section} className="page-enter">
          {section === 'profile' ? <MemberProfile /> : section === 'courses' ? <StudentCourses /> : section === 'schedule' ? <Schedule role={user.role} /> : section === 'notifications' ? <Notifications /> : section === 'security' ? (
            <>
              <div className="page-heading"><div><p className="eyebrow">TRANQUILIDAD PARA CONTINUAR</p><h1>Seguridad</h1><p className="muted">Tu cuenta, bajo tu control.</p></div></div>
              <div className="security-layout"><PasswordForm onChanged={onUserChange} /><aside className="security-advice"><span className="security-mark" aria-hidden="true">✧</span><h2>Un acceso solo tuyo.</h2><p>Tu contraseña es personal. No la compartas ni utilices la misma de otros servicios.</p><p>Al actualizarla, mantendremos esta sesión abierta y cerraremos el acceso de tus otras sesiones.</p></aside></div>
            </>
          ) : (
            <>
              <section className="member-hero">
                <div><p className="eyebrow">{roles[user.role].toUpperCase()} / SIGMA</p><h1>Bienvenido,<br /><em>{user.first_name}.</em></h1><p className="description">Un espacio para tu vida académica.</p><div className="university-pill"><span aria-hidden="true">▧</span>{user.university}</div></div>
                <div className="member-emblem" aria-hidden="true">σ<span>CONOCIMIENTO QUE CONECTA</span></div>
              </section>
              <div className="member-actions">
                <button className="action-card" onClick={() => setSection('profile')}><span className="step">01 / IDENTIDAD</span><h2>Mi información <span aria-hidden="true">↗</span></h2><p>Consulta tus datos personales y tu vínculo con la universidad.</p></button>
                {user.role === 'student' && <button className="action-card" onClick={() => setSection('courses')}><span className="step">02 / MATRÍCULA</span><h2>Cursos <span aria-hidden="true">↗</span></h2><p>Consulta la oferta de tu pensum y solicita un cupo.</p></button>}
                <button className="action-card" onClick={() => setSection('schedule')}><span className="step">03 / AGENDA</span><h2>Horario <span aria-hidden="true">↗</span></h2><p>Consulta tus bloques semanales en una cuadrícula.</p></button>
                {user.role === 'student' && <button className="action-card" onClick={() => setSection('notifications')}><span className="step">04 / NOVEDADES</span><h2>Notificaciones <span aria-hidden="true">↗</span></h2><p>Revisa cambios de cupo y cruces de horario.</p></button>}
                <button className="action-card" onClick={() => setSection('security')}><span className="step">02 / PRIVACIDAD</span><h2>Seguridad <span aria-hidden="true">↗</span></h2><p>Actualiza tu contraseña y mantén el control de tu acceso.</p></button>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
