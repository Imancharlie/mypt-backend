from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_student_id', 'get_program')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__program', 'profile__pt_phase')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__student_id')
    
    def get_student_id(self, obj):
        return obj.profile.student_id if hasattr(obj, 'profile') else '-'
    get_student_id.short_description = 'Student ID'
    
    def get_program(self, obj):
        return obj.profile.get_program_display() if hasattr(obj, 'profile') else '-'
    get_program.short_description = 'Program'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin) 