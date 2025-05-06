"""Functions to manage Azure Resource Groups."""

import secrets
import string
from datetime import UTC, datetime

from kina.azure import client_resource, username


def create_resource_group(locations: list[str]) -> str:
    """Create a new Azure resource group for Kina Clusters.

    Args:
        locations (list[str]): List of Azure locations to create Kubernetes Clusters in.

    Returns:
        str: Name of the created resource group.

    """
    resource_suffix = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    resource_group_name = f"kina-{resource_suffix}"
    client_resource.resource_groups.create_or_update(
        resource_group_name,
        {
            "location": locations[0],
            "tags": {
                "managed-by": "kina",
                "locations": ",".join(locations),
                "created-by": username,
                "created-at": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Creating",
            },
        },
    )
    return resource_group_name


def update_resource_group_status(
    resource_group_name: str,
    status: str,
) -> None:
    """Update the status tag of an Azure resource group created by Kina.

    Args:
        resource_group_name (str): Name of the resource group to update.
        status (str): Status to set for the resource group.

    Returns:
        None

    """
    resource_group = client_resource.resource_groups.get(resource_group_name)
    tags = resource_group.tags
    tags.update({"status": status})
    client_resource.resource_groups.update(
        resource_group_name,
        {
            "location": resource_group.location,
            "tags": tags,
        },
    )


def list_resource_groups() -> list[tuple[str, str, str, str, str]]:
    """List all Azure resource groups created by Kina.

    Returns:
        list[tuple[str, str, str, str, str]]: List of tuples containing resource group name, location, creator, and multicluster.

    """  # noqa: E501
    return [
        (rg.name, rg.tags.get("locations"), rg.tags.get("created-by"), rg.tags.get("created-at"), rg.tags.get("status"))
        for rg in client_resource.resource_groups.list()
        if rg.tags is not None and rg.tags.get("managed-by") == "kina"
    ]


def delete_resource_group(resource_group_name: str) -> bool:
    """Delete an Azure resource group created by Kina.

    Args:
        resource_group_name (str): Name of the resource group to delete.

    Returns:
        bool: True if the resource group was deleted, False otherwise.

    """
    # TODO(@cpressland): Improve validation of Kina Resource Groups.
    # https://github.com/cpressland/kina/issues/3
    deleted = False
    if resource_group_name.startswith("kina-"):
        client_resource.resource_groups.begin_delete(resource_group_name)
        deleted = True
    return deleted
