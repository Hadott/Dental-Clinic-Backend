from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import SlotAgenda, Reserva
from .serializers import SlotAgendaSerializer, ReservaCreateSerializer
from django.utils import timezone


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
