from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    employee_id = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.username} ({self.department})"


class Flag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.name
