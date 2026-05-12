# djangoapp/permissions.py

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Apenas clientes com role='admin'."""
    message = "Acesso restrito a administradores."

    def has_permission(self, request, view):
        try:
            return request.user.is_authenticated and request.user.cliente.is_admin()
        except Exception:
            return False


class IsGestorEstoque(BasePermission):
    """Admin ou gestor de estoque."""
    message = "Acesso restrito a gestores de estoque."

    def has_permission(self, request, view):
        try:
            return request.user.is_authenticated and request.user.cliente.is_gestor_estoque()
        except Exception:
            return False


class IsOwnerOrAdmin(BasePermission):
    """Dono do recurso ou admin."""
    message = "Você não tem permissão para acessar este recurso."

    def has_object_permission(self, request, view, obj):
        try:
            cliente = request.user.cliente
            if cliente.is_admin():
                return True
            # verifica se o objeto pertence ao cliente
            if hasattr(obj, 'cliente'):
                return obj.cliente == cliente
            if hasattr(obj, 'user'):
                return obj.user == request.user
            return False
        except Exception:
            return False