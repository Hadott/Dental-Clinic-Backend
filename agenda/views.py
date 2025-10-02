from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import SlotAgenda, Reserva
from .serializers import SlotAgendaSerializer, ReservaCreateSerializer
from django.utils import timezone
from .models import Dentista
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response


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
    """Genera slots de 30 minutos para un dentista en una fecha dada.
    body: {"fecha": "YYYY-MM-DD", "desde": "08:00", "hasta": "16:00"}
    """
    import datetime
    try:
        dentista = Dentista.objects.get(pk=dentista_id)
    except Dentista.DoesNotExist:
        return Response({'detail': 'Dentista no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    fecha = request.data.get('fecha')
    desde = request.data.get('desde', '08:00')
    hasta = request.data.get('hasta', '16:00')
    if not fecha:
        return Response({'detail': 'Se requiere campo fecha (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)

    fecha_obj = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
    t_desde = datetime.datetime.strptime(desde, '%H:%M').time()
    t_hasta = datetime.datetime.strptime(hasta, '%H:%M').time()

    # generar slots de 30 minutos
    current = datetime.datetime.combine(fecha_obj, t_desde)
    end = datetime.datetime.combine(fecha_obj, t_hasta)
    created = 0
    while current <= end:
        hora = current.time()
        # crear slot si no existe
        SlotAgenda.objects.get_or_create(dentista=dentista, fecha=fecha_obj, hora=hora, defaults={'capacidad': 1})
        created += 1
        current += datetime.timedelta(minutes=30)

    return Response({'created': created}, status=status.HTTP_201_CREATED)
