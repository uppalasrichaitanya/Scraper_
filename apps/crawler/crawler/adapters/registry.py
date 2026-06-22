from .remoteok import RemoteOKAdapter
from .wwr import WWRAdapter
from .naukri import NaukriAdapter
from .base import BaseAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "remoteok": RemoteOKAdapter,
    "weworkremotely": WWRAdapter,
    "naukri": NaukriAdapter,
}


def get_adapter(source_name: str) -> BaseAdapter:
    cls = ADAPTER_REGISTRY.get(source_name)
    if not cls:
        raise ValueError(f"No adapter registered for: {source_name}")
    return cls()
