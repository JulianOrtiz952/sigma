from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import (
    AcademicProgram,
    AcademicRecord,
    Administrator,
    Course,
    Curriculum,
    Enrollment,
    Group,
    GroupSchedule,
    Notification,
    Student,
    Teacher,
    University,
)

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

    def test_duplicate_email_allocates_incremental_suffix(self):
        first = self.create_account()
        second = self.create_account()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data['email'], 'andresjulianoj@test.example.edu')
        self.assertEqual(second.data['email'], 'andresjulianoj2@test.example.edu')

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
        self.assertTrue(response.data['user']['must_change_password'])
        response = browser.post('/api/auth/change-password/', {
            'current_password': str(created['code']),
            'new_password': 'NewStudentAccess!4732',
            'confirm_password': 'NewStudentAccess!4732',
        }, format='json', HTTP_X_CSRFTOKEN=response.data['csrfToken'])
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


class AcademicCourseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(username='academic-admin', password='LocalTest!4396', role='administrator')
        Administrator.objects.create(user=self.admin_user, is_global=True)
        self.university = University.objects.create(name='Universidad Académica', email_domain='academic.example.edu')
        self.program = AcademicProgram.objects.create(name='Ingeniería', university=self.university)
        self.curriculum = Curriculum.objects.create(academic_program=self.program, name='Pensum Ingeniería')
        self.teacher_user = User.objects.create_user(username='teacher-academic', role='teacher', first_name='Ada', last_name='Lovelace')
        self.teacher = Teacher.objects.create(user=self.teacher_user, university=self.university)
        self.student_user = User.objects.create_user(username='student-academic', role='student', first_name='Linus')
        self.student = Student.objects.create(user=self.student_user, academic_program=self.program)
        self.client.force_authenticate(self.admin_user)

    def payload(self, **changes):
        return {
            'name': 'Programación I', 'curriculum': self.curriculum.pk, 'academic_hours': 64,
            'credits': 4, 'semester': 1, 'minimum_approved_credits': 0, 'prerequisites': [],
            'teacher': self.teacher.pk, 'capacity': 1,
            'schedules': [{'day_of_week': 0, 'start_time': '08:00', 'end_time': '11:00'}],
        } | changes

    def create_course(self, **changes):
        return self.client.post('/api/courses/', self.payload(**changes), format='json')

    def test_admin_creates_open_course_with_one_teacher_and_capacity(self):
        response = self.create_course()
        self.assertEqual(response.status_code, 201, response.data)
        group = Group.objects.get()
        self.assertEqual(group.teacher, self.teacher)
        self.assertEqual(group.capacity, 1)
        self.assertEqual(group.status, Group.Status.OPEN)
        self.assertEqual(response.data['groups'][0]['available_seats'], 1)
        self.assertEqual(response.data['groups'][0]['section'], 'A')

    def test_teacher_must_belong_to_curriculum_university(self):
        other_university = University.objects.create(name='Otra académica', email_domain='other-academic.example.edu')
        other_user = User.objects.create_user(username='other-teacher', role='teacher')
        other_teacher = Teacher.objects.create(user=other_user, university=other_university)
        response = self.create_course(teacher=other_teacher.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Course.objects.count(), 0)

    def test_prerequisites_must_share_curriculum_and_have_lower_semester(self):
        prerequisite = Course.objects.create(curriculum=self.curriculum, name='Fundamentos', academic_hours=32, credits=2, semester=1)
        response = self.create_course(
            name='Programación II', semester=2, prerequisites=[prerequisite.pk],
            schedules=[{'day_of_week': 1, 'start_time': '08:00', 'end_time': '11:00'}],
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(list(Course.objects.get(name='Programación II').prerequisites.all()), [prerequisite])

        same_semester = Course.objects.create(curriculum=self.curriculum, name='Lógica', academic_hours=32, credits=2, semester=2)
        response = self.create_course(name='Estructuras', semester=2, prerequisites=[same_semester.pk])
        self.assertEqual(response.status_code, 400)

    def test_capacity_creates_fifo_waitlist_and_only_students_can_request(self):
        group_id = self.create_course().data['groups'][0]['id']
        self.client.force_authenticate(self.student_user)
        first = self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data['status'], Enrollment.Status.CONFIRMED)

        second_user = User.objects.create_user(username='student-two', role='student')
        Student.objects.create(user=second_user, academic_program=self.program)
        self.client.force_authenticate(second_user)
        second = self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json')
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data['status'], Enrollment.Status.WAITLISTED)
        self.assertEqual(Enrollment.objects.filter(status=Enrollment.Status.CONFIRMED).count(), 1)
        self.assertEqual(Enrollment.objects.filter(status=Enrollment.Status.WAITLISTED).count(), 1)
        self.assertEqual(self.client.get('/api/courses/').data[0]['groups'][0]['enrollment']['waitlist_position'], 1)

        self.client.force_authenticate(self.teacher_user)
        self.assertEqual(self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json').status_code, 403)

    def test_course_cannot_activate_without_confirmed_student(self):
        group_id = self.create_course().data['groups'][0]['id']
        response = self.client.patch(f'/api/groups/{group_id}/status/', {'status': 'active'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Group.objects.get(pk=group_id).status, Group.Status.OPEN)

        self.client.force_authenticate(self.student_user)
        self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json')
        self.client.force_authenticate(self.admin_user)
        response = self.client.patch(f'/api/groups/{group_id}/status/', {'status': 'active'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Group.objects.get(pk=group_id).status, Group.Status.ACTIVE)

    def test_student_only_sees_own_curriculum_and_prerequisites_are_enforced(self):
        prerequisite = Course.objects.create(curriculum=self.curriculum, name='Bases', academic_hours=32, credits=2, semester=1)
        course = Course.objects.create(curriculum=self.curriculum, name='Avanzada', academic_hours=64, credits=4, semester=2, minimum_approved_credits=2)
        course.prerequisites.add(prerequisite)
        group = Group.objects.create(course=course, teacher=self.teacher, capacity=10)
        GroupSchedule.objects.create(group=group, day_of_week=2, start_time='14:00', end_time='16:00')
        other_program = AcademicProgram.objects.create(name='Psicología', university=self.university)
        other_curriculum = Curriculum.objects.create(academic_program=other_program)
        hidden = Course.objects.create(curriculum=other_curriculum, name='Clínica', academic_hours=32, credits=2, semester=1)
        Group.objects.create(course=hidden, teacher=self.teacher, capacity=10)

        self.client.force_authenticate(self.student_user)
        visible = self.client.get('/api/courses/')
        self.assertEqual([item['name'] for item in visible.data], ['Bases', 'Avanzada'])
        self.assertEqual(self.client.post(f'/api/groups/{group.pk}/enroll/', {}, format='json').status_code, 400)

        AcademicRecord.objects.create(student=self.student, course=prerequisite, approved_at='2026-01-10')
        response = self.client.post(f'/api/groups/{group.pk}/enroll/', {}, format='json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_existing_course_gets_next_group_letter_and_requires_different_schedule(self):
        created = self.create_course().data
        course_id = created['id']
        response = self.client.post(f'/api/courses/{course_id}/groups/', {
            'teacher': self.teacher.pk, 'capacity': 15,
            'schedules': [{'day_of_week': 1, 'start_time': '08:00', 'end_time': '11:00'}],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([group['section'] for group in response.data['groups']], ['A', 'B'])
        duplicate = self.client.post(f'/api/courses/{course_id}/groups/', {
            'teacher': self.teacher.pk, 'capacity': 15,
            'schedules': [{'day_of_week': 1, 'start_time': '08:00', 'end_time': '11:00'}],
        }, format='json')
        self.assertEqual(duplicate.status_code, 400)

    def test_student_schedule_conflict_is_rejected_for_available_seat(self):
        first_group = self.create_course(schedules=[{'day_of_week': 0, 'start_time': '08:00', 'end_time': '10:00'}]).data['groups'][0]
        second_teacher_user = User.objects.create_user(username='teacher-two', role='teacher')
        second_teacher = Teacher.objects.create(user=second_teacher_user, university=self.university)
        second_group = self.create_course(
            name='Bases de datos', teacher=second_teacher.pk,
            schedules=[{'day_of_week': 0, 'start_time': '09:00', 'end_time': '11:00'}],
        ).data['groups'][0]
        self.client.force_authenticate(self.student_user)
        self.assertEqual(self.client.post(f"/api/groups/{first_group['id']}/enroll/", {}, format='json').status_code, 201)
        conflict = self.client.post(f"/api/groups/{second_group['id']}/enroll/", {}, format='json')
        self.assertEqual(conflict.status_code, 400)
        self.assertIn('Lunes', str(conflict.data))

    def test_cancelling_confirmed_enrollment_promotes_next_waitlisted_student(self):
        group_id = self.create_course().data['groups'][0]['id']
        self.client.force_authenticate(self.student_user)
        confirmed = self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json').data
        waiter_user = User.objects.create_user(username='waiter', role='student')
        waiter = Student.objects.create(user=waiter_user, academic_program=self.program)
        self.client.force_authenticate(waiter_user)
        waiting = self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json')
        self.assertEqual(waiting.data['status'], Enrollment.Status.WAITLISTED)
        self.client.force_authenticate(self.student_user)
        cancelled = self.client.delete(f"/api/enrollments/{confirmed['id']}/")
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(Enrollment.objects.get(student=waiter).status, Enrollment.Status.CONFIRMED)
        self.assertTrue(Notification.objects.filter(user=waiter_user, title='Cupo asignado').exists())

    def test_conflicting_first_waiter_swaps_and_second_is_promoted_with_notification(self):
        target_group = self.create_course(schedules=[{'day_of_week': 0, 'start_time': '08:00', 'end_time': '10:00'}]).data['groups'][0]
        self.client.force_authenticate(self.student_user)
        occupant = self.client.post(f"/api/groups/{target_group['id']}/enroll/", {}, format='json').data

        conflict_teacher_user = User.objects.create_user(username='conflict-teacher', role='teacher')
        conflict_teacher = Teacher.objects.create(user=conflict_teacher_user, university=self.university)
        self.client.force_authenticate(self.admin_user)
        conflict_group = self.create_course(
            name='Cálculo', teacher=conflict_teacher.pk, capacity=10,
            schedules=[{'day_of_week': 0, 'start_time': '09:00', 'end_time': '11:00'}],
        ).data['groups'][0]
        first_user = User.objects.create_user(username='first-waiter', role='student')
        first_waiter = Student.objects.create(user=first_user, academic_program=self.program)
        second_user = User.objects.create_user(username='second-waiter', role='student')
        second_waiter = Student.objects.create(user=second_user, academic_program=self.program)
        self.client.force_authenticate(first_user)
        self.client.post(f"/api/groups/{conflict_group['id']}/enroll/", {}, format='json')
        self.client.post(f"/api/groups/{target_group['id']}/enroll/", {}, format='json')
        self.client.force_authenticate(second_user)
        self.client.post(f"/api/groups/{target_group['id']}/enroll/", {}, format='json')

        self.client.force_authenticate(self.student_user)
        response = self.client.delete(f"/api/enrollments/{occupant['id']}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Enrollment.objects.get(student=first_waiter, group_id=target_group['id']).status, Enrollment.Status.WAITLISTED)
        self.assertEqual(Enrollment.objects.get(student=second_waiter, group_id=target_group['id']).status, Enrollment.Status.CONFIRMED)
        notice = Notification.objects.get(user=first_user)
        self.assertIn('Lunes', notice.message)
        self.assertIn('09:00', notice.message)

    def test_cancelled_course_disappears_from_student_schedule(self):
        group_id = self.create_course().data['groups'][0]['id']
        self.client.force_authenticate(self.student_user)
        enrollment = self.client.post(f'/api/groups/{group_id}/enroll/', {}, format='json').data
        self.assertEqual(len(self.client.get('/api/schedule/').data), 1)
        self.client.delete(f"/api/enrollments/{enrollment['id']}/")
        self.assertEqual(self.client.get('/api/schedule/').data, [])
