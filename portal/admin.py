from django.contrib import admin
from .models import Group, Subject, Schedule, Student, Grade, Task, News, Teacher

# Регистрация простых моделей без дополнительных настроек
admin.site.register(Group)
admin.site.register(Grade)
admin.site.register(Task)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'bio')

    def get_full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"

    get_full_name.short_description = 'ФИО Преподавателя'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher')
    list_filter = ('teacher',)
    search_fields = ('name',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'record_book_number', 'get_avg')
    list_filter = ('group',)

    def get_avg(self, obj):
        return obj.get_average_grade()

    get_avg.short_description = 'Ср. балл'


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'importance', 'target', 'created_at')
    list_filter = ('importance', 'target')
    search_fields = ('title', 'content')


# ИСПРАВЛЕНО: Убран лишний admin.site.register(Schedule), оставлен только этот блок
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('group', 'day_of_week', 'lesson_number', 'subject', 'classroom')
    list_filter = ('group', 'day_of_week')
    ordering = ('group', 'day_of_week', 'lesson_number')