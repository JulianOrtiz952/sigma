import React from 'react';
import AppHeader from '../components/AppHeader.jsx';
import PasswordForm from '../components/PasswordForm.jsx';

export default function FirstAccess({ user, logout, onUserChange }) {
  return (
    <>
      <AppHeader user={user} logout={logout} locked />
      <main className="workspace first-access page-enter">
        <section className="first-access-intro">
          <span className="security-mark" aria-hidden="true">✧</span>
          <p className="eyebrow">UN NUEVO COMIENZO, SOLO TUYO</p>
          <h1>Hola, {user.first_name}.<br /><em>Tu espacio te espera.</em></h1>
          <p className="description">Antes de continuar, cambia tu contraseña inicial para hacer tuya esta cuenta.</p>
          <div className="access-note"><span className="access-dot" aria-hidden="true" /><p>Este paso es obligatorio. Al completarlo podrás consultar tu información y acceder a tu espacio académico.</p></div>
        </section>
        <PasswordForm mandatory onChanged={onUserChange} />
      </main>
    </>
  );
}
