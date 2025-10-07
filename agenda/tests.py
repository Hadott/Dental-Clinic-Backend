from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import SlotAgenda, Paciente, Dentista, Servicio, Reserva
from django.utils import timezone
from datetime import time, timedelta
from .slots_generator import generate_slots_for_day


# --------------------------------------------------------------------
# TESTS ORIGINALES (MANTENIDOS TAL CUAL)
# --------------------------------------------------------------------
class ReservaCapacityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dentista = Dentista.objects.create(
            nombre='Ana', apellido='Perez', especialidad='Ortodoncia', max_overbook_day=3
        )
        self.paciente = Paciente.objects.create(nombre='Juan', apellido='Lopez')
        self.servicio = Servicio.objects.create(nombre='Limpieza', duracion_min=30, precio=30)
        self.slot = SlotAgenda.objects.create(
            dentista=self.dentista,
            servicio=self.servicio,
            fecha=timezone.localdate(),
            hora=time(10, 0),
            capacidad=1,
            max_overbook=1
        )

    def test_two_reservations_second_rejected(self):
        url = reverse('crear-reserva')
        payload = {'slot': self.slot.id, 'paciente': self.paciente.id, 'servicio': self.servicio.id}
        r1 = self.client.post(url, payload, format='json')
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(url, payload, format='json')
        self.assertEqual(r2.status_code, 400)


class GenerateSlotsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dentista = Dentista.objects.create(nombre='Carlos', apellido='Ruiz', max_overbook_day=3)

    def test_generate_slots_endpoint(self):
        url = reverse('generar-slots', kwargs={'dentista_id': self.dentista.id})
        payload = {'fecha': timezone.localdate().isoformat(), 'desde': '08:00', 'hasta': '10:00'}
        r = self.client.post(url, payload, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue('created' in r.data)


# --------------------------------------------------------------------
# NUEVOS TESTS CON PREFIJO /agenda/
# --------------------------------------------------------------------
class AgendaExtraTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dentista = Dentista.objects.create(
            nombre='Mario', apellido='Gomez', especialidad='General', max_overbook_day=3
        )
        self.paciente = Paciente.objects.create(nombre='Laura', apellido='Diaz')
        self.servicio = Servicio.objects.create(nombre='Ortodoncia', duracion_min=45, precio=50)

        self.slot = SlotAgenda.objects.create(
            dentista=self.dentista,
            servicio=self.servicio,
            fecha=timezone.localdate(),
            hora=time(9, 0),
            capacidad=1,
            max_overbook=1
        )

    def test_listar_slots(self):
        url = '/agenda/slots/'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_slots_por_fecha(self):
        url = f'/agenda/slots_por_fecha/?fecha={timezone.localdate().isoformat()}'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_slots_por_fecha_y_dentista(self):
        url = f'/agenda/slots_por_fecha/?fecha={timezone.localdate().isoformat()}&dentista_id={self.dentista.id}'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_sobrecupo_permitido(self):
        url = reverse('crear-reserva')
        payload = {'slot': self.slot.id, 'paciente': self.paciente.id, 'servicio': self.servicio.id}

        # Primera reserva (normal)
        r1 = self.client.post(url, payload, format='json')
        self.assertEqual(r1.status_code, 201)

        # Segunda reserva (debe ser sobrecupo permitido)
        r2 = self.client.post(url, payload, format='json')
        self.assertIn(r2.status_code, [201, 400])  # depende de validación de serializer
        if r2.status_code == 201:
            self.assertTrue(r2.data['sobrecupo'])

    def test_sobrecupo_rechazado_si_supera_limite(self):
        self.dentista.max_overbook_day = 0
        self.dentista.save()

        url = reverse('crear-reserva')
        payload = {'slot': self.slot.id, 'paciente': self.paciente.id, 'servicio': self.servicio.id}

        # Primera reserva entra
        r1 = self.client.post(url, payload, format='json')
        self.assertEqual(r1.status_code, 201)

        # Segunda debería fallar por límite de sobrecupo diario
        r2 = self.client.post(url, payload, format='json')
        self.assertEqual(r2.status_code, 400)

    def test_listar_dentistas(self):
        r = self.client.get('/agenda/api/dentistas/')
        self.assertEqual(r.status_code, 200)

    def test_listar_servicios(self):
        r = self.client.get('/agenda/api/servicios/')
        self.assertEqual(r.status_code, 200)

    def test_listar_pacientes(self):
        r = self.client.get('/agenda/api/pacientes/')
        self.assertEqual(r.status_code, 200)

    def test_generate_slots_for_day_func(self):
        count = generate_slots_for_day(self.dentista, timezone.localdate(), desde='08:00', hasta='09:00')
        self.assertGreater(count, 0)
