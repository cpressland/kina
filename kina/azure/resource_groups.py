"""Functions to manage Azure Resource Groups."""

import secrets
import string

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

from kina.azure.helpers import get_subscription_username


def create_resource_group(
    credential: DefaultAzureCredential,
    subscription_id: str,
    locations: list[str],
) -> str:
    """Create a new Azure resource group for Kina Clusters.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        locations (list[str]): List of Azure locations to create Kubernetes Clusters in.

    Returns:
        str: Name of the created resource group.

    """
    resource_suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    resource_group_name = f"kina-{resource_suffix}"
    client = ResourceManagementClient(credential, subscription_id)
    client.resource_groups.create_or_update(
        resource_group_name,
        {
            "location": locations[0],
            "tags": {
                "managed-by": "kina",
                "locations": ",".join(locations),
                "created-by": get_subscription_username(subscription_id),
            },
        },
    )
    return resource_group_name


def list_resource_groups(
    credential: DefaultAzureCredential,
    subscription_id: str,
) -> list[tuple[str, str, str]]:
    """List all Azure resource groups created by Kina.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.

    Returns:
        list[tuple[str, str, str, str]]: List of tuples containing resource group name, location, creator, and multicluster.

    """  # noqa: E501
    client = ResourceManagementClient(credential, subscription_id)
    return [
        (rg.name, rg.tags.get("locations"), rg.tags.get("created-by"))
        for rg in client.resource_groups.list()
        if rg.tags is not None and rg.tags.get("managed-by") == "kina"
    ]


def delete_resource_group(credential: DefaultAzureCredential, subscription_id: str, resource_group_name: str) -> bool:
    """Delete an Azure resource group created by Kina.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        resource_group_name (str): Name of the resource group to delete.

    Returns:
        bool: True if the resource group was deleted, False otherwise.

    """
    # TODO(@cpressland): Improve validation of Kina Resource Groups.
    # https://github.com/cpressland/kina/issues/3
    deleted = False
    if resource_group_name.startswith("kina-"):
        client = ResourceManagementClient(credential, subscription_id)
        client.resource_groups.begin_delete(resource_group_name)
        deleted = True
    return deleted
