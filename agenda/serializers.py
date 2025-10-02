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

            # verificar sobrecupos permitidos por slot
            sobrecupos_actuales_slot = slot.reservas.filter(sobrecupo=True).count()
            if sobrecupos_actuales_slot < slot.max_overbook:
                # verificar límite diario del dentista
                fecha = slot.fecha
                dentista = slot.dentista
                sobrecupos_dia = Reserva.objects.filter(slot__dentista=dentista, slot__fecha=fecha, sobrecupo=True).count()
                if sobrecupos_dia < dentista.max_overbook_day:
                    reserva = Reserva.objects.create(slot=slot, paciente=paciente, servicio=servicio, sobrecupo=True)
                    return reserva

            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({'detail': 'El slot está lleno y no se permiten sobrecupos adicionales.'})
