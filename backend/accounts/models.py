from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    position = models.CharField(max_length=100, blank=True)
    GENDER_CHOICES = [('F', 'أنثى'), ('M', 'ذكر')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)