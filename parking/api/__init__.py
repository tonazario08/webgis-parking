"""
API package for Parking Management System

This module intentionally avoids heavy imports at package import time. Import
`parking.utils.gis` functions inside views when needed to prevent startup
errors during management commands.
"""

__all__ = []
