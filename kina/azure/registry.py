"""Azure Container Registry (ACR) functions."""

from azure.mgmt.containerregistry.models import Registry, Sku

from kina.azure import client_registry


def create_acr(
    resource_group_name: str,
    location: str,
) -> str:
    """Create an Azure Container Registry (ACR) instance.

    Args:
        resource_group_name (str): Resource group name for the ACR instance.
        location (str): Azure region for the ACR instance.

    Returns:
        None

    """
    acr_name = resource_group_name.replace("-", "")
    client_registry.registries.begin_create(
        resource_group_name,
        acr_name,
        Registry(
            sku=Sku(name="Basic"),
            location=location,
            admin_user_enabled=True,
        ),
    ).result()
    return f"{acr_name}.azurecr.io"
