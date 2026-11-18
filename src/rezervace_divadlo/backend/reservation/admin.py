from django.contrib import admin

from .models import Hall, Performance, Play, Reservation, ReservationSeat, Seat

# Catalogue data: safe to edit directly.
admin.site.register([Play, Hall, Seat, Performance])


class ReadOnlyAdmin(admin.ModelAdmin):
    """Reservation state changes only through services.py; the admin is for inspection."""

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Reservation)
class ReservationAdmin(ReadOnlyAdmin):
    list_display = ("id", "owner", "performance", "status", "hold_until", "created_at")
    list_filter = ("status",)


@admin.register(ReservationSeat)
class ReservationSeatAdmin(ReadOnlyAdmin):
    list_display = ("id", "reservation", "performance", "seat", "active")
    list_filter = ("active",)
