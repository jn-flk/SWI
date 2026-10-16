from django.contrib import admin

from .models import NotificationRequest


@admin.register(NotificationRequest)
class NotificationRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation_id", "event", "status", "attempts", "next_attempt_at", "created_at")
    list_filter = ("status", "event")
    search_fields = ("event", "=reservation_id")
    readonly_fields = tuple(field.name for field in NotificationRequest._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
