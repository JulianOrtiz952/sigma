import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Notice } from '../components/ui.jsx';

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => { api('notifications/').then(setItems).catch(requestError => setError(requestError.message)).finally(() => setLoading(false)); }, []);
  async function markRead(item) {
    if (item.read) return;
    try {
      await api(`notifications/${item.id}/read/`, { method: 'PATCH', body: {} });
      setItems(current => current.map(value => value.id === item.id ? { ...value, read: true } : value));
    } catch (requestError) { setError(requestError.message); }
  }
  return <>
    <div className="page-heading"><div><p className="eyebrow">ACTUALIZACIONES ACADÉMICAS</p><h1>Notificaciones</h1><p className="muted">Asignaciones de cupo y novedades de tu lista de espera.</p></div><span className="count">{items.filter(item => !item.read).length} sin leer</span></div>
    <Notice error>{error}</Notice>
    {loading ? <p role="status">Cargando notificaciones…</p> : !items.length ? <div className="panel empty"><span aria-hidden="true">◇</span><h3>Sin novedades</h3><p>Te avisaremos aquí cuando cambie una solicitud.</p></div> : <div className="notification-list">{items.map(item => <button type="button" className={`notification-card ${item.read ? 'read' : 'unread'}`} key={item.id} onClick={() => markRead(item)}><span className="notification-dot" aria-hidden="true" /><div><h3>{item.title}</h3><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString('es-CO')}</time></div></button>)}</div>}
  </>;
}
