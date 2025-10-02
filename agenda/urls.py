from django.urls import path
from .views import SlotsDisponiblesList, CrearReserva

urlpatterns = [
    path('slots/', SlotsDisponiblesList.as_view(), name='slots-disponibles'),
    path('reservas/', CrearReserva.as_view(), name='crear-reserva'),
]
