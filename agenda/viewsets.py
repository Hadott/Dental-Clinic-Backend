from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission
from .models import Dentista, Servicio, Paciente
from .serializers import DentistaSerializer, ServicioSerializer, PacienteSerializer


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class DentistaViewSet(viewsets.ModelViewSet):
    queryset = Dentista.objects.all()
    serializer_class = DentistaSerializer
    permission_classes = (IsStaffOrReadOnly,)


class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = (IsStaffOrReadOnly,)


class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = (IsStaffOrReadOnly,)
