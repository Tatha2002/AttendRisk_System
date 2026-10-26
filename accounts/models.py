from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager

# creating a custom Django user model
class User(AbstractUser):   # AbstractUser: User structure + built-in user functionality
    HR = "HR"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"

    ROLE_CHOICES = [
        (HR, "HR"),
        (MANAGER, "MANAGER"),
        (EMPLOYEE, "EMPLOYEE"),
    ]

    username = None     # we are removing username, so we will use email, phone as the unique identifier
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)

    USERNAME_FIELD = "email"      
    REQUIRED_FIELDS = ["phone"]

    objects = UserManager()         

    def __str__(self):
        return self.email