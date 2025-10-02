from django.urls import path
from .views import SlotsDisponiblesList, CrearReserva, generar_slots

urlpatterns = [
    path('slots/', SlotsDisponiblesList.as_view(), name='slots-disponibles'),
    path('reservas/', CrearReserva.as_view(), name='crear-reserva'),
    path('dentistas/<int:dentista_id>/generar_slots/', generar_slots, name='generar-slots'),
]
