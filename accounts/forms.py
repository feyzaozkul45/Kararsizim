from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="E-posta",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        error_messages={"invalid": "Geçerli bir e-posta adresi gir."},
    )

    class Meta:
        model = User
        fields = ("username", "email")
        labels = {"username": "Kullanıcı adı"}
        help_texts = {"username": "3–20 karakter; harf, rakam, _ ve . kullanabilirsin."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Şifre"
        self.fields["password2"].label = "Şifre (tekrar)"
        self.fields["password2"].help_text = ""
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            # Screen readers announce this field's help text/errors alongside it.
            field.widget.attrs.setdefault("aria-describedby", f"id_{name}_help")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta adresiyle zaten bir hesap var.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="E-posta veya kullanıcı adı",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Şifre",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        "invalid_login": "E-posta/kullanıcı adı veya şifre hatalı.",
        "inactive": "Bu hesap aktif değil.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            field.widget.attrs.setdefault("aria-describedby", f"id_{name}_help")
