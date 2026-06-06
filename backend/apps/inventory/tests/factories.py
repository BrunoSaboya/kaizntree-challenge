import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from apps.inventory.models import Product, Stock, UnitType
from apps.users.models import Organization

User = get_user_model()


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = User.ROLE_OWNER
    organization = factory.SubFactory(OrganizationFactory)

    @factory.post_generation
    def _link_org_owner(self, create, extracted, **kwargs):
        if create and self.organization and not self.organization.owner_id:
            self.organization.owner = self
            self.organization.save(update_fields=["owner"])


class AdminUserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"admin{n}@example.com")
    username = factory.Sequence(lambda n: f"admin{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = User.ROLE_ADMIN
    organization = None
    is_staff = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    unit_type = UnitType.COUNT
    description = ""


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock

    organization = factory.LazyAttribute(lambda o: o.product.organization)
    product = factory.SubFactory(ProductFactory)
    identifier = factory.Sequence(lambda n: f"LOT-{n:04d}")
    quantity = factory.Faker("pydecimal", left_digits=4, right_digits=3, positive=True, min_value=1, max_value=1000)
