from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.apps.identity.models import Permission, Role, RolePermission, User, UserRole


@admin.register(User)
class IdentityUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "status", "is_staff")
    list_filter = ("status", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    filter_horizontal = ()
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "phone")}),
        ("State", {"fields": ("status", "email_verified_at")}),
        ("Technical access", {"fields": ("is_staff", "is_superuser")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "status",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(UserRole)
admin.site.register(RolePermission)
