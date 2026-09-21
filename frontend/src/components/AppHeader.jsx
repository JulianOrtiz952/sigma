import React from 'react';
import { roles } from './ui.jsx';

export default function AppHeader({ user, logout, items = [], section, onNavigate, locked = false }) {
  return (
    <header className="app-header">
      {locked ? <span className="brand">σ <span>SIGMA</span></span> : <a href="/" className="brand">σ <span>SIGMA</span></a>}
      {!locked && items.length > 0 && (
        <nav aria-label="Navegación principal">
          {items.map(item => (
            <button key={item.id} className={section === item.id ? 'active' : ''}
              aria-current={section === item.id ? 'page' : undefined}
              onClick={() => onNavigate(item.id)}>{item.label}</button>
          ))}
        </nav>
      )}
      <div className="session">
        <span><strong>{user.first_name || user.username}</strong><small>{roles[user.role]}</small></span>
        <button className="secondary" onClick={logout}>Salir</button>
      </div>
    </header>
  );
}
