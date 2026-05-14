from django.contrib import admin
from .models import (
    Group,
    Subject,
    Schedule,
    Student,
    Grade,
    Task,
    News,
    Teacher,
    Submission
)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):

    list_display = (
        'student',
        'task',
        'status',
        'attempt_number',
        'score',
        'created_at'
    )

    list_filter = (
        'status',
        'created_at'
    )

    search_fields = (
        'student__user__username',
        'task__title'
    )

    ordering = ('-created_at',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher')
    list_filter = ('teacher',)
    search_fields = ('name',)
    filter_horizontal = ('groups',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'record_book_number', 'get_avg')
    list_filter = ('group',)
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'record_book_number'
    )

    def get_avg(self, obj):
        return obj.get_average_grade()
    get_avg.short_description = 'Ср. балл'


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'importance', 'target', 'created_at')
    list_filter = ('importance', 'target')
    search_fields = ('title', 'content')


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('group', 'day_of_week', 'lesson_number', 'subject', 'classroom')
    list_filter = ('group', 'day_of_week')
    ordering = ('group', 'day_of_week', 'lesson_number')
    search_fields = (
        'group__name',
        'subject__name',
        'classroom'
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subject',
        'deadline',
        'max_attempts',
        'max_score'
    )
    list_filter = (
        'subject',
        'deadline'
    )
    search_fields = (
        'title',
        'description'
    )
    ordering = ('deadline',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'subject',
        'score',
        'date_updated'
    )
    list_filter = (
        'subject',
    )
    search_fields = (
        'student__user__username',
        'subject__name'
    )
    ordering = ('-date_updated',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)