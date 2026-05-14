from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

class Group(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название группы")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    bio = models.TextField(blank=True, verbose_name="О преподавателе / Кафедра")
    photo = models.ImageField(upload_to='teachers/', null=True, blank=True, verbose_name="Фотография")

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"

class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название предмета")
    # ИСПРАВЛЕНО: Теперь привязываемся к модели Teacher
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='subjects', verbose_name="Преподаватель")
    groups = models.ManyToManyField(Group, related_name='subjects', verbose_name="Доступен группам")
    image = models.ImageField(upload_to='subjects/', null=True, blank=True, verbose_name="Обложка курса")
    description = models.TextField(blank=True, verbose_name="Краткое описание")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

class Schedule(models.Model):
    DAY_CHOICES = [
        ('monday', 'Понедельник'), ('tuesday', 'Вторник'), ('wednesday', 'Среда'),
        ('thursday', 'Четверг'), ('friday', 'Пятница'), ('saturday', 'Суббота'),
    ]
    LESSON_TYPES = [
        ('lecture', 'Лекция'), ('practice', 'Практика'),
        ('seminar', 'Семинар'), ('lab', 'Лабораторная работа'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Группа")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Предмет")
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES, verbose_name="День недели")
    lesson_number = models.PositiveIntegerField(verbose_name="Номер пары")
    classroom = models.CharField(max_length=50, verbose_name="Аудитория")
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default='lecture', verbose_name="Тип занятия")
    is_stream = models.BooleanField(default=False, verbose_name="Потоковая лекция")

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписание"
        ordering = ['day_of_week', 'lesson_number']

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.lesson_number} пара"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, verbose_name="Группа")
    record_book_number = models.CharField(max_length=20, verbose_name="Номер зачетки")

    # НОВОЕ: Метод для аналитики в отчете
    def get_average_grade(self):
        avg = self.grades.aggregate(Avg('score'))['score__avg']
        return round(avg, 2) if avg else 0

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} ({self.group})"

    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades', verbose_name="Студент")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Предмет")
    score = models.PositiveIntegerField(default=0, verbose_name="Баллы")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Дата последнего изменения")

    class Meta:
        verbose_name = "Оценка/Балл"
        verbose_name_plural = "Оценки и баллы"
        unique_together = ('student', 'subject')

class Task(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tasks', verbose_name="Предмет")
    title = models.CharField(max_length=200, verbose_name="Название задания")
    description = models.TextField(verbose_name="Описание/Инструкция")
    deadline = models.DateTimeField(verbose_name="Срок сдачи (дедлайн)")
    max_attempts = models.PositiveIntegerField(default=3, verbose_name="Макс. кол-во попыток")
    max_score = models.PositiveIntegerField(default=10, verbose_name="Макс. балл")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Задание"
        verbose_name_plural = "Задания"

class News(models.Model):
    IMPORTANCE_CHOICES = [('low', 'Обычная'), ('medium', 'Важная'), ('high', 'Срочно')]
    TARGET_CHOICES = [('all', 'Всем'), ('auth', 'Авторизованным')]
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Текст")
    importance = models.CharField(max_length=10, choices=IMPORTANCE_CHOICES, default='low')
    target = models.CharField(max_length=10, choices=TARGET_CHOICES, default='all')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

class Submission(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Отправлено'),
        ('review', 'На проверке'),
        ('done', 'Зачтено'),
        ('fix', 'Требует исправления'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions', verbose_name="Задание")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Студент")
    file = models.FileField(upload_to='submissions/%Y/%m/%d/', verbose_name="Файл решения")
    comment = models.TextField(blank=True, verbose_name="Комментарий студента")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")

    def __str__(self):
        return f"{self.student.user.username} - {self.task.title}"

    class Meta:
        verbose_name = "Решение студента"
        verbose_name_plural = "Решения студентов"

