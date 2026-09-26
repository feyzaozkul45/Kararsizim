from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

username_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_.]{3,20}$",
    message="Kullanıcı adı 3–20 karakter olmalı; sadece harf, rakam, _ ve . içerebilir.",
)


class User(AbstractUser):
    username = models.CharField(
        "kullanıcı adı",
        max_length=20,
        unique=True,
        validators=[username_validator],
        error_messages={"unique": "Bu kullanıcı adı zaten alınmış."},
    )
    email = models.EmailField(
        "e-posta",
        unique=True,
        error_messages={"unique": "Bu e-posta adresiyle zaten bir hesap var."},
    )

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
