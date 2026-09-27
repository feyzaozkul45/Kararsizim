from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

VALID_PASSWORD = "Sifre-12345-xyz"


class RegisterTests(TestCase):
    def register(self, **overrides):
        data = {
            "username": "ayse",
            "email": "Ayse@Example.com",
            "password1": VALID_PASSWORD,
            "password2": VALID_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("register"), data)

    def test_register_logs_user_in_and_lowercases_email(self):
        response = self.register()
        self.assertRedirects(response, reverse("poll_list"))
        user = User.objects.get(username="ayse")
        self.assertEqual(user.email, "ayse@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_is_rejected(self):
        self.register()
        self.client.post(reverse("logout"))
        response = self.register(username="baska", email="AYSE@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu e-posta adresiyle zaten bir hesap var.")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_is_rejected_case_insensitively(self):
        self.register()
        self.client.post(reverse("logout"))
        response = self.register(username="AYSE", email="baska@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_username_is_rejected(self):
        response = self.register(username="a b")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_password_mismatch_is_rejected(self):
        response = self.register(password2="baska-sifre-999")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_redirected_away(self):
        self.register()
        for name in ("register", "login"):
            self.assertRedirects(self.client.get(reverse(name)), reverse("poll_list"))


class LoginTests(TestCase):
    def setUp(self):
        User.objects.create_user("mehmet", "mehmet@example.com", VALID_PASSWORD)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"), {"username": "Mehmet@example.com", "password": VALID_PASSWORD}
        )
        self.assertRedirects(response, reverse("poll_list"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_username(self):
        response = self.client.post(
            reverse("login"), {"username": "mehmet", "password": VALID_PASSWORD}
        )
        self.assertRedirects(response, reverse("poll_list"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            reverse("login"), {"username": "mehmet", "password": "yanlis"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.client.login(username="mehmet", password=VALID_PASSWORD)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_full_flow_register_logout_email_login_logout_username_login(self):
        register = self.client.post(
            reverse("register"),
            {
                "username": "zeynep",
                "email": "zeynep@example.com",
                "password1": VALID_PASSWORD,
                "password2": VALID_PASSWORD,
            },
        )
        self.assertRedirects(register, reverse("poll_list"))
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

        self.client.post(
            reverse("login"), {"username": "zeynep@example.com", "password": VALID_PASSWORD}
        )
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("logout"))

        self.client.post(reverse("login"), {"username": "zeynep", "password": VALID_PASSWORD})
        self.assertIn("_auth_user_id", self.client.session)


class AccessibilityTests(TestCase):
    """Basic checks that assistive-tech wiring stays in place."""

    def test_register_fields_are_described_for_screen_readers(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, 'aria-describedby="id_username_help"')
        self.assertContains(response, 'id="id_username_help"')
        self.assertContains(response, 'aria-describedby="id_email_help"')

    def test_login_fields_are_described_for_screen_readers(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, 'aria-describedby="id_username_help"')
        self.assertContains(response, 'aria-describedby="id_password_help"')

    def test_skip_link_is_present(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'id="main-content"')
