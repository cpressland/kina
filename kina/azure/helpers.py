"""Helper functions for Azure CLI integration."""

import json
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient


def get_location_availability_zones(
    credential: DefaultAzureCredential,
    subscription_id: str,
    location: str,
) -> list[str]:
    """Get the availability zones for a given Azure location.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        location (str): Azure region to check for availability zones.

    Returns:
        list[str]: List of availability zones in the specified location.

    """
    client = SubscriptionClient(credential)
    loc = next((loc for loc in client.subscriptions.list_locations(subscription_id) if loc.name == location), None)
    return [zone.logical_zone for zone in (loc.availability_zone_mappings or [])]


def get_subscription_username(subscription_id: str) -> str:
    """Get the username of the Azure account associated with the given subscription ID.

    Args:
        subscription_id (str): The Azure subscription ID.

    Returns:
        str: The username associated with the subscription ID.

    """
    try:
        azure_profile = json.loads(Path("~/.azure/azureProfile.json").expanduser().read_text())
    except json.JSONDecodeError:
        azure_profile = json.loads(Path("~/.azure/azureProfile.json").expanduser().read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise FileNotFoundError("Azure profile file not found. Please log in to Azure CLI.") from None

    return next(sub for sub in azure_profile["subscriptions"] if sub["id"] == subscription_id)["user"]["name"]


def get_default_subscription_id() -> str:
    """Get the default Azure subscription ID.

    Returns:
        str: The default Azure subscription ID.

    """
    try:
        azure_profile = json.loads(Path("~/.azure/azureProfile.json").expanduser().read_text())
    except json.JSONDecodeError:
        azure_profile = json.loads(Path("~/.azure/azureProfile.json").expanduser().read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise FileNotFoundError("Azure profile file not found. Please log in to Azure CLI.") from None

    return next(sub for sub in azure_profile["subscriptions"] if sub["isDefault"])["id"]
