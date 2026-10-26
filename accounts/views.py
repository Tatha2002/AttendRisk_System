from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

from rest_framework.exceptions import AuthenticationFailed
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpRequest
from django.contrib import messages
from .models import User

from accounts.security.jwt_auth import (create_access_token, create_refresh_token, decode_access_token, decode_refresh_token)

@never_cache
@login_required(login_url="login")
def home(request):
    return render(request, 'home.html')

def register_view(request):
    if request.method == "POST":
        print(request.POST)
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Password Validation
        if password != confirm_password:
            messages.error(request,"Password and Confirm Password do not match.")
            return redirect("register")

        # Email Check
        if User.objects.filter(email=email).exists():
            messages.error(request,"Email already exists.")
            return redirect("register")

        # Phone Check
        if User.objects.filter(phone=phone).exists():
            messages.error(request,"Phone number already exists.")
            return redirect("register")

        # create_user method from UserManager
        User.objects.create_user(email=email, phone=phone, password=password, role=role)
        
        messages.success(request,"Registration Successful. Please Login.")
        return redirect("login")

    return render(request,"accounts/register.html")


def login_view(request):
    context = {
        "error": ""
    }

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # ---------- Authentication ----------
        user = authenticate(request, username=username, password=password)

        if not user:
            context["error"] = "Invalid Email/Phone or Password"
            return render(request, "accounts/login.html", context)

        # ---------- Session Management ----------
        login(request, user)

        # ---------- JWT Token Generation ----------
        access_token = create_access_token(user.id, user.role)

        refresh_token = create_refresh_token(user.id, user.role)

        # ---------- Response ----------
        response: HttpResponseRedirect = redirect("dashboard")

        # ---------- Store JWT in Cookies ----------
        response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="Lax")
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="Lax")
        return response

    return render(request, "accounts/login.html", context)


def refresh_token_view(request):
    refresh_token = request.COOKIES.get("refresh_token")

    # Refresh Token Missing
    if not refresh_token:
        response = redirect("login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

    try:
        # Decode Refresh Token
        user_id = decode_refresh_token(refresh_token)
        user = User.objects.get(id=user_id)

        # Generate New Tokens
        new_access_token = create_access_token(user.id, user.role)
        # new_refresh_token = create_refresh_token(user.id, user.role)

        response = redirect("dashboard")

        response.set_cookie(key="access_token",value=new_access_token,httponly=True,samesite="Lax")
        # response.set_cookie(key="refresh_token",value=new_refresh_token,httponly=True,samesite="Lax")
        return response

    except User.DoesNotExist:
        response = redirect("login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

    except AuthenticationFailed:
        response = redirect("login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


@never_cache
@login_required(login_url="login")
def dashboard(request):
    token = request.COOKIES.get("access_token")

    if not token:
        return redirect("login")

    try:
        user_id = decode_access_token(token)
        user = User.objects.get(id=user_id)

    except AuthenticationFailed:
        return redirect("refresh_token")

    except User.DoesNotExist:
        response = redirect("login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

    response = render(request, "accounts/dashboard.html", {
            "user": user,
            "is_authenticated": True,
        }
    )

    # manually clearing cache.
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response

def logout_view(request):
    print("BEFORE LOGOUT:", request.COOKIES)
    response = redirect("login")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    logout(request)
    print("AFTER LOGOUT:", request.COOKIES)
    return response