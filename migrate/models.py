from dataclasses import dataclass


@dataclass
class OrgInfo:
    alias: str
    username: str
    is_sandbox: bool


@dataclass
class Credentials:
    access_token: str
    instance_url: str
    alias: str
    username: str


class ProductionOrgError(Exception):
    """Raised when user selects a production org as the migration target."""


class SFCLINotFoundError(Exception):
    """Raised when the sf CLI is not installed or not on PATH."""
