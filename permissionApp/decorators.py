from functools import wraps
from django.shortcuts import render

from .models import UserPermission


def permission_required(permission_name):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            permission_exists = UserPermission.objects.filter(
                user=request.user,
                permission__name=permission_name
            ).exists()

            if not permission_exists:
                return render(
                    request,
                    "errors/403.html",
                    status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator