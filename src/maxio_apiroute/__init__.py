"""A Python client for Maxio Advanced Billing (formerly Chargify), generated with apiroute
from Maxio's OpenAPI spec.

    from maxio_apiroute.advanced_billing import AdvancedBillingApi

    maxio = AdvancedBillingApi(api_key="...", site="acme")
    customer = maxio.customers.models.read_customer(123)

Only maxio_apiroute.auth (the hand-written MaxioAuth) and this file are written by hand;
everything under maxio_apiroute.advanced_billing is regenerated from Maxio's spec.
"""
