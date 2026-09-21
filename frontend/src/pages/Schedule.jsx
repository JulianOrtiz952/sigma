import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';
import { Notice } from '../components/ui.jsx';

const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const toMinutes = value => { const [hours, minutes] = value.split(':').map(Number); return hours * 60 + minutes; };
const labelTime = minutes => `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;

export default function Schedule({ role }) {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => { api('schedule/').then(setBlocks).catch(requestError => setError(requestError.message)).finally(() => setLoading(false)); }, []);
  const range = useMemo(() => {
    if (!blocks.length) return { start: 6 * 60, end: 22 * 60 };
    return {
      start: Math.min(6 * 60, ...blocks.map(block => Math.floor(toMinutes(block.start_time) / 30) * 30)),
      end: Math.max(22 * 60, ...blocks.map(block => Math.ceil(toMinutes(block.end_time) / 30) * 30)),
    };
  }, [blocks]);
  const slots = [];
  for (let value = range.start; value < range.end; value += 30) slots.push(value);

  return <>
    <div className="page-heading"><div><p className="eyebrow">AGENDA SEMANAL</p><h1>Horario</h1><p className="muted">{role === 'teacher' ? 'Grupos que tienes asignados.' : 'Materias con matrícula confirmada.'}</p></div><span className="count">{blocks.length} bloques</span></div>
    <Notice error>{error}</Notice>
    {loading ? <p role="status">Cargando horario…</p> : !blocks.length ? <div className="panel empty"><span aria-hidden="true">▦</span><h3>Tu horario está libre</h3><p>Los grupos asignados aparecerán en esta cuadrícula.</p></div> : <div className="schedule-table-wrap panel"><table className="schedule-table"><thead><tr><th>Hora</th>{days.map(day => <th key={day}>{day}</th>)}</tr></thead><tbody>{slots.map(slot => <tr key={slot}><th>{labelTime(slot)}</th>{days.map((day, dayIndex) => {
      const matches = blocks.filter(block => block.day_of_week === dayIndex && toMinutes(block.start_time) < slot + 30 && slot < toMinutes(block.end_time));
      return <td key={day} className={matches.length ? 'scheduled-cell' : ''}>{matches.map(block => <div className="schedule-entry" key={block.id}>{slot <= toMinutes(block.start_time) && toMinutes(block.start_time) < slot + 30 ? <><strong>{block.course} {block.section}</strong><span>{block.start_time}–{block.end_time}</span>{role === 'student' && <small>{block.teacher}</small>}</> : <span aria-hidden="true">·</span>}</div>)}</td>;
    })}</tr>)}</tbody></table></div>}
  </>;
}
