import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Notice } from '../components/ui.jsx';

const statusNames = { open: 'Abierto', active: 'Activo', finished: 'Finalizado' };
const enrollmentNames = { confirmed: 'Matrícula confirmada', waitlisted: 'En lista de espera', cancelled: 'Cancelada' };

export default function StudentCourses() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function load() {
    const result = await api('courses/'); setCourses(result); setError('');
  }
  useEffect(() => { load().catch(requestError => setError(requestError.message)).finally(() => setLoading(false)); }, []);

  async function enroll(groupId) {
    setBusy(groupId); setError(''); setSuccess('');
    try {
      const result = await api(`groups/${groupId}/enroll/`, { method: 'POST', body: {} });
      setSuccess(result.detail); await load();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(null); }
  }

  async function cancel(enrollment) {
    const label = enrollment.status === 'confirmed' ? 'esta materia' : 'tu lugar en la lista de espera';
    if (!window.confirm(`¿Deseas cancelar ${label}?`)) return;
    setBusy(enrollment.id); setError(''); setSuccess('');
    try {
      const result = await api(`enrollments/${enrollment.id}/`, { method: 'DELETE' });
      setSuccess(result.detail); await load();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(null); }
  }

  return <>
    <div className="page-heading"><div><p className="eyebrow">MI PENSUM</p><h1>Cursos disponibles</h1><p className="muted">Solo ves materias autorizadas para tu programa académico.</p></div><span className="count">{courses.length} cursos</span></div>
    <Notice error>{error}</Notice><Notice>{success}</Notice>
    {loading ? <p role="status">Cargando cursos…</p> : !courses.length ? <div className="panel empty"><span aria-hidden="true">◇</span><h3>No hay cursos publicados</h3><p>La oferta de tu pensum aparecerá aquí.</p></div> : <div className="student-course-grid">{courses.flatMap(course => course.groups.map(group => <article className="panel student-course" key={group.id}>
      <div className="course-card-heading"><div><span className="step">CÓDIGO {course.code} · SEMESTRE {course.semester}</span><h2>{course.name} {group.section}</h2><p className="muted">{course.credits} créditos · {course.academic_hours} horas</p></div><span className={`badge status-${group.status}`}>{statusNames[group.status]}</span></div>
      <p>Docente: <strong>{group.teacher_name}</strong></p>
      <div className="schedule-chips">{group.schedules.map(block => <span key={block.id}>{block.day} · {block.start_time}–{block.end_time}</span>)}</div>
      <div className="occupancy"><span><strong>{group.available_seats}</strong> disponibles</span><span><strong>{group.capacity}</strong> cupos</span><span><strong>{group.waitlist}</strong> en espera</span></div>
      <p className="hint">Prerrequisitos: {course.prerequisites.length ? course.prerequisites.map(item => item.name).join(', ') : 'ninguna materia'}{course.minimum_approved_credits ? ` · ${course.minimum_approved_credits} créditos aprobados` : ''}</p>
      {group.enrollment ? <><div className="enrollment-state">{enrollmentNames[group.enrollment.status]}{group.enrollment.waitlist_position ? ` · posición ${group.enrollment.waitlist_position}` : ''}</div><button className="cancel-enrollment" disabled={busy === group.enrollment.id} onClick={() => cancel(group.enrollment)}>{busy === group.enrollment.id ? 'Cancelando…' : group.enrollment.status === 'confirmed' ? 'Cancelar materia' : 'Salir de lista de espera'}</button></> : <button className="primary full" disabled={busy === group.id || group.status === 'finished' || !group.schedules.length} onClick={() => enroll(group.id)}>{!group.schedules.length ? 'Horario pendiente' : busy === group.id ? 'Procesando…' : group.available_seats ? 'Solicitar matrícula' : 'Entrar a lista de espera'}</button>}
    </article>))}</div>}
  </>;
}
