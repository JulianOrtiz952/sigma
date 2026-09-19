from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import Administrator, AcademicProgram, University, Student, Teacher

User = get_user_model()


class AccountFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_user(username='test-admin', password='LocalTest!4396', role='administrator')
        Administrator.objects.create(user=self.admin, is_global=True)
        self.university = University.objects.create(name='Universidad de prueba', email_domain='test.example.edu')
        self.other = University.objects.create(name='Otra universidad', email_domain='other.example.edu')
        self.program = AcademicProgram.objects.create(name='Sistemas', university=self.university)
        self.other_program = AcademicProgram.objects.create(name='Sistemas', university=self.other)
        self.client.force_authenticate(self.admin)
        self.payload = {'role': 'student', 'first_name': 'Andrés Julián', 'first_surname': 'Ortiz', 'second_surname': 'Jaimes', 'university': self.university.pk, 'academic_program': self.program.pk}

    def create_account(self, **changes):
        return self.client.post('/api/auth/signup/', self.payload | changes, format='json')

    def test_student_code_email_and_hashed_password(self):
        response = self.create_account()
        self.assertEqual(response.status_code, 201, response.data)
        student = Student.objects.get()
        self.assertEqual(response.data['email'], 'andresjulianoj@test.example.edu')
        self.assertEqual(response.data['code'], student.pk)
        self.assertTrue(student.user.check_password(str(student.pk)))
        self.assertNotEqual(student.user.password, str(student.pk))
        self.assertNotIn('password', response.data)
        self.assertEqual(student.university, self.university)
        self.assertFalse(student.user.is_staff)
        self.assertFalse(student.user.is_superuser)

    def test_teacher_uses_own_incremental_id(self):
        response = self.create_account(role='teacher', academic_program=None)
        self.assertEqual(response.status_code, 201, response.data)
        teacher = Teacher.objects.get()
        self.assertEqual(response.data['code'], teacher.pk)
        self.assertTrue(teacher.user.check_password(str(teacher.pk)))

    def test_custom_password_is_hashed_and_never_returned(self):
        response = self.create_account(password='CustomOnly!42719')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Student.objects.get().user.check_password('CustomOnly!42719'))
        self.assertNotIn('password', response.data)
        self.assertNotIn('CustomOnly', str(self.client.get('/api/users/').data))

    def test_weak_custom_password_rolls_back_user_and_profile(self):
        before = User.objects.count()
        response = self.create_account(password='abc')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), before)
        self.assertEqual(Student.objects.count(), 0)

    def test_cross_university_program_rejected(self):
        response = self.create_account(academic_program=self.other_program.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Student.objects.count(), 0)

    def test_student_requires_program(self):
        self.assertEqual(self.create_account(academic_program=None).status_code, 400)

    def test_teacher_cannot_have_program(self):
        self.assertEqual(self.create_account(role='teacher').status_code, 400)

    def test_no_role_escalation(self):
        self.assertEqual(self.create_account(role='administrator').status_code, 400)
        self.assertEqual(self.create_account(is_superuser=True).status_code, 400)
        self.assertEqual(self.create_account(is_staff=True).status_code, 400)
        self.assertEqual(Administrator.objects.count(), 1)

    def test_duplicate_email_does_not_create_extra_user(self):
        self.assertEqual(self.create_account().status_code, 201)
        before = User.objects.count()
        self.assertEqual(self.create_account().status_code, 400)
        self.assertEqual(User.objects.count(), before)

    def test_only_first_two_names_used(self):
        response = self.create_account(first_name='Andrés Julián David')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['email'], 'andresjulianoj@test.example.edu')

    def test_single_name_supported_and_both_surnames_required(self):
        response = self.create_account(first_name='Ana')
        self.assertEqual(response.data['email'], 'anaoj@test.example.edu')
        self.assertEqual(self.create_account(second_surname='').status_code, 400)

    def test_anonymous_cannot_register_or_read_admin_data(self):
        self.client.force_authenticate(None)
        for path in ['/api/users/', '/api/auth/signup/', '/api/universities/', '/api/programs/']:
            self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.post(path, {}, format='json').status_code, 403)

    def test_student_and_teacher_cannot_access_administration(self):
        for role in ['student', 'teacher']:
            user = User.objects.create_user(username=role, role=role)
            self.client.force_authenticate(user)
            for path in ['/api/users/', '/api/auth/signup/', '/api/universities/', '/api/programs/']:
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 403)

    def test_scoped_admin_cannot_cross_institution_boundary(self):
        scoped = User.objects.create_user(username='scoped', role='administrator')
        profile = Administrator.objects.create(user=scoped)
        profile.universities.add(self.university)
        self.create_account()
        self.create_account(first_name='Otro', university=self.other.pk, academic_program=self.other_program.pk)
        self.client.force_authenticate(scoped)
        self.assertEqual(len(self.client.get('/api/universities/').data), 1)
        self.assertEqual(len(self.client.get('/api/programs/').data), 1)
        self.assertEqual(len(self.client.get('/api/users/').data), 1)
        self.assertEqual(self.create_account(first_name='Nuevo', university=self.other.pk, academic_program=self.other_program.pk).status_code, 400)
        self.assertEqual(self.client.post('/api/universities/', {'name': 'No autorizada', 'email_domain': 'no.example.edu'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/programs/', {'name': 'No autorizado', 'university': self.other.pk}, format='json').status_code, 400)

    def test_admin_without_assigned_universities_has_no_access(self):
        admin = User.objects.create_user(username='limited', role='administrator')
        Administrator.objects.create(user=admin)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/universities/').data, [])
        self.assertEqual(self.create_account().status_code, 400)

    def test_domain_normalization_and_duplicate(self):
        response = self.client.post('/api/universities/', {'name': 'UFPS', 'email_domain': 'UFPS.EDU.CO'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['email_domain'], 'ufps.edu.co')
        response = self.client.post('/api/universities/', {'name': 'Otro nombre', 'email_domain': 'UFPS.EDU.CO'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_domains_rejected(self):
        for domain in ['@ufps.edu.co', 'https://ufps.edu.co', 'ufps.edu.co/path', 'ufps', '-ufps.edu.co', 'ufps..edu.co']:
            response = self.client.post('/api/universities/', {'name': 'Invalid', 'email_domain': domain}, format='json')
            self.assertEqual(response.status_code, 400, domain)

    def test_program_duplicates_only_within_same_university(self):
        response = self.client.post('/api/programs/', {'name': 'SISTEMAS', 'university': self.university.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/programs/', {'name': 'Psicología', 'university': self.university.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_login_csrf_session_and_logout(self):
        browser = APIClient(enforce_csrf_checks=True)
        credentials = {'username': 'test-admin', 'password': 'LocalTest!4396'}
        self.assertEqual(browser.post('/api/auth/login/', credentials, format='json').status_code, 403)
        token = browser.get('/api/auth/session/').data['csrfToken']
        response = browser.post('/api/auth/login/', credentials, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.cookies['sessionid']['httponly'])
        self.assertEqual(browser.get('/api/auth/session/').data['user']['username'], 'test-admin')
        self.assertEqual(browser.post('/api/universities/', {'name': 'CSRF', 'email_domain': 'csrf.example.edu'}, format='json').status_code, 403)
        response = browser.post('/api/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=response.data['csrfToken'])
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(browser.get('/api/auth/session/').data['user'])
        self.assertEqual(browser.get('/api/users/').status_code, 403)

    def test_new_student_can_login_with_code_and_sees_only_own_profile(self):
        created = self.create_account().data
        browser = APIClient(enforce_csrf_checks=True)
        token = browser.get('/api/auth/session/').data['csrfToken']
        response = browser.post('/api/auth/login/', {'username': created['email'].upper(), 'password': str(created['code'])}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['user']['code'], created['code'])
        self.assertEqual(browser.get('/api/users/').status_code, 403)

    def test_bad_login_and_inactive_user(self):
        browser = APIClient(enforce_csrf_checks=True)
        token = browser.get('/api/auth/session/').data['csrfToken']
        self.assertEqual(browser.post('/api/auth/login/', {'username': 'test-admin', 'password': 'wrong'}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.admin.is_active = False
        self.admin.save()
        self.assertEqual(browser.post('/api/auth/login/', {'username': 'test-admin', 'password': 'LocalTest!4396'}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 400)

    def test_login_throttle(self):
        browser = APIClient()
        for _ in range(10):
            self.assertEqual(browser.post('/api/auth/login/', {}, format='json').status_code, 400)
        self.assertEqual(browser.post('/api/auth/login/', {}, format='json').status_code, 429)
