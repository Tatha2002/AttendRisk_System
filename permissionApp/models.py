from django.db import models
from accounts.models import User


class Permission(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.name


class UserPermission(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_permissions'
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("user", "permission")

    def __str__(self):
        return f"{self.user.email} -> {self.permission.name}"