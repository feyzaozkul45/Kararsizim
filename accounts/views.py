from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("poll_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
            messages.success(request, f"Hoş geldin @{user.username}! 🎉")
            return redirect("poll_list")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True
