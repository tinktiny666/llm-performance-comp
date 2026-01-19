"""
Minimal package init for backend to allow tests and imports. Exposes the Flask `app`.
"""
from .app import app

__all__ = ['app']
