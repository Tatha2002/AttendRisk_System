from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager): # BaseUserManager: Defines How User Is Created

    # These methods tell Django how to create user.
    def create_user(self, email, phone, password=None, **extra_fields):  
        # print(f'User created: {self.model}')
        
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)    
        user = self.model(email=email, phone=phone, **extra_fields)     
        user.set_password(password)             # Password hashing
        # user.save(using=self._db)
        user.save()
        return user

    # These methods tell Django how to create Super users.
    def create_superuser(self, email, phone, password=None,**extra_fields):
        extra_fields.setdefault("is_staff",True)
        extra_fields.setdefault("is_superuser",True)

        return self.create_user(email, phone, password, **extra_fields)