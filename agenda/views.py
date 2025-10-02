from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import SlotAgenda, Reserva, Dentista
from .serializers import SlotAgendaSerializer, ReservaCreateSerializer
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response

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
