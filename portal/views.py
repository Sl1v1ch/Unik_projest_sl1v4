from collections import defaultdict

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import (
    Schedule,
    Group,
    Student,
    Grade,
    Task,
    Subject,
    News,
    Submission,
    Specialty
)


def index(request):
    news_queryset = News.objects.all().order_by('-created_at')

    if request.user.is_authenticated:
        news = news_queryset.filter(target__in=['all', 'auth'])
    else:
        news = news_queryset.filter(target='all')

    context = {
        'news': news[:10]
    }

    return render(request, 'portal/index.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('portal:index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('portal:index')

        return render(request, 'portal/login.html', {
            'error': 'Неверный логин или пароль'
        })

    return render(request, 'portal/login.html')


def logout_view(request):
    logout(request)
    return redirect('portal:index')


def news_detail_view(request, pk):
    article = get_object_or_404(News, pk=pk)

    return render(request, 'portal/news_detail.html', {
        'article': article
    })


def is_teacher(user):
    return hasattr(user, 'teacher') or user.is_superuser


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard_view(request):
    teacher = getattr(request.user, 'teacher', None)

    if request.user.is_superuser:
        submissions = Submission.objects.all()
    else:
        submissions = Submission.objects.filter(
            task__subject__teacher=teacher
        )

    submissions = submissions.select_related(
        'student',
        'student__group',
        'task',
        'task__subject'
    ).order_by('-created_at')

    if request.method == 'POST':
        submission_id = request.POST.get('submission_id')

        submission = get_object_or_404(
            Submission,
            id=submission_id
        )

        score = request.POST.get('score')
        teacher_comment = request.POST.get('teacher_comment')

        submission.score = score
        submission.teacher_comment = teacher_comment

        if score and int(score) > 0:
            submission.status = 'done'
        else:
            submission.status = 'fix'

        submission.save()

        return redirect('portal:teacher_dashboard')

    context = {
        'submissions': submissions,
        'teacher': teacher
    }

    return render(request, 'portal/teacher_dashboard.html', context)


def schedule_view(request):
    user = request.user
    group_id = request.GET.get('group_id')

    is_teacher_flag = False
    is_student_flag = False
    teacher_obj = None
    student_obj = None

    if user.is_authenticated:
        # Суперпользователь/стафф — ведут себя как преподаватель (видят дропдаун)
        if user.is_superuser or user.is_staff:
            is_teacher_flag = True
        else:
            try:
                teacher_obj = user.teacher
                is_teacher_flag = True
            except Exception:
                pass

            if not is_teacher_flag:
                try:
                    student_obj = user.student
                    is_student_flag = True
                except Exception:
                    pass

    all_groups = Group.objects.all()

    # Студент — всегда только своя группа, без выбора
    if is_student_flag and student_obj and student_obj.group:
        group = student_obj.group
    else:
        # Преподаватель, админ или неавторизованный — может выбирать группу
        group = None
        if group_id:
            group = Group.objects.filter(id=group_id).first()
        if not group:
            if is_teacher_flag and teacher_obj:
                first_lesson = Schedule.objects.filter(
                    subject__teacher=teacher_obj
                ).select_related('group').first()
                group = first_lesson.group if first_lesson else Group.objects.first()
            else:
                group = Group.objects.first()

    if not group:
        return render(request, 'portal/schedule.html', {
            'error': 'В системе пока не создано ни одной группы',
            'is_student': is_student_flag,
            'is_teacher': is_teacher_flag,
        })

    lessons = (
        Schedule.objects
        .filter(group=group)
        .select_related('subject', 'subject__teacher')
        .order_by('day_of_week', 'lesson_number')
    )

    # Для преподавателя — набор id его занятий в этой группе
    teacher_lesson_ids = set()
    if is_teacher_flag and teacher_obj:
        teacher_lesson_ids = set(
            Schedule.objects.filter(
                subject__teacher=teacher_obj, group=group
            ).values_list('id', flat=True)
        )

    days_data = [
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
        ('saturday', 'Суббота'),
    ]

    lessons_map = defaultdict(dict)
    for lesson in lessons:
        lessons_map[lesson.day_of_week][lesson.lesson_number] = lesson

    all_lesson_numbers = [ln for day in lessons_map.values() for ln in day.keys()]
    max_lesson = max(all_lesson_numbers, default=6)
    max_lesson = max(max_lesson, 6)
    lesson_numbers = list(range(1, max_lesson + 1))

    schedule_table = []
    for code, name in days_data:
        row = {
            'code': code,
            'name': name,
            'lessons': [lessons_map[code].get(n) for n in lesson_numbers],
        }
        schedule_table.append(row)

    context = {
        'all_groups': all_groups,
        'current_group': group,
        'group_name': group.name,
        'schedule_table': schedule_table,
        'lesson_numbers': lesson_numbers,
        'is_student': is_student_flag,
        'is_teacher': is_teacher_flag,
        'teacher_lesson_ids': teacher_lesson_ids,
    }

    return render(request, 'portal/schedule.html', context)

@login_required
def profile_view(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'portal/profile.html', {
            'error': 'Ваш аккаунт не связан с профилем студента.'
        })

    grades = Grade.objects.filter(
        student=student
    ).select_related('subject')

    submissions = Submission.objects.filter(
        student=student
    ).select_related('task')

    completed_count = submissions.filter(status='done').count()

    pending_count = submissions.filter(
        status__in=['sent', 'review']
    ).count()

    context = {
        'student': student,
        'grades': grades,
        'completed': completed_count,
        'pending': pending_count,
        'activities': submissions.order_by('-created_at')[:5]
    }

    return render(request, 'portal/profile.html', context)


@login_required
def subjects_list_view(request):
    if request.user.is_superuser:
        subjects = Subject.objects.all().select_related(
            'teacher'
        ).distinct()

        group_name = 'Все курсы (режим администратора)'

    else:
        try:
            student_group = request.user.student.group

            if student_group:
                subjects = Subject.objects.filter(
                    groups=student_group
                ).select_related('teacher').distinct()

                group_name = student_group.name

            else:
                subjects = []
                group_name = 'Группа не назначена'

        except Student.DoesNotExist:
            subjects = []
            group_name = 'Профиль студента не найден'

    context = {
        'subjects': subjects,
        'group_name': group_name
    }

    return render(request, 'portal/subjects_list.html', context)


@login_required
def subject_detail_view(request, pk):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'portal/subject_detail.html', {
            'error': 'Профиль студента не найден'
        })

    subject = get_object_or_404(
        Subject,
        pk=pk,
        groups=student.group
    )

    tasks = subject.tasks.all().order_by('deadline')

    error_msg = None

    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        uploaded_file = request.FILES.get('solution_file')

        if uploaded_file and task_id:
            task = get_object_or_404(
                Task,
                id=task_id,
                subject=subject
            )

            if timezone.now() > task.deadline:
                error_msg = 'Срок сдачи задания истек'

            else:
                attempts_count = Submission.objects.filter(
                    task=task,
                    student=student
                ).count()

                if attempts_count >= task.max_attempts:
                    error_msg = 'Превышено количество попыток'

                else:
                    Submission.objects.create(
                        task=task,
                        student=student,
                        file=uploaded_file,
                        comment=request.POST.get('comment', ''),
                        status='sent',
                        attempt_number=attempts_count + 1
                    )

                    return redirect(
                        'portal:subject_detail',
                        pk=pk
                    )

    user_submissions = Submission.objects.filter(
        student=student,
        task__subject=subject
    ).select_related('task')

    submissions_dict = {}

    for sub in user_submissions:
        if (
            sub.task_id not in submissions_dict
            or
            sub.attempt_number > submissions_dict[sub.task_id].attempt_number
        ):
            submissions_dict[sub.task_id] = sub

    completed_tasks = 0

    for task in tasks:
        task.user_submission = submissions_dict.get(task.id)

        if (
            task.user_submission
            and
            task.user_submission.status == 'done'
        ):
            completed_tasks += 1

    progress_percent = 0

    if tasks.count() > 0:
        progress_percent = int(
            (completed_tasks / tasks.count()) * 100
        )

    context = {
        'subject': subject,
        'tasks': tasks,
        'submissions_dict': submissions_dict,
        'completed_tasks': completed_tasks,
        'total_tasks': tasks.count(),
        'progress_percent': progress_percent,
        'error': error_msg,
        'now': timezone.now(),
    }

    return render(request, 'portal/subject_detail.html', context)


@login_required
def tasks_list_view(request):
    try:
        student = request.user.student

        tasks = Task.objects.filter(
            subject__groups=student.group
        ).select_related('subject').distinct().order_by('deadline')

    except Student.DoesNotExist:
        tasks = []

    return render(request, 'portal/tasks_list.html', {
        'tasks': tasks
    })


def admission_view(request):
    all_specs = Specialty.objects.all()

    grouped = defaultdict(list)

    for specialty in all_specs:
        grouped[specialty.name].append(specialty)

    context = {
        'grouped_specialties': dict(grouped)
    }

    return render(request, 'portal/info/admission.html', context)


def career_view(request):
    return render(request, 'portal/info/career.html', {
        'jobs_count': 12
    })


def college_view(request):
    return render(request, 'portal/info/information.html')


def support_view(request):
    return render(request, 'portal/info/support.html')