from .remoteok import RemoteOKAdapter
from .wwr import WWRAdapter
from .naukri import NaukriAdapter
from .linkedin import LinkedInAdapter
from .internshala import InternshalaAdapter
from .base import BaseAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "remoteok": RemoteOKAdapter,
    "weworkremotely": WWRAdapter,
    "naukri": NaukriAdapter,
    "linkedin": LinkedInAdapter,
    "internshala": InternshalaAdapter,
}


def get_adapter(source_name: str) -> BaseAdapter:
    cls = ADAPTER_REGISTRY.get(source_name)
    if not cls:
        raise ValueError(f"No adapter registered for: {source_name}")
    return cls()
