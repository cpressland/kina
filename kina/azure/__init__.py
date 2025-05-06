"""Module for Azure-related functionality."""

import json
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient


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


subscription_id = get_default_subscription_id()
username = get_subscription_username(subscription_id)
credential = DefaultAzureCredential()
client_authorization = AuthorizationManagementClient(credential, subscription_id)
client_registry = ContainerRegistryManagementClient(credential, subscription_id)
client_container = ContainerServiceClient(credential, subscription_id)
client_subscription = SubscriptionClient(credential)
client_network = NetworkManagementClient(credential, subscription_id)
client_resource = ResourceManagementClient(credential, subscription_id)


def get_location_availability_zones(location: str) -> list[str]:
    """Get the availability zones for a given Azure location.

    Args:
        location (str): Azure region to check for availability zones.

    Returns:
        list[str]: List of availability zones in the specified location.

    """
    loc = next(
        (loc for loc in client_subscription.subscriptions.list_locations(subscription_id) if loc.name == location),
        None,
    )
    return [zone.logical_zone for zone in (loc.availability_zone_mappings or [])]
