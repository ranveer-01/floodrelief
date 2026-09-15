from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html

from .models import Role, User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "name", "role")


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "user_count")
    search_fields = ("name", "description")

    @admin.display(description="users")
    def user_count(self, obj):
        return obj.users.count()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreateForm
    form = UserEditForm
    model = User

    list_display = ("email", "name", "role_badge", "is_staff", "is_active", "created_at")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "name", "phone")
    ordering = ("email",)
    readonly_fields = ("created_at", "last_login", "id")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Profile", {"fields": ("name", "phone", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Timestamps", {"fields": ("created_at", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    @admin.display(description="role", ordering="role__name")
    def role_badge(self, obj):
        if not obj.role:
            return format_html('<span style="color:#9aa8ab;">—</span>')
        colours = {
            "victim": "#1fa2b8",
            "donor": "#f2a03d",
            "ngo_staff": "#2fb37f",
            "admin": "#ff5f45",
        }
        colour = colours.get(obj.role.name, "#6f8a93")
        return format_html(
            '<span style="background:{}1f;color:{};padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;">{}</span>',
            colour,
            colour,
            obj.role.get_name_display().upper(),
        )
