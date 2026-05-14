from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Schedule, Group, Student, Grade, Task, Subject, News, Submission


def index(request):
    if request.user.is_authenticated:
        news = News.objects.all().order_by('-created_at')
    else:
        news = News.objects.filter(target='all').order_by('-created_at')
    return render(request, 'portal/index.html', {'news': news})


def login_view(request):
    if request.method == 'POST':
        user_login = request.POST.get('username')
        user_pass = request.POST.get('password')
        user = authenticate(username=user_login, password=user_pass)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'portal/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'portal/login.html')


def logout_view(request):
    logout(request)
    return redirect('index')


@login_required
def schedule_view(request):
    # 1. Защита от отсутствия профиля или группы
    student = get_object_or_404(Student, user=request.user)
    group = student.group

    if not group:
        return render(request, 'portal/schedule.html', {'error': 'Вы не прикреплены к группе'})

    # 2. Оптимизированный запрос (select_related подтягивает Предмет сразу)
    lessons = Schedule.objects.filter(group=group).select_related('subject').order_by('lesson_number')

    # 3. Список дней для итерации
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

    # 4. Разбивка на 2 колонки (Пн-Ср и Чт-Сб)
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
        grades = Grade.objects.filter(student=student).select_related('subject')
        # Статистика
        completed = Submission.objects.filter(student=student, status='done').count()
        pending = Submission.objects.filter(student=student, status='sent').count()
        activities = Submission.objects.filter(student=student).order_by('-created_at')[:5]
    except Student.DoesNotExist:
        student = None
        grades, completed, pending, activities = [], 0, 0, []

    return render(request, 'portal/profile.html', {
        'student': student,
        'grades': grades,
        'completed': completed,
        'pending': pending,
        'activities': activities
    })


@login_required
def subjects_list_view(request):
    # Проверяем, является ли пользователь администратором
    if request.user.is_superuser:
        subjects = Subject.objects.all()
        group_name = "Все курсы (режим администратора)"
        student_group = None
    else:
        try:
            student_profile = request.user.student
            student_group = student_profile.group
            # Фильтруем предметы по группе студента
            subjects = Subject.objects.filter(groups=student_group)
            group_name = student_group.name
        except Student.DoesNotExist:
            # Если это обычный юзер, но почему-то без профиля студента
            subjects = []
            group_name = "Группа не назначена"
            student_group = None

    return render(request, 'portal/subjects_list.html', {
        'subjects': subjects,
        'group': student_group,
        'group_name': group_name # Добавили переменную для заголовка
    })

@login_required
def subject_detail_view(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    tasks = subject.tasks.all().order_by('created_at')

    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'portal/subject_detail.html',
                      {'subject': subject, 'tasks': tasks, 'error': 'Профиль студента не найден'})

    # Загрузка задания
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        uploaded_file = request.FILES.get('solution_file')
        if uploaded_file and task_id:
            task = get_object_or_404(Task, id=task_id)
            Submission.objects.update_or_create(
                task=task, student=student,
                defaults={
                    'file': uploaded_file,
                    'comment': request.POST.get('comment', ''),
                    'status': 'sent'
                }
            )
            return redirect('subject_detail', pk=pk)

    user_submissions = Submission.objects.filter(student=student, task__subject=subject)
    submissions_dict = {s.task_id: s for s in user_submissions}

    return render(request, 'portal/subject_detail.html', {
        'subject': subject,
        'tasks': tasks,
        'submissions': submissions_dict
    })


@login_required
def tasks_list_view(request):
    tasks = Task.objects.all().order_by('deadline')
    return render(request, 'portal/tasks_list.html', {'tasks': tasks})