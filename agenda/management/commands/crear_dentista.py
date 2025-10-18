from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from agenda.models import Dentista


class Command(BaseCommand):
    help = 'Crear usuario dentista'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username del dentista', required=True)
        parser.add_argument('--password', type=str, help='Password del dentista', required=True)
        parser.add_argument('--email', type=str, help='Email del dentista', default='')
        parser.add_argument('--nombre', type=str, help='Nombre del dentista', required=True)
        parser.add_argument('--apellido', type=str, help='Apellido del dentista', required=True)
        parser.add_argument('--especialidad', type=str, help='Especialidad del dentista', default='')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        nombre = options['nombre']
        apellido = options['apellido']
        especialidad = options['especialidad']

        # Crear usuario
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'El usuario {username} ya existe')
            )
            return

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=nombre,
            last_name=apellido
        )

        # Crear perfil de dentista
        dentista = Dentista.objects.create(
            user=user,
            nombre=nombre,
            apellido=apellido,
            especialidad=especialidad,
            email=email,
            activo=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Dentista creado exitosamente: {dentista} (Usuario: {username})'
            )
        )