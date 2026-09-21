let csrfToken = '';

function describeError(data) {
  if (typeof data === 'string') return data;
  if (Array.isArray(data)) return data.map(describeError).join(' ');
  if (data && typeof data === 'object') return Object.values(data).map(describeError).join(' ');
  return 'No se pudo completar la solicitud.';
}

export async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...(method !== 'GET' ? { 'X-CSRFToken': csrfToken } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => ({ detail: 'El servidor no está disponible o la sesión caducó. Recarga la página.' }));
  if (!response.ok) {
    if (data.code === 'password_change_required') window.dispatchEvent(new Event('sigma:password-required'));
    throw new Error(describeError(data));
  }
  if (data.csrfToken) csrfToken = data.csrfToken;
  return data;
}

export function previewEmail(names, surname, secondSurname, domain) {
  const clean = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z]/g, '');
  if (!names.trim() || !surname.trim() || !secondSurname.trim() || !domain) return '';
  return `${names.trim().split(/\s+/).slice(0, 2).map(clean).join('')}${clean(surname)[0] || ''}${clean(secondSurname)[0] || ''}@${domain}`;
}
