import React, { useMemo, useState } from 'react';
import { api } from '../api.js';
import { Notice, roles } from '../components/ui.jsx';

const statusNames = { open: 'Abierto', active: 'Activo', finished: 'Finalizado' };
const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const sections = [
  { id: 'users', label: 'Usuarios' },
  { id: 'institutions', label: 'Instituciones' },
  { id: 'courses', label: 'Cursos' },
];

function searchable(...values) {
  return values.filter(Boolean).join(' ').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function GroupEditor({ group, teachers, onSaved, onCancel }) {
  const currentTeacher = teachers.find(teacher => teacher.id === group.teacher);
  const availableTeachers = teachers.filter(teacher => teacher.university === currentTeacher?.university);
  const [form, setForm] = useState({
    teacher: String(group.teacher), capacity: String(group.capacity),
    schedules: group.schedules.length ? group.schedules.map(block => ({ day_of_week: String(block.day_of_week), start_time: block.start_time, end_time: block.end_time })) : [{ day_of_week: '0', start_time: '08:00', end_time: '11:00' }],
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  function updateBlock(index, key, value) { setForm(current => ({ ...current, schedules: current.schedules.map((block, position) => position === index ? { ...block, [key]: value } : block) })); }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await api(`groups/${group.id}/`, { method: 'PATCH', body: { teacher: Number(form.teacher), capacity: Number(form.capacity), schedules: form.schedules.map(block => ({ ...block, day_of_week: Number(block.day_of_week) })) } });
      await onSaved();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }
  return <form className="group-editor" onSubmit={submit}><Notice error>{error}</Notice><div className="form-row"><label className="field"><span>Docente</span><select required value={form.teacher} onChange={event => setForm({ ...form, teacher: event.target.value })}>{availableTeachers.map(teacher => <option key={teacher.id} value={teacher.id}>{teacher.name}</option>)}</select></label><label className="field"><span>Cupo</span><input required type="number" min="1" value={form.capacity} onChange={event => setForm({ ...form, capacity: event.target.value })} /></label></div>{form.schedules.map((block, index) => <div className="schedule-row compact" key={index}><label className="field"><span>Día</span><select value={block.day_of_week} onChange={event => updateBlock(index, 'day_of_week', event.target.value)}>{days.map((day, dayIndex) => <option value={dayIndex} key={day}>{day}</option>)}</select></label><label className="field"><span>Inicio</span><input type="time" required value={block.start_time} onChange={event => updateBlock(index, 'start_time', event.target.value)} /></label><label className="field"><span>Fin</span><input type="time" required value={block.end_time} onChange={event => updateBlock(index, 'end_time', event.target.value)} /></label><button type="button" className="remove-block" disabled={form.schedules.length === 1} onClick={() => setForm(current => ({ ...current, schedules: current.schedules.filter((_, position) => position !== index) }))}>×</button></div>)}<button type="button" className="text-button" onClick={() => setForm(current => ({ ...current, schedules: [...current.schedules, { day_of_week: '0', start_time: '08:00', end_time: '10:00' }] }))}>+ Añadir bloque</button><div className="editor-actions"><button type="button" className="secondary" onClick={onCancel}>Cancelar</button><button className="primary" disabled={busy}>{busy ? 'Guardando…' : 'Guardar horario'}</button></div></form>;
}

export default function Records({ users, universities, programs, courses, teachers, refresh }) {
  const [section, setSection] = useState('users');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingGroup, setEditingGroup] = useState(null);
  const needle = searchable(query);

  const visibleUsers = useMemo(() => users.filter(user => searchable(
    user.first_name, user.first_surname, user.second_surname, user.email,
    roles[user.role], user.university, user.academic_program, user.code,
  ).includes(needle)), [users, needle]);
  const visibleUniversities = useMemo(() => universities.filter(university => searchable(
    university.name, university.email_domain,
    ...programs.filter(program => program.university === university.id).map(program => program.name),
  ).includes(needle)), [universities, programs, needle]);
  const visibleCourses = useMemo(() => courses.filter(course => searchable(
    course.name, course.code, course.program, course.university, course.semester,
    ...course.groups.flatMap(group => [group.teacher_name, group.section, statusNames[group.status], ...group.schedules.map(block => `${block.day} ${block.start_time} ${block.end_time}`)]),
  ).includes(needle)), [courses, needle]);

  const counts = { users: users.length, institutions: universities.length, courses: courses.length };
  const placeholders = { users: 'Buscar por nombre, correo, rol o código', institutions: 'Buscar universidad, dominio o programa', courses: 'Buscar curso, docente, programa o estado' };

  function selectSection(nextSection) {
    setSection(nextSection); setQuery(''); setError(''); setSuccess('');
  }

  async function changeStatus(groupId, status) {
    setBusy(true); setError(''); setSuccess('');
    try {
      await api(`groups/${groupId}/status/`, { method: 'PATCH', body: { status } });
      await refresh(); setSuccess(`Estado actualizado a ${statusNames[status].toLowerCase()}.`);
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><p className="eyebrow">DIRECTORIO ADMINISTRATIVO</p><h1>Registros</h1><p className="muted">Consulta y gestiona la información existente sin saturar los formularios de creación.</p></div><span className="count">{counts[section]} registros</span></div>
    <Notice error>{error}</Notice><Notice>{success}</Notice>
    <div className="records-toolbar">
      <div className="segmented records-tabs" aria-label="Tipo de registro">{sections.map(item => <button key={item.id} type="button" aria-pressed={section === item.id} className={section === item.id ? 'selected' : ''} onClick={() => selectSection(item.id)}>{item.label}<span>{counts[item.id]}</span></button>)}</div>
      <label className="record-search"><span className="sr-only">Buscar registros</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={placeholders[section]} /></label>
    </div>

    {section === 'users' && <section className="panel records-panel">
      {!visibleUsers.length ? <div className="empty"><span aria-hidden="true">♧</span><h3>Sin resultados</h3><p>No hay cuentas que coincidan con la búsqueda.</p></div> : <div className="records-grid user-records">{visibleUsers.map(user => <article className="record-card" key={user.id}><div className="user-card-top"><h3>{user.first_name} {user.first_surname} {user.second_surname}</h3><span className={`badge ${user.role}`}>{roles[user.role]}</span></div><p className="user-email">{user.email}</p><p className="record-meta">Código {user.code} · {user.university}</p>{user.academic_program && <p className="record-meta">{user.academic_program}</p>}</article>)}</div>}
    </section>}

    {section === 'institutions' && <section className="panel records-panel">
      {!visibleUniversities.length ? <div className="empty"><span aria-hidden="true">▧</span><h3>Sin resultados</h3><p>No hay instituciones que coincidan con la búsqueda.</p></div> : <div className="records-grid institution-records">{visibleUniversities.map(university => <article key={university.id} className="record-card institution"><div className="institution-title"><span className="institution-icon" aria-hidden="true">{university.name.slice(0, 2).toUpperCase()}</span><div><h3>{university.name}</h3><p>@{university.email_domain}</p></div></div><div className="tags">{programs.filter(program => program.university === university.id).map(program => <span key={program.id}>{program.name}</span>)}{!programs.some(program => program.university === university.id) && <p className="hint">Sin programas registrados.</p>}</div></article>)}</div>}
    </section>}

    {section === 'courses' && <section className="panel records-panel">
      {!visibleCourses.length ? <div className="empty"><span aria-hidden="true">◇</span><h3>Sin resultados</h3><p>No hay cursos que coincidan con la búsqueda.</p></div> : <div className="course-list records-course-list">{visibleCourses.map(course => <article className="course-card course-record" key={course.id}>
        <div className="course-card-heading"><div><span className="step">CÓDIGO {course.code} · SEMESTRE {course.semester}</span><h3>{course.name}</h3><p>{course.program} · {course.credits} créditos · {course.academic_hours} horas</p></div><span className="badge">{course.groups.length} {course.groups.length === 1 ? 'grupo' : 'grupos'}</span></div>
        <p className="hint">Prerrequisitos: {course.prerequisites.length ? course.prerequisites.map(item => item.name).join(', ') : 'ninguna materia'}{course.minimum_approved_credits ? ` · ${course.minimum_approved_credits} créditos aprobados` : ''}</p>
        <div className="group-records">{course.groups.map(group => <section className="group-record" key={group.id}>
          <div className="group-record-title"><div><strong>Grupo {group.section}</strong><span>{group.teacher_name}</span></div><span className={`badge status-${group.status}`}>{statusNames[group.status]}</span></div>
          <div className="schedule-chips">{group.schedules.map(block => <span key={block.id}>{block.day} · {block.start_time}–{block.end_time}</span>)}</div>
          <div className="occupancy"><span><strong>{group.confirmed}</strong> confirmados</span><span><strong>{group.available_seats}</strong> disponibles</span><span><strong>{group.waitlist}</strong> en espera</span><span><strong>{group.capacity}</strong> cupos</span></div>
          {editingGroup === group.id ? <GroupEditor group={group} teachers={teachers} onCancel={() => setEditingGroup(null)} onSaved={async () => { await refresh(); setEditingGroup(null); setSuccess('Horario del grupo actualizado.'); }} /> : <div className="course-actions"><button type="button" className="secondary" onClick={() => setEditingGroup(group.id)}>Editar grupo</button>{group.status !== 'open' && <button type="button" className="secondary" disabled={busy} onClick={() => changeStatus(group.id, 'open')}>Abrir</button>}{group.status !== 'active' && <button type="button" className="secondary" disabled={busy} onClick={() => changeStatus(group.id, 'active')}>Activar</button>}{group.status !== 'finished' && <button type="button" className="text-button" disabled={busy} onClick={() => changeStatus(group.id, 'finished')}>Finalizar</button>}</div>}
        </section>)}</div>
      </article>)}</div>}
    </section>}
  </>;
}
