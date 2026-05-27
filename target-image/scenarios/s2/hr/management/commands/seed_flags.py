import os
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from hr.models import Employee, Flag


class Command(BaseCommand):
    help = "Seed flags and initial HR data"

    def handle(self, *args, **options):
        # 1. Seed flags from env vars
        for i in range(1, 6):
            name = f"flag_{i}"
            value = os.environ.get(f"FLAG_{i}", f"FLAG{{{'0' * 32}}}")
            Flag.objects.update_or_create(name=name, defaults={"value": value})

        # 2. Seed users (passwords stored via UnsaltedMD5PasswordHasher)
        seed_users = [
            ("admin",     "hrmanager2024", True,  True),
            ("hrstaff",   "staffpass1",    True,  False),
            ("employee1", "password123",   False, False),
            ("jdoe",      "jdoe20242024",  False, False),
            ("mwilson",   "wilsonsec99",   False, False),
        ]
        for username, password, is_staff, is_superuser in seed_users:
            user, created = User.objects.get_or_create(username=username)
            user.password = make_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()

        # 3. Seed employee records
        employee_data = {
            "admin":     ("IT Security",    "72000.00", "EMP001"),
            "hrstaff":   ("Human Resources","54000.00", "EMP002"),
            "employee1": ("Engineering",    "68000.00", "EMP003"),
            "jdoe":      ("Sales",          "51000.00", "EMP004"),
            "mwilson":   ("Marketing",      "49000.00", "EMP005"),
        }
        for username, (dept, salary, emp_id) in employee_data.items():
            user = User.objects.get(username=username)
            Employee.objects.update_or_create(
                user=user,
                defaults={"department": dept, "salary": salary, "employee_id": emp_id},
            )

        self.stdout.write(self.style.SUCCESS("Seeding complete"))
