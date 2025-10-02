"""Lógica reutilizable para generar slots de agenda por dentista.
Se expone `generate_slots_for_day` y `generate_slots_range`.
"""
import datetime
from .models import SlotAgenda


def _parse_time(t):
    if isinstance(t, datetime.time):
        return t
    return datetime.datetime.strptime(t, '%H:%M').time()


def generate_slots_for_day(dentista, fecha, desde='08:00', hasta='16:00', capacidad_default=1):
    """Genera slots de 30 minutos para un dentista en una fecha. Devuelve cantidad creados.

    - dentista: instancia de Dentista
    - fecha: datetime.date
    - desde/hasta: 'HH:MM' o datetime.time
    - capacidad_default: valor por defecto para `capacidad`
    """
    t_desde = _parse_time(desde)
    t_hasta = _parse_time(hasta)

    current = datetime.datetime.combine(fecha, t_desde)
    end = datetime.datetime.combine(fecha, t_hasta)
    created = 0
    # iterar en bloques de 30 minutos; usamos <= end para mantener compatibilidad con la vista original
    while current <= end:
        hora = current.time()
        # get_or_create evita duplicados
        SlotAgenda.objects.get_or_create(
            dentista=dentista,
            fecha=fecha,
            hora=hora,
            defaults={'capacidad': capacidad_default}
        )
        created += 1
        current += datetime.timedelta(minutes=30)

    return created


def generate_slots_range(dentista, start_date, end_date, desde='08:00', hasta='16:00', capacidad_default=1):
    """Genera slots desde start_date hasta end_date (inclusive). Devuelve cantidad creados totales."""
    created_total = 0
    day = start_date
    while day <= end_date:
        created_total += generate_slots_for_day(dentista, day, desde=desde, hasta=hasta, capacidad_default=capacidad_default)
        day += datetime.timedelta(days=1)
    return created_total
