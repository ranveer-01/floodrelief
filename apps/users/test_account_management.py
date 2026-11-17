from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.dashboard.models import Notification
from apps.requests.tests.helpers import WorkflowTestCase

from .models import Role, User


class AccountManagementTests(WorkflowTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        role = Role.objects.get(name=Role.Name.ADMIN)
        cls.admin = User.objects.create_superuser("admin@example.test", "Account-password-29!", name="Administrator", role=role)
        cls.viewer = User.objects.create_user("viewer@example.test", "Account-password-29!", name="Account viewer", role=role, is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_user", content_type__app_label="users"))
        cls.editor = User.objects.create_user("editor@example.test", "Account-password-29!", name="Account editor", role=role, is_staff=True)
        cls.editor.user_permissions.add(Permission.objects.get(codename="change_user", content_type__app_label="users"))

    def test_account_pages_require_login(self):
        self.assertEqual(self.client.get(reverse("users:manage_accounts")).status_code, 302)
        self.assertEqual(self.client.post(reverse("users:approve_donor", args=[self.pending.pk])).status_code, 302)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.support_approved)

    def test_relief_roles_and_admin_label_do_not_grant_account_permissions(self):
        label_only = User.objects.create_user("label@example.test", "Account-password-29!", name="Administrator label", role=Role.objects.get(name=Role.Name.ADMIN), is_staff=True)
        for user in (self.owner, self.donor, self.staff, label_only):
            with self.subTest(role=user.role_name):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("users:manage_accounts"), {"status": "all"}).status_code, 403)
                self.assertEqual(self.client.post(reverse("users:approve_donor", args=[self.pending.pk])).status_code, 403)
                dashboard = self.client.get(reverse("dashboard:home"))
                self.assertNotContains(dashboard, self.pending.email)
                self.assertNotIn("account_stats", dashboard.context)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.support_approved)

    def test_view_permission_allows_reading_but_cannot_approve(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("users:manage_accounts"))
        self.assertContains(response, self.pending.email)
        self.assertNotContains(response, reverse("users:approve_donor", args=[self.pending.pk]))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.post(reverse("users:approve_donor", args=[self.pending.pk])).status_code, 403)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.support_approved)

    def test_approval_preserves_identity_privileges_and_other_accounts(self):
        self.client.force_login(self.editor)
        original = {field: getattr(self.pending, field) for field in ("name", "email", "password", "role_id", "is_staff", "is_superuser")}
        response = self.client.post(reverse("users:approve_donor", args=[self.pending.pk]), {
            "q": "Pending", "role": "admin", "status": "all", "next": "https://external.example/",
            "is_staff": "true", "is_superuser": "true", "password": "Replacement-password-11!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("users:manage_accounts") + "?"))
        self.assertNotIn("external.example", response.url)
        self.pending.refresh_from_db()
        self.assertTrue(self.pending.can_support)
        self.assertEqual({field: getattr(self.pending, field) for field in original}, original)
        self.other.refresh_from_db()
        self.assertFalse(self.other.support_approved)

    def test_approval_notifies_after_commit_and_repeated_posts_are_idempotent(self):
        self.client.force_login(self.admin)
        url = reverse("users:approve_donor", args=[self.pending.pk])
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url).status_code, 302)
            self.assertFalse(Notification.objects.filter(recipient=self.pending).exists())
        self.assertEqual(Notification.objects.filter(recipient=self.pending, title="Donor support approved").count(), 1)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(Notification.objects.filter(recipient=self.pending).count(), 1)

    def test_only_active_donors_can_be_approved_and_get_never_changes_state(self):
        inactive = User.objects.create_user("inactive-donor@example.test", "Account-password-29!", name="Inactive donor", role=self.pending.role, is_active=False)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("users:approve_donor", args=[self.pending.pk])).status_code, 405)
        for target in (self.owner, self.staff, inactive):
            with self.subTest(target=target.email):
                self.assertEqual(self.client.post(reverse("users:approve_donor", args=[target.pk])).status_code, 404)
                target.refresh_from_db()
                self.assertFalse(target.support_approved)
        self.pending.refresh_from_db()
        self.assertFalse(self.pending.support_approved)

    def test_account_filters_and_summary_exclude_inactive_pending_donors(self):
        User.objects.create_user("inactive-donor@example.test", "Account-password-29!", name="Inactive donor", role=self.pending.role, is_active=False)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:manage_accounts"))
        self.assertEqual(response.context["account_stats"]["pending_donors"], 1)
        self.assertEqual(list(response.context["page_obj"]), [self.pending])
        response = self.client.get(reverse("users:manage_accounts"), {"status": "all", "role": "donor", "q": "Approved"})
        self.assertEqual(list(response.context["page_obj"]), [self.donor])
        self.assertNotContains(response, self.pending.email)

    def test_account_pagination_retains_filters(self):
        for index in range(21):
            User.objects.create_user(f"queue-{index:02d}@example.test", None, name=f"Queue donor {index:02d}", role=self.pending.role)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:manage_accounts"), {"status": "pending", "q": "Queue", "page": "2"})
        self.assertEqual(response.context["page_obj"].paginator.count, 21)
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, "q=Queue")

    def test_approval_enforces_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        url = reverse("users:approve_donor", args=[self.pending.pk])
        self.assertEqual(client.post(url).status_code, 403)
        self.assertEqual(client.get(reverse("users:manage_accounts")).status_code, 200)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(url, HTTP_X_CSRFTOKEN=token).status_code, 302)
