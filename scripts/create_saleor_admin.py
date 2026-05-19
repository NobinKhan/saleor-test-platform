#!/usr/bin/env python3
"""Create default Saleor admin user (run inside saleor-api container)."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get("SALEOR_ADMIN_EMAIL", "admin@example.com")
password = os.environ.get("SALEOR_ADMIN_PASSWORD", "admin123456")

user, created = User.objects.get_or_create(
    email=email,
    defaults={"is_staff": True, "is_active": True, "is_superuser": True},
)
if created:
    user.set_password(password)
    user.save()
    print(f"Created admin: {email}")
else:
    user.is_staff = True
    user.is_active = True
    user.is_superuser = True
    user.set_password(password)
    user.save()
    print(f"Updated admin: {email}")
