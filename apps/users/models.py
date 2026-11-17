"""
Users and roles.

Maps directly onto the class diagram in the proposal:

    Role: id (uuid), name
    User: id (uuid), name, email, passwordHash, createdAt, role (FK -> Role)

`passwordHash` is Django's inherited `password` field (PBKDF2 hash), so we get
hashing, validation and the admin's password tooling for free.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.Model):
    """One of the four actors in the platform."""

    class Name(models.TextChoices):
        VICTIM = "victim", "Victim"
        DONOR = "donor", "Donor"
        NGO_STAFF = "ngo_staff", "NGO staff"
        ADMIN = "admin", "Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32, choices=Name.choices, unique=True)
    description = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class UserManager(BaseUserManager):
    """Email-based manager — this project has no `username` field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        extra_fields.setdefault("name", email.split("@")[0])
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("full name", max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Can sign in to the Django admin / coordination desk.",
    )
    support_approved = models.BooleanField(
        default=False,
        help_text="Allows a donor to browse verified requests and offer support. Set by an administrator.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split(" ")[0] if self.name else self.email

    @property
    def role_name(self):
        return self.role.name if self.role else ""

    def has_role(self, *names):
        return self.role_name in names

    @property
    def workspace_role(self):
        return Role.Name.ADMIN if self.is_superuser else self.role_name or Role.Name.VICTIM

    @property
    def workspace_role_label(self):
        if self.workspace_role == Role.Name.VICTIM:
            return "Beneficiary"
        return dict(Role.Name.choices).get(self.workspace_role, "Your account")

    @property
    def can_view_accounts(self):
        return self.is_active and self.is_staff and (
            self.has_perm("users.view_user") or self.has_perm("users.change_user")
        )

    @property
    def can_approve_donors(self):
        return self.is_active and self.is_staff and self.has_perm("users.change_user")

    @property
    def can_coordinate(self):
        return self.is_active and (
            self.is_superuser or self.has_role(Role.Name.NGO_STAFF, Role.Name.ADMIN)
        )

    @property
    def can_support(self):
        return self.can_coordinate or (
            self.is_active and self.has_role(Role.Name.DONOR) and self.support_approved
        )
