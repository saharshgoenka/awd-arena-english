import os
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from hr.models import Employee, Flag, PerformanceReport


class Command(BaseCommand):
    help = "Seed flags and initial HR data"

    def handle(self, *args, **options):
        # 1. Seed ONLY flag_4 (the SQLi-reachable flag). The others are served
        #    from env by their views so one UNION injection can't dump them all.
        for i in [4]:
            name = f"flag_{i}"
            value = os.environ.get(f"FLAG_{i}", f"FLAG{{{'0' * 32}}}")
            Flag.objects.update_or_create(name=name, defaults={"value": value})

        # 2. Seed users (passwords stored via UnsaltedMD5PasswordHasher)
        seed_users = [
            ("admin",     "hrmanager2024", True,  True),
            ("hrstaff",   "StaffSpring25!", True,  False),
            ("employee1", "employee1!",   False, False),
            ("jdoe",      "sunrise7",      False, False),
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

        # 4. Seed performance reports (flag_1 BOLA). The restricted consolidated
        #    review is owned by a manager (admin) and carries FLAG_1 at render time.
        #    Each standard report references the restricted report's id, so the
        #    low-priv holder can DERIVE the target id from their own object.
        admin_user = User.objects.get(username="admin")
        mgr_report, _ = PerformanceReport.objects.get_or_create(
            owner=admin_user,
            title="Consolidated Manager Review — FY2024",
            defaults={"body": "", "classification": "restricted"},
        )
        mgr_report.classification = "restricted"
        mgr_report.body = (
            "Aggregated leadership performance notes and compensation calibration. "
            "Distribution restricted to HR management."
        )
        mgr_report.reviewer_report_id = None
        mgr_report.save()

        standard_reports = {
            "employee1": "Performance Review — employee1",
            "jdoe": "Performance Review — jdoe",
            "mwilson": "Performance Review — mwilson",
            "hrstaff": "Performance Review — hrstaff",
        }
        for username, title in standard_reports.items():
            user = User.objects.get(username=username)
            report, _ = PerformanceReport.objects.get_or_create(
                owner=user,
                title=title,
                defaults={"body": "", "classification": "standard"},
            )
            report.classification = "standard"
            report.body = (
                "Your annual performance review. Your reviewing manager compiled the "
                "consolidated calibration summary referenced below."
            )
            report.reviewer_report_id = mgr_report.pk
            report.save()

        self.stdout.write(self.style.SUCCESS("Seeding complete"))
