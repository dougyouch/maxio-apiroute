"""Every API in apis.yaml is fetched, generated and importable, and every route compiles."""

import importlib
from pathlib import Path

import pytest
import yaml
from apiroute.lazy_attribute import LazyAttribute
from apiroute.route_method import RouteMethod

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "apis.yaml").read_text())
APIS = CONFIG["apis"]


def test_names_and_modules_are_unique():
    assert len({api["name"] for api in APIS}) == len(APIS)
    assert len({api["module"] for api in APIS}) == len(APIS)


@pytest.mark.parametrize("api", APIS, ids=lambda api: api["name"])
def test_each_api(api):
    assert (ROOT / "specs" / f"{api['name']}.json").is_file()
    assert api["docs"].startswith("https://developers.maxio.com/")
    if api.get("pagination"):
        assert (ROOT / api["pagination"]).is_file()
    module = importlib.import_module(f"{CONFIG['package']}.{api['module']}")
    client = getattr(module, api["client"])
    base_module, base_name = api["base_class"].split(":")
    assert issubclass(client, getattr(importlib.import_module(base_module), base_name))
    assert client._config.base_url.startswith("https://")
    assert _compile_routes(client) > 0


@pytest.mark.parametrize("api", APIS, ids=lambda api: api["name"])
def test_every_model_builds(api):
    """Each typed model is a complete pydantic class: a forward reference left unresolved
    (which only some Python versions would show) fails here, not in a user's call."""
    models = importlib.import_module(f"{CONFIG['package']}.{api['module']}.models.models")
    classes = [getattr(models, name) for name in models.__all__]
    built = [
        model.model_rebuild(force=True) for model in classes if hasattr(model, "model_rebuild")
    ]
    assert built and all(built)


def _compile_routes(router_class: type) -> int:
    """Compiles every route of a client and its sections; returns how many there were."""
    count = 0
    for name, value in vars(router_class).items():
        if isinstance(value, RouteMethod):
            assert value.definition.name == name
            count += 1
        elif isinstance(value, LazyAttribute) and name != "models":
            count += _compile_routes(value.load())
    return count
