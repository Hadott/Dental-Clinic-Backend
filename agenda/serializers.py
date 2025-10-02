from rest_framework import serializers
from .models import SlotAgenda, Reserva, Servicio, Dentista, Paciente

class SlotAgendaSerializer(serializers.ModelSerializer):
    dentista = serializers.StringRelatedField()
    servicio = serializers.StringRelatedField()

    class Meta:
        model = SlotAgenda
        fields = ('id', 'dentista', 'servicio', 'fecha', 'hora', 'capacidad')


class ReservaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = ('slot', 'paciente', 'servicio')

    def validate(self, data):
        # validaciones simples
        return data

    def create(self, validated_data):
        from django.db import transaction
        slot = validated_data['slot']
        paciente = validated_data['paciente']
        servicio = validated_data.get('servicio')

        # Control transaccional: no exceder capacidad
        with transaction.atomic():
            reservas_actuales = slot.reservas.select_for_update().count()
            if reservas_actuales < slot.capacidad:
                reserva = Reserva.objects.create(slot=slot, paciente=paciente, servicio=servicio, sobrecupo=False)
                return reserva
            else:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError({'detail': 'El slot está lleno, no se permiten más reservas.'})
