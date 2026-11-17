from django.test import TestCase
from django.urls import reverse

from .models import Role, User


class AccountTests(TestCase):
    def registration_data(self, **overrides):
        data = {"name": "New user", "email": "new@example.test", "phone": "+91 98765 43210", "role": "victim", "password1": "Account-password-29!", "password2": "Account-password-29!"}
        data.update(overrides)
        return data

    def test_registration_creates_a_hashed_password_and_signed_in_beneficiary(self):
        response = self.client.post(reverse("users:register"), self.registration_data())
        self.assertRedirects(response, reverse("dashboard:home"))
        user = User.objects.get()
        self.assertEqual(user.role_name, "victim")
        self.assertTrue(user.check_password("Account-password-29!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_donor_registration_cannot_approve_or_elevate_itself(self):
        self.client.post(reverse("users:register"), self.registration_data(role="donor", support_approved=True, is_staff=True, is_superuser=True))
        user = User.objects.get()
        self.assertFalse(user.support_approved)
        self.assertFalse(user.can_support)
        self.assertFalse(user.can_coordinate)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_public_registration_rejects_staff_and_admin_roles(self):
        for role in ("ngo_staff", "admin"):
            with self.subTest(role=role):
                response = self.client.post(reverse("users:register"), self.registration_data(role=role))
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.exists())

    def test_case_insensitive_email_login_and_duplicate_registration(self):
        User.objects.create_user("Known@Example.test", "Account-password-29!", name="Known account")
        response = self.client.post(reverse("users:login"), {"username": "known@example.test", "password": "Account-password-29!"})
        self.assertRedirects(response, reverse("dashboard:home"))
        self.client.logout()
        response = self.client.post(reverse("users:register"), self.registration_data(email="KNOWN@example.test"))
        self.assertContains(response, "already uses this email")
        self.assertEqual(User.objects.count(), 1)

    def test_login_does_not_redirect_to_an_external_next_url(self):
        User.objects.create_user("known@example.test", "Account-password-29!", name="Known account")
        response = self.client.post(reverse("users:login") + "?next=https://external.example/", {"username": "known@example.test", "password": "Account-password-29!"})
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_inactive_account_cannot_authenticate_or_coordinate(self):
        role = Role.objects.create(name="ngo_staff")
        user = User.objects.create_user("inactive@example.test", "Account-password-29!", name="Inactive staff", role=role, is_active=False)
        self.assertFalse(user.can_coordinate)
        response = self.client.post(reverse("users:login"), {"username": user.email, "password": "Account-password-29!"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sign_out_requires_post(self):
        user = User.objects.create_user("known@example.test", "Account-password-29!", name="Known account")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("users:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("users:logout")), reverse("dashboard:landing"))
