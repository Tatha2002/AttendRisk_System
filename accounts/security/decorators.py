from functools import wraps
from django.shortcuts import redirect

from rest_framework.exceptions import AuthenticationFailed

from ..models import User
from ..security.jwt_auth import decode_access_token


def jwt_login_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.COOKIES.get("access_token")

        if not token:
            return redirect("login")

        try:
            user_id = decode_access_token(token)
            user = User.objects.get(id=user_id)

            # Store authenticated user on request
            request.jwt_user = user

        except AuthenticationFailed:
            return redirect("refresh_token")

        except User.DoesNotExist:
            response = redirect("login")
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

        return view_func(request, *args, **kwargs)

    return wrapper