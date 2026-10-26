from django.contrib import admin
from .models import Permission, UserPermission


admin.site.register(Permission)
admin.site.register(UserPermission)