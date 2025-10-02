from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import SlotAgenda, Paciente, Dentista, Servicio
from django.utils import timezone
from datetime import time


class ReservaCapacityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dentista = Dentista.objects.create(nombre='Ana', apellido='Perez', especialidad='Ortodoncia')
        self.paciente = Paciente.objects.create(nombre='Juan', apellido='Lopez')
        self.servicio = Servicio.objects.create(nombre='Limpieza', duracion_min=30, precio=30)
        # slot con capacidad 1
        self.slot = SlotAgenda.objects.create(dentista=self.dentista, servicio=self.servicio, fecha=timezone.localdate(), hora=time(10,0), capacidad=1)

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
        self.dentista = Dentista.objects.create(nombre='Carlos', apellido='Ruiz')

    def test_generate_slots_endpoint(self):
        url = reverse('generar-slots', kwargs={'dentista_id': self.dentista.id})
        payload = {'fecha': timezone.localdate().isoformat(), 'desde': '08:00', 'hasta': '10:00'}
        r = self.client.post(url, payload, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue('created' in r.data)
