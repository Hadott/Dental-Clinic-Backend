from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import SlotAgenda, Reserva, Dentista, Paciente
from .serializers import SlotAgendaSerializer, ReservaCreateSerializer, PacienteSerializer
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from django.db import transaction

# Reutilizamos la lógica de generación para permitir que la misma lógica sea llamada
# desde la vista y desde un comando management.
from .slots_generator import generate_slots_for_day, generate_slots_range


class SlotsDisponiblesList(generics.ListAPIView):
    serializer_class = SlotAgendaSerializer

    def get_queryset(self):
        # devolver slots >= hoy
        hoy = timezone.localdate()
        return SlotAgenda.objects.filter(fecha__gte=hoy).order_by('fecha', 'hora')


class CrearReserva(generics.CreateAPIView):
    serializer_class = ReservaCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserva = serializer.save()
        return Response({'id': reserva.id, 'sobrecupo': reserva.sobrecupo}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def generar_slots(request, dentista_id):
    """Genera slots usando la lógica centralizada en `slots_generator`.
    body:
      - fecha: YYYY-MM-DD (requerido)
      - desde: HH:MM (opcional, default 08:00)
      - hasta: HH:MM (opcional, default 16:00)
      - dias: int (opcional). Si se especifica, genera ese número de días empezando en `fecha`.
    """
    import datetime
    try:
        dentista = Dentista.objects.get(pk=dentista_id)
    except Dentista.DoesNotExist:
        return Response({'detail': 'Dentista no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    fecha = request.data.get('fecha')
    desde = request.data.get('desde', '08:00')
    hasta = request.data.get('hasta', '16:00')
    dias = request.data.get('dias')

    if not fecha:
        return Response({'detail': 'Se requiere campo fecha (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
    except Exception:
        return Response({'detail': 'Formato de fecha inválido. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if dias:
            dias = int(dias)
        else:
            dias = 1
    except Exception:
        return Response({'detail': 'El campo dias debe ser un entero.'}, status=status.HTTP_400_BAD_REQUEST)

    # si dias > 1 usamos generate_slots_range
    if dias > 1:
        end_date = fecha_obj + datetime.timedelta(days=dias - 1)
        created = generate_slots_range(dentista, fecha_obj, end_date, desde=desde, hasta=hasta)
    else:
        created = generate_slots_for_day(dentista, fecha_obj, desde=desde, hasta=hasta)

    return Response({'created': created}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def slots_por_fecha(request):
    """Endpoint adicional útil: filtrar por fecha y opcionalmente por dentista.
    Query params: fecha=YYYY-MM-DD, dentista_id=1
    """
    import datetime
    fecha = request.GET.get('fecha')
    dentista_id = request.GET.get('dentista_id')
    qs = SlotAgenda.objects.all()
    if fecha:
        try:
            fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
            qs = qs.filter(fecha=fecha_obj)
        except Exception:
            return Response({'detail': 'Formato de fecha inválido. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
    if dentista_id:
        qs = qs.filter(dentista_id=dentista_id)
    serializer = SlotAgendaSerializer(qs.order_by('hora'), many=True)
    return Response(serializer.data)


@api_view(['POST'])
def bulk_create_pacientes(request):
    """
    Endpoint para crear múltiples pacientes desde sistemas externos
    Acepta una lista de pacientes y los crea en lote
    """
    if not isinstance(request.data, list):
        return Response(
            {'error': 'Se espera una lista de pacientes'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_pacientes = []
    errors = []
    
    with transaction.atomic():
        for i, paciente_data in enumerate(request.data):
            try:
                # Verificar si ya existe un paciente similar (evitar duplicados exactos)
                existing = Paciente.objects.filter(
                    rut=paciente_data.get('rut'),
                    email=paciente_data.get('email')
                ).first()
                
                if existing:
                    # Si existe, actualizar los datos
                    serializer = PacienteSerializer(existing, data=paciente_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        created_pacientes.append({
                            'index': i,
                            'action': 'updated',
                            'paciente': serializer.data
                        })
                    else:
                        errors.append({
                            'index': i,
                            'errors': serializer.errors,
                            'data': paciente_data
                        })
                else:
                    # Si no existe, crear nuevo
                    serializer = PacienteSerializer(data=paciente_data)
                    if serializer.is_valid():
                        serializer.save()
                        created_pacientes.append({
                            'index': i,
                            'action': 'created',
                            'paciente': serializer.data
                        })
                    else:
                        errors.append({
                            'index': i,
                            'errors': serializer.errors,
                            'data': paciente_data
                        })
                        
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'data': paciente_data
                })
    
    return Response({
        'success_count': len(created_pacientes),
        'error_count': len(errors),
        'created_pacientes': created_pacientes,
        'errors': errors
    }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)


@api_view(['GET'])
def system_status(request):
    """
    Endpoint para verificar el estado del sistema y contadores
    """
    from .models import Region, Servicio, Dentista, Paciente, SlotAgenda, Reserva
    
    return Response({
        'status': 'active',
        'timestamp': timezone.now(),
        'counts': {
            'regiones': Region.objects.count(),
            'servicios': Servicio.objects.count(),
            'dentistas': Dentista.objects.count(),
            'pacientes': Paciente.objects.count(),
            'slots_agenda': SlotAgenda.objects.count(),
            'reservas': Reserva.objects.count()
        },
        'data_sources': {
            'allow_duplicate_rut': True,
            'bulk_endpoints_available': True,
            'external_integration_ready': True
        }
    })
