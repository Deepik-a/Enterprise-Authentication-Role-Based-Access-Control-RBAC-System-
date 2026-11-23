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


    code = models.SlugField(max_length=50, unique=True, null=True, blank=True)

    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    data_scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_OWN)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.code == self.SUPER_ADMIN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Super Admin role cannot be deleted.")
        return super().delete(*args, **kwargs)
