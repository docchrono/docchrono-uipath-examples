"""Versioned JSON bridge between UiPath workflows and DocChrono."""

from docchrono_uipath_bridge.bridge import execute
from docchrono_uipath_bridge.contracts import BRIDGE_SCHEMA_VERSION, BridgeError, Request

__all__ = ["BRIDGE_SCHEMA_VERSION", "BridgeError", "Request", "execute"]

__version__ = "0.1.0"
