"""
DevMind Core package.
Core utilities and dependency injection.
"""

from devmind.core.container import DIContainer, initialize_container, get_container

__all__ = ["DIContainer", "initialize_container", "get_container"]
