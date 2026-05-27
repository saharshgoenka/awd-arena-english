import os

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Employee, Flag


def health(request):
    return JsonResponse({"status": "ok"})


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        # VULNERABLE: separate lookup reveals whether username exists (flag_5 enumeration)
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return render(request, "hr/login.html", {"error": "User not found"})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect("/dashboard/")
        error = "Invalid password"
    return render(request, "hr/login.html", {"error": error})


def logout_view(request):
    auth_logout(request)
    return redirect("/login/")


@login_required
def dashboard(request):
    employees = Employee.objects.select_related("user").all()[:5]
    return render(request, "hr/dashboard.html", {"employees": employees})


# ── flag_1: A01 Broken Access Control ─────────────────────────────────────────
# @login_required present but @permission_required is intentionally missing.

@login_required
# @permission_required('hr.view_reports', raise_exception=True)  # intentionally omitted
def staff_reports(request):
    flag = Flag.objects.get(name="flag_1")
    reports = [
        {"title": "Q1 Headcount Summary",       "department": "Engineering"},
        {"title": "Attrition Report FY2024",     "department": "All"},
        {"title": "Compensation Benchmarking",   "department": "Finance"},
        {"title": "Diversity & Inclusion KPIs",  "department": "HR"},
        {"title": "Termination Summary Q4",      "department": "Legal"},
    ]
    return render(request, "hr/staff_reports.html", {"flag": flag.value, "reports": reports})


# ── flag_2: A02 Security Misconfiguration ─────────────────────────────────────
# Debug endpoint dumps settings + os.environ; FLAG_2 is in environ. No auth.

def debug_info(request):
    import django.conf
    data = {
        "settings": {
            k: str(v)
            for k, v in vars(django.conf.settings).items()
            if not k.startswith("_")
        },
        "environ": dict(os.environ),
    }
    return JsonResponse(data)


# ── flag_3: A04 Cryptographic Failures ────────────────────────────────────────
# Employee detail shows user.password (raw MD5 hex via UnsaltedMD5PasswordHasher).

@login_required
def employee_list(request):
    employees = Employee.objects.select_related("user").order_by("employee_id")
    return render(request, "hr/employee_list.html", {"employees": employees})


@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    return render(request, "hr/employee_detail.html", {"employee": employee})


@login_required
def profile_secret(request):
    if request.user.username != "employee1":
        return HttpResponse("Forbidden — employee1 access only", status=403)
    flag = Flag.objects.get(name="flag_3")
    return render(request, "hr/profile_secret.html", {"flag": flag.value})


# ── flag_4: A05 Injection ─────────────────────────────────────────────────────
# .raw() with f-string — UNION-injectable; hr_flag table in same DB.

@login_required
def employee_search(request):
    q = request.GET.get("q", "")
    if q:
        results = list(Employee.objects.raw(
            f"SELECT hr_employee.id, hr_employee.user_id, hr_employee.department, "
            f"hr_employee.salary, hr_employee.employee_id, auth_user.username "
            f"FROM hr_employee "
            f"JOIN auth_user ON hr_employee.user_id = auth_user.id "
            f"WHERE auth_user.username LIKE '%{q}%'"
        ))
    else:
        results = list(Employee.objects.select_related("user").all())
    return render(request, "hr/employee_search.html", {"results": results, "q": q})


# ── flag_5: A07 Authentication Failures ───────────────────────────────────────
# /login has no rate limit; /hr/payroll/ requires is_staff (brute-force target).

@login_required
def payroll(request):
    if not request.user.is_staff:
        return HttpResponse("Forbidden", status=403)
    flag = Flag.objects.get(name="flag_5")
    employees = Employee.objects.select_related("user").all()
    return render(request, "hr/payroll.html", {"flag": flag.value, "employees": employees})
