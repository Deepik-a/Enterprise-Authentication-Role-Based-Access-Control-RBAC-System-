from django.db import models
from django.utils.text import slugify


class Module(models.Model):
    """A functional area of the system (Users, Orders, Reports...).

    `slug` is the prefix of every permission codename in the module
    (e.g. slug `orders` -> `orders_view`). `route` is the frontend path the
    sidebar links to, so the menu is driven by data, not hardcoded.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    route = models.CharField(max_length=100, blank=True, default="")
    order = models.PositiveIntegerField(default=100)
    # System modules are created by seed_data and cannot be deleted through the API.
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name).replace("-", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Permission(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="permissions")
    action = models.CharField(max_length=50)
    codename = models.CharField(max_length=100, unique=True)

    class Meta:
        unique_together = ("module", "action")

    def __str__(self):
        return f"{self.module.name} - {self.action}"


class Role(models.Model):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    CUSTOMER = "customer"

    # Data scope decides *which records* a role can see once it has the
    # permission to see a kind of record at all (object-level scoping).
    SCOPE_ALL = "all"
    SCOPE_TEAM = "team"
    SCOPE_OWN = "own"
    SCOPE_CHOICES = [
        (SCOPE_ALL, "All records"),
        (SCOPE_TEAM, "Own and team records"),
        (SCOPE_OWN, "Own records only"),
    ]
    SCOPE_RANK = {SCOPE_OWN: 0, SCOPE_TEAM: 1, SCOPE_ALL: 2}

    name = models.CharField(max_length=100, unique=True)
    # Stable identifier for built-in roles. Never derived from `name`, so
    # renaming a role can't change who is treated as Super Admin.
    code = models.SlugField(max_length=50, unique=True, null=True, blank=True)
    # System roles are seeded and cannot be edited or deleted through the API.
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    data_scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_OWN)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    def __str__(self):
        return self.name
