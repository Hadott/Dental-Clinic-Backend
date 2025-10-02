from django.db import models
from django.utils import timezone


class Paciente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Dentista(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    max_overbook_day = models.PositiveIntegerField(default=0, help_text='Máximo de sobrecupos permitidos por día para este dentista')

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.especialidad}"


class Servicio(models.Model):
    nombre = models.CharField(max_length=150)
    duracion_min = models.PositiveIntegerField(help_text='Duración en minutos')
    precio = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.nombre


class SlotAgenda(models.Model):
    dentista = models.ForeignKey(Dentista, on_delete=models.CASCADE, related_name='slots')
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField()
    hora = models.TimeField()
    capacidad = models.PositiveIntegerField(default=1, help_text='Cuántos pacientes caben en este slot')
    max_overbook = models.PositiveIntegerField(default=0, help_text='Cuántos sobrecupos adicionales se permiten en este slot')
    creador = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('dentista', 'fecha', 'hora')

    def __str__(self):
        return f"{self.dentista} - {self.fecha} {self.hora}"

    def clean(self):
        # Validaciones adicionales: un único slot por dentista/fecha/hora y hora dentro del rango 08:00-16:00
        from django.core.exceptions import ValidationError
        import datetime

        # comprobar rango horario
        min_hora = datetime.time(8, 0)
        max_hora = datetime.time(16, 0)
        if self.hora < min_hora or self.hora > max_hora:
            raise ValidationError({'hora': 'La hora debe estar entre 08:00 y 16:00.'})

        # comprobar duplicados manualmente (para dar error amigable antes de DB)
        qs = SlotAgenda.objects.filter(dentista=self.dentista, fecha=self.fecha, hora=self.hora)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError('Ya existe un slot para este dentista en la misma fecha y hora.')

        # comprobar bloques de 30 minutos (mm == 0 o 30)
        if self.hora.minute not in (0, 30):
            raise ValidationError({'hora': 'La hora debe estar en bloques de 30 minutos (mm = 00 o 30).'})

    def save(self, *args, **kwargs):
        # ejecutar validación completa antes de guardar (admin y APIs respetarán esto)
        self.full_clean()
        return super().save(*args, **kwargs)


class Reserva(models.Model):
    slot = models.ForeignKey(SlotAgenda, on_delete=models.CASCADE, related_name='reservas')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='reservas')
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    sobrecupo = models.BooleanField(default=False)

    class Meta:
        unique_together = ('slot', 'paciente')

    def __str__(self):
        return f"Reserva {self.paciente} -> {self.slot} {'(Sobrecupo)' if self.sobrecupo else ''}"
