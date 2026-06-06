import datetime
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.inventory.tests.factories import ProductFactory, StockFactory, UserFactory
from apps.orders.models import OrderStatus, PurchaseOrder, SalesOrder


class PurchaseOrderFactory(DjangoModelFactory):
    class Meta:
        model = PurchaseOrder

    organization = factory.LazyAttribute(lambda o: o.product.organization)
    product = factory.SubFactory(ProductFactory)
    quantity = Decimal("100.000")
    cost_per_unit = Decimal("1.0000")
    status = OrderStatus.DRAFT
    order_date = factory.LazyFunction(datetime.date.today)


class SalesOrderFactory(DjangoModelFactory):
    class Meta:
        model = SalesOrder

    organization = factory.LazyAttribute(lambda o: o.product.organization)
    product = factory.SubFactory(ProductFactory)
    stock = factory.SubFactory(
        StockFactory,
        product=factory.SelfAttribute("..product"),
        organization=factory.SelfAttribute("..organization"),
    )
    quantity = Decimal("10.000")
    price_per_unit = Decimal("10.0000")
    status = OrderStatus.DRAFT
    order_date = factory.LazyFunction(datetime.date.today)
