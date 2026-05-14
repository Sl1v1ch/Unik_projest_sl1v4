from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import (
    Schedule,
    Group,
    Student,
    Grade,
    Task,
    Subject,
    News,
    Submission
)


def index(request):
    if request.user.is_authenticated:
        news = News.objects.all().order_by('-created_at')
    else:
        news = News.objects.filter(target='all').order_by('-created_at')

    return render(request, 'portal/index.html', {
        'news': news
    })


def login_view(request):

    # Если пользователь уже вошел
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':

        user_login = request.POST.get('username')
        user_pass = request.POST.get('password')

        user = authenticate(
            username=user_login,
            password=user_pass
        )

        if user is not None:
            login(request, user)
            return redirect('index')

        return render(request, 'portal/login.html', {
            'error': 'Неверный логин или пароль'
        })

    return render(request, 'portal/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('index')


@login_required
def schedule_view(request):

    student = get_object_or_404(
        Student,
        user=request.user
    )

    group = student.group

    if not group:
        return render(request, 'portal/schedule.html', {
            'error': 'Вы не прикреплены к группе'
        })

    lessons = (
        Schedule.objects
        .filter(group=group)
        .select_related('subject')
        .order_by('day_of_week', 'lesson_number')
    )

    days_data = [
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
        ('saturday', 'Суббота'),
    ]

    schedule_list = []

    for code, name in days_data:
        schedule_list.append({
            'name': name,
            'lessons': lessons.filter(day_of_week=code)
        })

    context = {
        'group_name': group.name,
        'col_left': schedule_list[:3],
        'col_right': schedule_list[3:],
    }

    return render(request, 'portal/schedule.html', context)


@login_required
def profile_view(request):

    try:
        student = request.user.student

    except Student.DoesNotExist:
        return render(request, 'portal/profile.html', {
            'error': 'Профиль студента не найден'
        })

    grades = (
        Grade.objects
        .filter(student=student)
        .select_related('subject')
    )

    submissions = Submission.objects.filter(student=student)

    completed = submissions.filter(status='done').count()

    pending = submissions.filter(
        status__in=['sent', 'review']
    ).count()

    activities = (
        submissions
        .select_related('task')
        .order_by('-created_at')[:5]
    )

    return render(request, 'portal/profile.html', {
        'student': student,
        'grades': grades,
        'completed': completed,
        'pending': pending,
        'activities': activities
    })


@login_required
def subjects_list_view(request):

    # Режим администратора
    if request.user.is_superuser:

        subjects = (
            Subject.objects
            .all()
            .select_related('teacher')
            .distinct()
        )

        group_name = "Все курсы (режим администратора)"
        student_group = None

    else:

        try:
            student_profile = request.user.student
            student_group = student_profile.group

            if not student_group:
                return render(request, 'portal/subjects_list.html', {
                    'subjects': [],
                    'group_name': 'Группа не назначена'
                })

            subjects = (
                Subject.objects
                .filter(groups=student_group)
                .select_related('teacher')
                .distinct()
            )

            group_name = student_group.name

        except Student.DoesNotExist:

            subjects = []
            group_name = "Профиль студента не найден"
            student_group = None

    return render(request, 'portal/subjects_list.html', {
        'subjects': subjects,
        'group': student_group,
        'group_name': group_name
    })


@login_required
def subject_detail_view(request, pk):

    try:
        student = request.user.student

    except Student.DoesNotExist:

        return render(
            request,
            'portal/subject_detail.html',
            {'error': 'Профиль студента не найден'}
        )

    # Проверка доступа к предмету
    subject = get_object_or_404(
        Subject,
        pk=pk,
        groups=student.group
    )

    tasks = (
        subject.tasks
        .all()
        .order_by('created_at')
    )

    # Загрузка задания
    if request.method == 'POST':

        task_id = request.POST.get('task_id')
        uploaded_file = request.FILES.get('solution_file')

        if uploaded_file and task_id:

            task = get_object_or_404(
                Task,
                id=task_id,
                subject=subject
            )

            # Проверка дедлайна
            if timezone.now() > task.deadline:

                return render(request, 'portal/subject_detail.html', {
                    'subject': subject,
                    'tasks': tasks,
                    'error': 'Срок сдачи задания истек'
                })

            # Количество попыток
            attempts_count = Submission.objects.filter(
                task=task,
                student=student
            ).count()

            # Проверка лимита попыток
            if attempts_count >= task.max_attempts:

                return render(request, 'portal/subject_detail.html', {
                    'subject': subject,
                    'tasks': tasks,
                    'error': 'Превышено количество попыток'
                })

            Submission.objects.create(
                task=task,
                student=student,
                file=uploaded_file,
                comment=request.POST.get('comment', ''),
                status='sent',
                attempt_number=attempts_count + 1
            )

            return redirect('subject_detail', pk=pk)

    user_submissions = (
        Submission.objects
        .filter(
            student=student,
            task__subject=subject
        )
        .select_related('task')
    )

    submissions_dict = {}

    for submission in user_submissions:

        # Берем только последнюю попытку
        if (
            submission.task_id not in submissions_dict
            or
            submission.attempt_number >
            submissions_dict[submission.task_id].attempt_number
        ):
            submissions_dict[submission.task_id] = submission

    return render(request, 'portal/subject_detail.html', {
        'subject': subject,
        'tasks': tasks,
        'submissions': submissions_dict
    })


@login_required
def tasks_list_view(request):

    student = get_object_or_404(
        Student,
        user=request.user
    )

    tasks = (
        Task.objects
        .filter(subject__groups=student.group)
        .select_related('subject')
        .distinct()
        .order_by('deadline')
    )

    return render(request, 'portal/tasks_list.html', {
        'tasks': tasks
    })