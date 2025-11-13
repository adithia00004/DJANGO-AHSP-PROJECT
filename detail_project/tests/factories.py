import factory
from datetime import date
from decimal import Decimal
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "auth.User"  # Adjust if using custom user

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "pass")


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = "dashboard.Project"

    owner = factory.SubFactory(UserFactory)
    nama = factory.Sequence(lambda n: f"Project {n}")
    sumber_dana = "APBD"
    lokasi_project = "Test Location"
    nama_client = "Client Test"
    anggaran_owner = Decimal("100000000.00")
    tanggal_mulai = factory.LazyFunction(date.today)
    is_active = True
