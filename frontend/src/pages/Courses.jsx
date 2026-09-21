import React, { useMemo, useState } from 'react';
import { api } from '../api.js';
import { Field, Notice, UniversitySelect } from '../components/ui.jsx';

const emptyCourse = {
  name: '', university: '', program: '', academic_hours: '', credits: '', semester: '',
  minimum_approved_credits: '0', prerequisites: [], teacher: '', capacity: '',
  schedules: [{ day_of_week: '0', start_time: '08:00', end_time: '11:00' }],
};
const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export default function Courses({ universities, programs, teachers, courses, refresh }) {
  const [form, setForm] = useState(emptyCourse);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const availablePrograms = programs.filter(item => item.university === Number(form.university) && item.curriculum);
  const availableTeachers = teachers.filter(item => item.university === Number(form.university));
  const selectedProgram = programs.find(item => item.id === Number(form.program));
  const prerequisiteOptions = useMemo(() => courses.filter(item =>
    item.curriculum === selectedProgram?.curriculum?.id && item.semester < Number(form.semester || 0)
  ), [courses, selectedProgram, form.semester]);

  function update(key, value) {
    setForm(current => ({
      ...current,
      [key]: value,
      ...(key === 'university' ? { program: '', teacher: '', prerequisites: [] } : {}),
      ...(['program', 'semester'].includes(key) ? { prerequisites: [] } : {}),
    }));
  }

  function updateSchedule(index, key, value) {
    setForm(current => ({ ...current, schedules: current.schedules.map((block, position) => position === index ? { ...block, [key]: value } : block) }));
  }

  function addSchedule() {
    setForm(current => ({ ...current, schedules: [...current.schedules, { day_of_week: '0', start_time: '08:00', end_time: '10:00' }] }));
  }

  function removeSchedule(index) {
    setForm(current => ({ ...current, schedules: current.schedules.filter((_, position) => position !== index) }));
  }

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); setSuccess('');
    try {
      const existing = courses.find(course => course.curriculum === selectedProgram.curriculum.id && course.name.trim().toLowerCase() === form.name.trim().toLowerCase());
      if (existing && !window.confirm(`La materia ${existing.name} ya existe. ¿Deseas crear un grupo con horario diferente? Se asignará automáticamente la siguiente letra.`)) {
        setBusy(false); return;
      }
      const groupFields = {
        teacher: Number(form.teacher),
        capacity: Number(form.capacity),
        schedules: form.schedules.map(block => ({ ...block, day_of_week: Number(block.day_of_week) })),
      };
      const result = await api(existing ? `courses/${existing.id}/groups/` : 'courses/', { method: 'POST', body: existing ? groupFields : {
        name: form.name,
        curriculum: selectedProgram.curriculum.id,
        academic_hours: Number(form.academic_hours),
        credits: Number(form.credits),
        semester: Number(form.semester),
        minimum_approved_credits: Number(form.minimum_approved_credits),
        prerequisites: form.prerequisites.map(Number),
        ...groupFields,
      }});
      const createdGroup = result.groups[result.groups.length - 1];
      setForm({ ...emptyCourse, schedules: [{ ...emptyCourse.schedules[0] }] }); await refresh();
      setSuccess(existing ? `Grupo ${createdGroup.section} creado con su nuevo horario.` : 'Curso y grupo A creados en estado abierto.');
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><p className="eyebrow">OFERTA ACADÉMICA</p><h1>Cursos</h1><p className="muted">Crea materias, prerrequisitos, docentes y cupos. Gestiona la oferta existente en Registros.</p></div></div>
    <Notice error>{error}</Notice><Notice>{success}</Notice>
    <div className="form-shell"><form className="panel" onSubmit={submit}>
        <span className="step">01 / NUEVO CURSO</span><h2>Crear curso</h2>
        <UniversitySelect universities={universities} value={form.university} onChange={event => update('university', event.target.value)} />
        <Field label="Pensum / programa"><select required value={form.program} onChange={event => update('program', event.target.value)}><option value="">Selecciona un programa</option>{availablePrograms.map(program => <option key={program.id} value={program.id}>{program.name}</option>)}</select></Field>
        <Field label="Nombre de la materia" required maxLength={150} value={form.name} onChange={event => update('name', event.target.value)} placeholder="Programación I" />
        <div className="form-row"><Field label="Semestre" required type="number" min="1" value={form.semester} onChange={event => update('semester', event.target.value)} /><Field label="Créditos" required type="number" min="1" value={form.credits} onChange={event => update('credits', event.target.value)} /></div>
        <div className="form-row"><Field label="Horas académicas" required type="number" min="1" value={form.academic_hours} onChange={event => update('academic_hours', event.target.value)} /><Field label="Créditos aprobados requeridos" type="number" min="0" value={form.minimum_approved_credits} onChange={event => update('minimum_approved_credits', event.target.value)} /></div>
        <Field label="Materias prerrequisito"><select multiple value={form.prerequisites} onChange={event => update('prerequisites', [...event.target.selectedOptions].map(option => option.value))}>{prerequisiteOptions.map(course => <option key={course.id} value={course.id}>{course.name} · semestre {course.semester}</option>)}</select></Field>
        <p className="hint">Solo aparecen materias del mismo pensum y de semestres anteriores. Usa Ctrl para seleccionar varias.</p>
        <Field label="Docente"><select required value={form.teacher} onChange={event => update('teacher', event.target.value)}><option value="">Selecciona un docente</option>{availableTeachers.map(teacher => <option key={teacher.id} value={teacher.id}>{teacher.name} · {teacher.email}</option>)}</select></Field>
        <Field label="Cupo máximo" required type="number" min="1" value={form.capacity} onChange={event => update('capacity', event.target.value)} />
        <div className="schedule-builder"><div className="schedule-builder-title"><div><span className="step">BLOQUES SEMANALES</span><h3>Horario del grupo</h3></div><button type="button" className="secondary" onClick={addSchedule}>+ Añadir bloque</button></div>
          {form.schedules.map((block, index) => <div className="schedule-row" key={index}>
            <Field label={`Día ${index + 1}`}><select required value={block.day_of_week} onChange={event => updateSchedule(index, 'day_of_week', event.target.value)}>{days.map((day, dayIndex) => <option value={dayIndex} key={day}>{day}</option>)}</select></Field>
            <Field label="Inicio" type="time" required value={block.start_time} onChange={event => updateSchedule(index, 'start_time', event.target.value)} />
            <Field label="Fin" type="time" required value={block.end_time} onChange={event => updateSchedule(index, 'end_time', event.target.value)} />
            <button type="button" className="remove-block" disabled={form.schedules.length === 1} onClick={() => removeSchedule(index)} aria-label={`Eliminar bloque ${index + 1}`}>×</button>
          </div>)}
        </div>
        <button className="primary full" disabled={busy || !availablePrograms.length || !availableTeachers.length}>{busy ? 'Guardando…' : 'Crear curso abierto'}</button>
        {form.university && !availableTeachers.length && <p className="hint">Crea primero al menos un docente de esta universidad.</p>}
      </form></div>
  </>;
}
