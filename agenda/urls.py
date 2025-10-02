from django.urls import path, include
from .views import SlotsDisponiblesList, CrearReserva, generar_slots
from .views import slots_por_fecha
from rest_framework.routers import DefaultRouter
from .viewsets import DentistaViewSet, ServicioViewSet, PacienteViewSet

router = DefaultRouter()
router.register(r'dentistas', DentistaViewSet, basename='dentista')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'pacientes', PacienteViewSet, basename='paciente')

urlpatterns = [
    path('slots/', SlotsDisponiblesList.as_view(), name='slots-disponibles'),
    path('reservas/', CrearReserva.as_view(), name='crear-reserva'),
    path('dentistas/<int:dentista_id>/generar_slots/', generar_slots, name='generar-slots'),
    path('slots_por_fecha/', slots_por_fecha, name='slots-por-fecha'),
    path('api/', include(router.urls)),
]
