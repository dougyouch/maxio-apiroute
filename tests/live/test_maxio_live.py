"""The client against a Maxio test site: JSON bodies, typed models validating real responses,
paging past the first page, async and errors."""

import asyncio
import uuid

import pytest
from apiroute import UnexpectedResponse


@pytest.fixture
def customer(maxio):
    reference = f"apiroute-{uuid.uuid4().hex[:12]}"
    created = maxio.customers.models.create_customer(
        body={
            "customer": {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": f"{reference}@example.com",
                "reference": reference,
            }
        }
    ).customer
    yield created
    maxio.customers.delete_customer(created.id)


def test_the_site_is_typed(maxio):
    site = maxio.sites.models.read_site().site
    assert site.test is True and site.subdomain


def test_create_read_and_update(maxio, customer):
    found = maxio.customers.models.read_customer_by_reference(reference=customer.reference)
    assert found.customer.id == customer.id
    updated = maxio.customers.models.update_customer(
        customer.id, body={"customer": {"organization": "Analytical Engines"}}
    )
    assert updated.customer.organization == "Analytical Engines"


def test_list_all_pages_past_the_first_page(maxio):
    run = uuid.uuid4().hex[:12]
    created = [
        maxio.customers.create_customer(
            body={
                "customer": {
                    "first_name": "Page",
                    "last_name": str(n),
                    "email": f"paging-{run}-{n}@example.com",
                }
            }
        )["customer"]["id"]
        for n in range(3)
    ]
    try:
        found = list(maxio.customers.models.list_customers_all(q=f"paging-{run}", per_page=1))
        assert sorted(item.customer.id for item in found) == sorted(created)  # three pages
    finally:
        for customer_id in created:
            maxio.customers.delete_customer(customer_id)


def test_reads_across_sections(maxio):
    assert isinstance(maxio.products.list_products(per_page=1), list)
    assert isinstance(maxio.subscriptions.list_subscriptions(per_page=1), list)
    assert "invoices" in maxio.invoices.list_invoices(per_page=1)


def test_async(maxio, customer):
    found = asyncio.run(maxio.customers.models.aio.read_customer(customer.id))
    assert found.customer.id == customer.id


def test_an_error_is_an_unexpected_response(maxio):
    with pytest.raises(UnexpectedResponse) as raised:
        maxio.customers.read_customer(2_000_000_000)
    assert raised.value.response.status_code == 404
