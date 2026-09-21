import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Notice } from '../components/ui.jsx';
import AppHeader from '../components/AppHeader.jsx';
import Users from './Users.jsx';
import Universities from './Universities.jsx';
import Courses from './Courses.jsx';
import Records from './Records.jsx';

const navigation = [
  { id: 'users', label: 'Creación de usuarios' },
  { id: 'universities', label: 'Universidades' },
  { id: 'courses', label: 'Cursos' },
  { id: 'records', label: 'Registros' },
];

export default function AdminDashboard({ user, logout }) {
  const [section, setSection] = useState('users');
  const [data, setData] = useState({ universities: [], programs: [], users: [], teachers: [], courses: [] });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  async function refresh() {
    const [universities, programs, users, teachers, courses] = await Promise.all([api('universities/'), api('programs/'), api('users/'), api('teachers/'), api('courses/')]);
    setData({ universities, programs, users, teachers, courses });
    setError('');
  }
  useEffect(() => {
    refresh().catch(error => setError(error.message)).finally(() => setLoading(false));
  }, [user.id]);
  return (
    <>
      <AppHeader user={user} logout={logout} items={navigation} section={section} onNavigate={setSection} />
      <div className="workspace">
        <Notice error>{error}</Notice>
        {loading ? <p role="status">Cargando tu espacio…</p> : (
          <div key={section} className="page-enter">
            {section === 'users'
              ? <Users {...data} refresh={refresh} goUniversities={() => setSection('universities')} />
              : section === 'universities'
                ? <Universities {...data} refresh={refresh} canAffiliate={user.is_global_admin} />
                : section === 'courses'
                  ? <Courses {...data} refresh={refresh} />
                  : <Records {...data} refresh={refresh} />}
          </div>
        )}
      </div>
    </>
  );
}
