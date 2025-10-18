from django.urls import path, include
from .views import SlotsDisponiblesList, CrearReserva, generar_slots
from .views import slots_por_fecha
from rest_framework.routers import DefaultRouter
from .viewsets import DentistaViewSet, ServicioViewSet, PacienteViewSet, RegionViewSet, ReservaViewSet
from .auth_views import (
    LoginView, ProfileView, dashboard_stats, AgendaDentistaView,
    CrearSlotAgendaView, SlotAgendaDetailView, MisReservasView,
    cancelar_reserva, VacacionesView, VacacionDetailView,
    HorarioTrabajoView, HorarioTrabajoDetailView, generar_slots_auto,
    calendar_events
)

router = DefaultRouter()
router.register(r'regiones', RegionViewSet, basename='region')
router.register(r'dentistas', DentistaViewSet, basename='dentista')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'reservas', ReservaViewSet, basename='reserva')

urlpatterns = [
    # URLs existentes
    path('slots/', SlotsDisponiblesList.as_view(), name='slots-disponibles'),
    path('reservas/', CrearReserva.as_view(), name='crear-reserva'),
    path('dentistas/<int:dentista_id>/generar_slots/', generar_slots, name='generar-slots'),
    path('slots_por_fecha/', slots_por_fecha, name='slots-por-fecha'),
    path('api/', include(router.urls)),
    
    # URLs de autenticación y panel dentista
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/dashboard/', dashboard_stats, name='dashboard-stats'),
    
    # Gestión de agenda del dentista
    path('dentista/agenda/', AgendaDentistaView.as_view(), name='dentista-agenda'),
    path('dentista/slots/crear/', CrearSlotAgendaView.as_view(), name='dentista-crear-slot'),
    path('dentista/slots/<int:pk>/', SlotAgendaDetailView.as_view(), name='dentista-slot-detail'),
    path('dentista/slots/generar/', generar_slots_auto, name='generar-slots-auto'),
    
    # Gestión de reservas del dentista
    path('dentista/reservas/', MisReservasView.as_view(), name='dentista-reservas'),
    path('dentista/reservas/<int:reserva_id>/cancelar/', cancelar_reserva, name='cancelar-reserva'),
    
    # Gestión de vacaciones
    path('dentista/vacaciones/', VacacionesView.as_view(), name='dentista-vacaciones'),
    path('dentista/vacaciones/<int:pk>/', VacacionDetailView.as_view(), name='vacacion-detail'),
    
    # Gestión de horarios
    path('dentista/horarios/', HorarioTrabajoView.as_view(), name='dentista-horarios'),
    path('dentista/horarios/<int:pk>/', HorarioTrabajoDetailView.as_view(), name='horario-detail'),
    
    # Calendario
    path('dentista/calendar/', calendar_events, name='calendar-events'),
]
