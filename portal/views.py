from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Max
from django.contrib.auth.decorators import user_passes_test
from collections import defaultdict
from .models import (
    Schedule, Group, Student, Grade,
    Task, Subject, News, Submission, Specialty
)


def index(request):
    news_queryset = News.objects.all().order_by('-created_at')
    if not request.user.is_authenticated:
        news = news_queryset.filter(target='all')
    else:
        news = news_queryset.filter(target__in=['all', 'auth'])

    return render(request, 'portal/index.html', {'news': news[:10]})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        user_login = request.POST.get('username')
        user_pass = request.POST.get('password')
        user = authenticate(username=user_login, password=user_pass)

        if user is not None:
            login(request, user)
            return redirect('index')

        return render(request, 'portal/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'portal/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

def news_detail_view(request, pk):
    # Ищем новость по ID, если не нашли — 404
    article = get_object_or_404(News, pk=pk)
    return render(request, 'portal/news_detail.html', {'article': article})


def is_teacher(user):
    return hasattr(user, 'teacher') or user.is_superuser


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard_view(request):
    teacher = getattr(request.user, 'teacher', None)

    # Если зашел админ, показываем всё, если препод — только его курсы
    if request.user.is_superuser:
        submissions = Submission.objects.all()
    else:
        submissions = Submission.objects.filter(task__subject__teacher=teacher)

    # Параметры сортировки из GET-запроса
    sort = request.GET.get('sort', '-created_at')
    submissions = submissions.select_related('student', 'task', 'student__group').order_by('student__group__name', sort)

    # Обработка оценки и комментария
    if request.method == 'POST':
        sub_id = request.POST.get('submission_id')
        submission = get_object_or_404(Submission, id=sub_id)

        submission.score = request.POST.get('score')
        submission.teacher_comment = request.POST.get('teacher_comment')
        submission.status = 'done' if int(submission.score) > 0 else 'fix'
        submission.save()
        return redirect('teacher_dashboard')

    return render(request, 'portal/teacher_dashboard.html', {
        'submissions': submissions,
        'teacher': teacher
    })


def schedule_view(request):
    group_id = request.GET.get('group_id')
    group = None

    if group_id:
        group = Group.objects.filter(id=group_id).first()
    if not group and request.user.is_authenticated:
        try:
            group = request.user.student.group
        except (Student.DoesNotExist, AttributeError):
            pass
    if not group:
        group = Group.objects.first()
    if not group:
        return render(request, 'portal/schedule.html', {'error': 'В системе пока не создано ни одной группы'})
    lessons = (
        Schedule.objects
        .filter(group=group)
        .select_related('subject')
        .order_by('day_of_week', 'lesson_number')
    )

    days_data = [
        ('monday', 'Понедельник'), ('tuesday', 'Вторник'), ('wednesday', 'Среда'),
        ('thursday', 'Четверг'), ('friday', 'Пятница'), ('saturday', 'Суббота'),
    ]

    schedule_list = []
    for code, name in days_data:
        schedule_list.append({
            'name': name,
            'lessons': lessons.filter(day_of_week=code)
        })

    # 5. Собираем контекст (добавили all_groups для выпадающего списка)
    context = {
        'all_groups': Group.objects.all(),
        'current_group': group,
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
        return render(request, 'portal/profile.html', {'error': 'Ваш аккаунт не связан с профилем студента.'})

    grades = Grade.objects.filter(student=student).select_related('subject')
    submissions = Submission.objects.filter(student=student)

    context = {
        'student': student,
        'grades': grades,
        'completed': submissions.filter(status='done').count(),
        'pending': submissions.filter(status__in=['sent', 'review']).count(),
        'activities': submissions.select_related('task').order_by('-created_at')[:5]
    }
    return render(request, 'portal/profile.html', context)


@login_required
def subjects_list_view(request):
    if request.user.is_superuser:
        subjects = Subject.objects.all().select_related('teacher').distinct()
        group_name = "Все курсы (режим администратора)"
    else:
        try:
            student_group = request.user.student.group
            if student_group:
                subjects = Subject.objects.filter(groups=student_group).select_related('teacher').distinct()
                group_name = student_group.name
            else:
                subjects, group_name = [], "Группа не назначена"
        except Student.DoesNotExist:
            subjects, group_name = [], "Профиль студента не найден"

    return render(request, 'portal/subjects_list.html', {'subjects': subjects, 'group_name': group_name})


@login_required
def subject_detail_view(request, pk):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'portal/subject_detail.html', {'error': 'Профиль студента не найден'})

    subject = get_object_or_404(Subject, pk=pk, groups=student.group)
    tasks = subject.tasks.all().order_by('created_at')
    error_msg = None

    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        uploaded_file = request.FILES.get('solution_file')

        if uploaded_file and task_id:
            task = get_object_or_404(Task, id=task_id, subject=subject)

            if timezone.now() > task.deadline:
                error_msg = 'Срок сдачи задания истек'
            else:
                attempts_count = Submission.objects.filter(task=task, student=student).count()
                if attempts_count >= task.max_attempts:
                    error_msg = 'Превышено количество попыток'
                else:
                    Submission.objects.create(
                        task=task, student=student, file=uploaded_file,
                        comment=request.POST.get('comment', ''),
                        status='sent', attempt_number=attempts_count + 1
                    )
                    return redirect('subject_detail', pk=pk)
    user_submissions = Submission.objects.filter(student=student, task__subject=subject)
    submissions_dict = {}
    for sub in user_submissions:
        if sub.task_id not in submissions_dict or sub.attempt_number > submissions_dict[sub.task_id].attempt_number:
            submissions_dict[sub.task_id] = sub

    return render(request, 'portal/subject_detail.html', {
        'subject': subject, 'tasks': tasks,
        'submissions': submissions_dict, 'error': error_msg
    })


@login_required
def tasks_list_view(request):
    try:
        student = request.user.student
        tasks = Task.objects.filter(subject__groups=student.group).select_related('subject').distinct().order_by(
            'deadline')
    except Student.DoesNotExist:
        tasks = []

    return render(request, 'portal/tasks_list.html', {'tasks': tasks})


def admission_view(request):
    all_specs = Specialty.objects.all()
    grouped = defaultdict(list)
    for s in all_specs:
        grouped[s.name].append(s)

    # Превращаем обратно в обычный словарь для шаблона
    return render(request, 'portal/info/admission.html', {
        'grouped_specialties': dict(grouped)
    })

def career_view(request):
    # В будущем тут будет QuerySet с вакансиями
    return render(request, 'portal/info/career.html', {
        'jobs_count': 12
    })

def college_view(request):
    return render(request, 'portal/info/college.html')

def support_view(request):
    return render(request, 'portal/info/support.html')
