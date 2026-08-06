"""Adapters that make external tools available to Boukensha."""

from .mcp import CollisionError, register, register_client

__all__ = ["CollisionError", "register", "register_client"]
