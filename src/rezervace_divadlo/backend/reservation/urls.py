from django.urls import path

from . import views

urlpatterns = [
    path("", views.play_list, name="play_list"),
    path("plays/<int:pk>/", views.play_detail, name="play_detail"),
    path("performances/<int:pk>/seats/", views.seat_selection, name="seat_selection"),
    path("reservations/<int:pk>/form/", views.reservation_form, name="reservation_form"),
    path("reservations/<int:pk>/summary/", views.reservation_summary, name="reservation_summary"),
    path("reservations/<int:pk>/success/", views.reservation_success, name="reservation_success"),
]
