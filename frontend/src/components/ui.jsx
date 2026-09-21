import React from 'react';

export const roles = { administrator: 'Administrador', teacher: 'Docente', student: 'Estudiante' };

export function Field({ label, children, ...props }) {
  return <label className="field"><span>{label}</span>{children || <input {...props} />}</label>;
}
export function Notice({ error, children }) {
  return children ? <div className={`notice ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>{children}</div> : null;
}
export function UniversitySelect({ universities, value, onChange, label = 'Universidad' }) {
  return <Field label={label}><select required value={value} onChange={onChange}><option value="">Selecciona una universidad</option>{universities.map(university => <option key={university.id} value={university.id}>{university.name}</option>)}</select></Field>;
}
