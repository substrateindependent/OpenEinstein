"""Gateway web application factory exports."""

from openeinstein.gateway.web.app import create_dashboard_app
from openeinstein.gateway.web.config import DashboardConfig, DashboardDeps

__all__ = ["DashboardConfig", "DashboardDeps", "create_dashboard_app"]
