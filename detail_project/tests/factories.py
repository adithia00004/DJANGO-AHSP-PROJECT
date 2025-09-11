import factory
from factory.django import DjangoModelFactory

class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = "dashboard.Project"
    owner = factory.SubFactory("detail_project.tests.factories.UserFactory")
    nama = factory.Sequence(lambda n: f"Project {n}")

class UserFactory(DjangoModelFactory):
    class Meta:
        model = "auth.User"  # ganti jika pakai custom user
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "pass")
