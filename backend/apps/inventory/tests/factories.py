import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from apps.inventory.models import Product, Stock, UnitType

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    unit_type = UnitType.COUNT
    description = ""


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock

    owner = factory.LazyAttribute(lambda o: o.product.owner)
    product = factory.SubFactory(ProductFactory)
    identifier = factory.Sequence(lambda n: f"LOT-{n:04d}")
    quantity = factory.Faker("pydecimal", left_digits=4, right_digits=3, positive=True, min_value=1, max_value=1000)
