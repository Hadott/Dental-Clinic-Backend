from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import (
    Dentista, SlotAgenda, Reserva, Vacacion, HorarioTrabajo, 
    Servicio, Paciente
)
from .serializers import (
    LoginSerializer, DentistaDetailSerializer, VacacionSerializer,
    HorarioTrabajoSerializer, SlotAgendaCreateSerializer, AgendaDentistaSerializer,
    EstadisticasDentistaSerializer, ReservaReadSerializer
)


class LoginView(generics.CreateAPIView):
    """Vista para login de dentistas"""
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'dentista': DentistaDetailSerializer(user.dentista).data
            }
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Vista para ver y actualizar el perfil del dentista"""
    serializer_class = DentistaDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.dentista


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas para el dashboard del dentista"""
    dentista = request.user.dentista
    hoy = timezone.localdate()
    
    # Citas de hoy
    citas_hoy = SlotAgenda.objects.filter(
        dentista=dentista,
        fecha=hoy
    ).aggregate(
        total=Count('reservas')
    )['total'] or 0
    
    # Citas de esta semana
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    citas_semana = SlotAgenda.objects.filter(
        dentista=dentista,
        fecha__range=[inicio_semana, fin_semana]
    ).aggregate(
        total=Count('reservas')
    )['total'] or 0
    
    # Citas de este mes
    citas_mes = SlotAgenda.objects.filter(
        dentista=dentista,
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).aggregate(
        total=Count('reservas')
    )['total'] or 0
    
    # Próximas citas (próximos 7 días)
    fin_proximos = hoy + timedelta(days=7)
    proximas_citas = SlotAgenda.objects.filter(
        dentista=dentista,
        fecha__range=[hoy, fin_proximos],
        reservas__isnull=False
    ).prefetch_related('reservas', 'servicio').distinct()[:10]
    
    # Pacientes únicos atendidos este mes
    pacientes_mes = Reserva.objects.filter(
        slot__dentista=dentista,
        slot__fecha__year=hoy.year,
        slot__fecha__month=hoy.month
    ).values('paciente').distinct().count()
    
    stats = {
        'citas_hoy': citas_hoy,
        'citas_semana': citas_semana,
        'citas_mes': citas_mes,
        'proximas_citas': AgendaDentistaSerializer(proximas_citas, many=True).data,
        'pacientes_atendidos_mes': pacientes_mes
    }
    
    return Response(EstadisticasDentistaSerializer(stats).data)


class AgendaDentistaView(generics.ListAPIView):
    """Vista para ver la agenda del dentista"""
    serializer_class = AgendaDentistaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Desactivar paginación

    def get_queryset(self):
        dentista = self.request.user.dentista
        fecha = self.request.query_params.get('fecha')
        
        queryset = SlotAgenda.objects.filter(dentista=dentista)
        
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha=fecha_obj)
            except ValueError:
                pass
        else:
            # Por defecto, mostrar desde hoy
            queryset = queryset.filter(fecha__gte=timezone.localdate())
        
        return queryset.order_by('fecha', 'hora').prefetch_related('reservas', 'servicio')


class CrearSlotAgendaView(generics.CreateAPIView):
    """Vista para que el dentista cree slots manualmente"""
    serializer_class = SlotAgendaCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(dentista=self.request.user.dentista)


class SlotAgendaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vista para ver, actualizar o eliminar un slot específico"""
    serializer_class = SlotAgendaCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SlotAgenda.objects.filter(dentista=self.request.user.dentista)


class MisReservasView(generics.ListAPIView):
    """Vista para ver las reservas del dentista"""
    serializer_class = ReservaReadSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Desactivar paginación

    def get_queryset(self):
        dentista = self.request.user.dentista
        fecha = self.request.query_params.get('fecha')
        estado = self.request.query_params.get('estado')  # 'pendiente', 'completada'
        
        queryset = Reserva.objects.filter(slot__dentista=dentista)
        
        if fecha:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                queryset = queryset.filter(slot__fecha=fecha_obj)
            except ValueError:
                pass
        
        # Por defecto mostrar desde hoy hacia adelante
        if not fecha:
            queryset = queryset.filter(slot__fecha__gte=timezone.localdate())
        
        return queryset.order_by('slot__fecha', 'slot__hora').select_related(
            'slot', 'paciente', 'servicio'
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_reserva(request, reserva_id):
    """Cancelar una reserva específica"""
    try:
        reserva = Reserva.objects.get(
            id=reserva_id,
            slot__dentista=request.user.dentista
        )
        reserva.delete()
        return Response({'message': 'Reserva cancelada exitosamente'})
    except Reserva.DoesNotExist:
        return Response(
            {'error': 'Reserva no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )


class VacacionesView(generics.ListCreateAPIView):
    """Vista para ver y crear vacaciones"""
    serializer_class = VacacionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Desactivar paginación

    def get_queryset(self):
        return Vacacion.objects.filter(
            dentista=self.request.user.dentista,
            activa=True
        ).order_by('-fecha_inicio')

    def perform_create(self, serializer):
        serializer.save(dentista=self.request.user.dentista)


class VacacionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vista para ver, actualizar o eliminar una vacación"""
    serializer_class = VacacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vacacion.objects.filter(dentista=self.request.user.dentista)


class HorarioTrabajoView(generics.ListCreateAPIView):
    """Vista para ver y crear horarios de trabajo"""
    serializer_class = HorarioTrabajoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Desactivar paginación

    def get_queryset(self):
        return HorarioTrabajo.objects.filter(
            dentista=self.request.user.dentista,
            activo=True
        ).order_by('dia_semana', 'hora_inicio')

    def perform_create(self, serializer):
        serializer.save(dentista=self.request.user.dentista)


class HorarioTrabajoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vista para ver, actualizar o eliminar un horario de trabajo"""
    serializer_class = HorarioTrabajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HorarioTrabajo.objects.filter(dentista=self.request.user.dentista)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_slots_auto(request):
    """Generar slots automáticamente basado en horarios de trabajo"""
    dentista = request.user.dentista
    fecha_inicio = request.data.get('fecha_inicio')
    fecha_fin = request.data.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        return Response(
            {'error': 'Se requieren fecha_inicio y fecha_fin'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Obtener horarios de trabajo del dentista
    horarios = HorarioTrabajo.objects.filter(dentista=dentista, activo=True)
    
    if not horarios:
        return Response(
            {'error': 'No hay horarios de trabajo configurados'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    slots_creados = 0
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        # Verificar si hay vacaciones en esta fecha
        hay_vacacion = Vacacion.objects.filter(
            dentista=dentista,
            fecha_inicio__lte=fecha_actual,
            fecha_fin__gte=fecha_actual,
            activa=True
        ).exists()
        
        if not hay_vacacion:
            # Obtener horario para el día de la semana
            dia_semana = fecha_actual.weekday()
            horario = horarios.filter(dia_semana=dia_semana).first()
            
            if horario:
                # Generar slots cada 30 minutos
                hora_actual = horario.hora_inicio
                while hora_actual < horario.hora_fin:
                    # Verificar que el slot no exista
                    if not SlotAgenda.objects.filter(
                        dentista=dentista,
                        fecha=fecha_actual,
                        hora=hora_actual
                    ).exists():
                        SlotAgenda.objects.create(
                            dentista=dentista,
                            fecha=fecha_actual,
                            hora=hora_actual,
                            capacidad=1,
                            max_overbook=0,
                            creador=f'auto_{request.user.username}'
                        )
                        slots_creados += 1
                    
                    # Avanzar 30 minutos
                    hora_actual = (
                        datetime.combine(date.today(), hora_actual) + 
                        timedelta(minutes=30)
                    ).time()
        
        fecha_actual += timedelta(days=1)
    
    return Response({
        'message': f'Se crearon {slots_creados} slots automáticamente',
        'slots_creados': slots_creados
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_events(request):
    """Obtener eventos para el calendario del dentista"""
    dentista = request.user.dentista
    
    # Obtener rango de fechas
    fecha_inicio = request.query_params.get('start')
    fecha_fin = request.query_params.get('end')
    
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Por defecto, mostrar el mes actual
        hoy = timezone.localdate()
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = (fecha_inicio.replace(month=fecha_inicio.month % 12 + 1) - 
                    timedelta(days=1))
    
    events = []
    
    # Agregar citas
    reservas = Reserva.objects.filter(
        slot__dentista=dentista,
        slot__fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('slot', 'paciente', 'servicio')
    
    for reserva in reservas:
        events.append({
            'id': f'reserva_{reserva.id}',
            'title': f'{reserva.paciente.nombre} - {reserva.servicio.nombre if reserva.servicio else "Sin servicio"}',
            'start': f'{reserva.slot.fecha}T{reserva.slot.hora}',
            'type': 'reserva',
            'backgroundColor': '#28a745' if not reserva.sobrecupo else '#ffc107',
            'borderColor': '#28a745' if not reserva.sobrecupo else '#ffc107',
            'extendedProps': {
                'reserva_id': reserva.id,
                'paciente': reserva.paciente.nombre,
                'servicio': reserva.servicio.nombre if reserva.servicio else None,
                'sobrecupo': reserva.sobrecupo
            }
        })
    
    # Agregar vacaciones
    vacaciones = Vacacion.objects.filter(
        dentista=dentista,
        activa=True,
        fecha_inicio__lte=fecha_fin,
        fecha_fin__gte=fecha_inicio
    )
    
    for vacacion in vacaciones:
        events.append({
            'id': f'vacacion_{vacacion.id}',
            'title': f'Vacación: {vacacion.motivo}' if vacacion.motivo else 'Vacación',
            'start': str(vacacion.fecha_inicio),
            'end': str(vacacion.fecha_fin + timedelta(days=1)),  # FullCalendar excluye el último día
            'type': 'vacacion',
            'backgroundColor': '#dc3545',
            'borderColor': '#dc3545',
            'extendedProps': {
                'vacacion_id': vacacion.id,
                'motivo': vacacion.motivo
            }
        })
    
    return Response(events)