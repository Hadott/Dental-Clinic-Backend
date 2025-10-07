from rest_framework import serializers
from django.db import IntegrityError
from .models import SlotAgenda, Reserva, Servicio, Dentista, Paciente, Region


class SlotAgendaSerializer(serializers.ModelSerializer):
    dentista = serializers.StringRelatedField()
    servicio = serializers.StringRelatedField()

    class Meta:
        model = SlotAgenda
        fields = ('id', 'dentista', 'servicio', 'fecha', 'hora', 'capacidad', 'max_overbook')


class ReservaCreateSerializer(serializers.Serializer):
    # Campos principales del modelo Reserva
    slot = serializers.PrimaryKeyRelatedField(queryset=SlotAgenda.objects.all(), required=False, allow_null=True)
    paciente = serializers.IntegerField()
    servicio = serializers.IntegerField(required=False)
    
    # Campos alternativos para crear el slot
    dentista = serializers.IntegerField(required=False)
    fecha = serializers.DateField(required=False)
    hora_inicio = serializers.TimeField(required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        # Si no se proporciona slot, se debe proporcionar dentista, fecha y hora_inicio
        if not data.get('slot'):
            if not all([data.get('dentista'), data.get('fecha'), data.get('hora_inicio')]):
                raise serializers.ValidationError(
                    "Se debe proporcionar 'slot' o los campos 'dentista', 'fecha' y 'hora_inicio'"
                )
        return data

    def create(self, validated_data):
        # Debug: imprimir los datos que llegan
        print("=== DEBUG SERIALIZER CREATE ===")
        print("validated_data:", validated_data)
        print("Tipos de datos:")
        for key, value in validated_data.items():
            print(f"  {key}: {type(value)} = {value}")
        print("================================")
        
        # Extraer campos adicionales
        dentista_id = validated_data.pop('dentista', None)
        fecha = validated_data.pop('fecha', None)
        hora_inicio = validated_data.pop('hora_inicio', None)
        observaciones = validated_data.pop('observaciones', None)
        
        # Obtener instancias de paciente y servicio
        paciente_data = validated_data.get('paciente')
        servicio_id = validated_data.get('servicio')
        
        # Manejar si paciente es un objeto o un ID
        if isinstance(paciente_data, Paciente):
            paciente = paciente_data
        else:
            try:
                paciente_id = int(paciente_data) if paciente_data else None
                if not paciente_id:
                    raise serializers.ValidationError("ID de paciente es requerido")
                paciente = Paciente.objects.get(id=paciente_id)
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"ID de paciente inválido: {paciente_data}")
            except Paciente.DoesNotExist:
                raise serializers.ValidationError(f"Paciente con ID {paciente_id} no existe")
        
        servicio = None
        if servicio_id:
            # Manejar si servicio es un objeto o un ID
            if isinstance(servicio_id, Servicio):
                servicio = servicio_id
            else:
                try:
                    servicio_id_int = int(servicio_id)
                    servicio = Servicio.objects.get(id=servicio_id_int)
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"ID de servicio inválido: {servicio_id}")
                except Servicio.DoesNotExist:
                    raise serializers.ValidationError(f"Servicio con ID {servicio_id} no existe")
        
        # Si no hay slot, buscar o crear uno
        slot = validated_data.get('slot')
        if not slot and dentista_id and fecha and hora_inicio:
            try:
                dentista = Dentista.objects.get(id=dentista_id)
                
                # Buscar slot existente
                slot, created = SlotAgenda.objects.get_or_create(
                    dentista=dentista,
                    fecha=fecha,
                    hora=hora_inicio,
                    defaults={
                        'servicio': servicio,
                        'capacidad': 1,
                        'max_overbook': 0
                    }
                )
            except Dentista.DoesNotExist:
                raise serializers.ValidationError(f"Dentista con ID {dentista_id} no existe")
        
        if not slot:
            raise serializers.ValidationError("No se pudo crear o encontrar un slot válido")
        
        # Lógica transaccional común en clínicas: contar reservas con select_for_update
        from django.db import transaction

        with transaction.atomic():
            # Primero verificar si ya existe esta reserva exacta
            existing_reserva = Reserva.objects.filter(slot=slot, paciente=paciente).first()
            if existing_reserva:
                # Si ya existe, retornar la existente en lugar de crear una nueva
                return existing_reserva
            
            reservas_actuales = slot.reservas.select_for_update().count()
            if reservas_actuales < slot.capacidad:
                try:
                    return Reserva.objects.create(slot=slot, paciente=paciente, servicio=servicio, sobrecupo=False)
                except IntegrityError:
                    # Si falla por constraint único, buscar la reserva existente
                    existing_reserva = Reserva.objects.filter(slot=slot, paciente=paciente).first()
                    if existing_reserva:
                        return existing_reserva
                    raise

            # Si capacidad alcanzada, permitir sobrecupo si el slot y el dentista lo permiten
            sobrecupos_actuales_slot = slot.reservas.filter(sobrecupo=True).count()
            if sobrecupos_actuales_slot < slot.max_overbook:
                # comprobar límite diario del dentista
                fecha = slot.fecha
                dentista = slot.dentista
                sobrecupos_dia = Reserva.objects.filter(slot__dentista=dentista, slot__fecha=fecha, sobrecupo=True).count()
                if sobrecupos_dia < dentista.max_overbook_day:
                    try:
                        return Reserva.objects.create(slot=slot, paciente=paciente, servicio=servicio, sobrecupo=True)
                    except IntegrityError:
                        # Si falla por constraint único, buscar la reserva existente
                        existing_reserva = Reserva.objects.filter(slot=slot, paciente=paciente).first()
                        if existing_reserva:
                            return existing_reserva
                        raise

            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({'detail': 'El slot está lleno y no se permiten sobrecupos adicionales.'})




class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ('id', 'nombre', 'codigo')


class DentistaSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    region_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Dentista
        fields = ('id', 'nombre', 'apellido', 'especialidad', 'email', 'telefono', 'region', 'region_id', 'max_overbook_day')


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ('id', 'nombre', 'duracion_min', 'precio')


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ('id', 'rut', 'nombre', 'apellido', 'telefono', 'email', 'fecha_registro')
    
    def validate_rut(self, value):
        """Validar formato básico del RUT (permite duplicados)"""
        if not value:
            raise serializers.ValidationError("El RUT es requerido")
        return value.strip().upper()
    
    def validate_email(self, value):
        """Validar email pero permitir duplicados si es necesario"""
        if value:
            return value.lower().strip()
        return value


class ReservaReadSerializer(serializers.ModelSerializer):
    """Serializer para lectura de reservas con información detallada"""
    slot = SlotAgendaSerializer(read_only=True)
    paciente = PacienteSerializer(read_only=True)
    servicio = ServicioSerializer(read_only=True)
    
    class Meta:
        model = Reserva
        fields = ('id', 'slot', 'paciente', 'servicio', 'creado_en', 'sobrecupo')
