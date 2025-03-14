import json
import random
import string
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient


def get_username() -> str:
    return json.loads(Path("~/.azure/azureProfile.json").expanduser().read_text())["subscriptions"][0]["user"]["name"]


def create_resource_group(credential: DefaultAzureCredential, subscription_id: str, location: str) -> str:
    resource_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    resource_group_name = f"kina-{resource_suffix}"
    client = ResourceManagementClient(credential, subscription_id)
    client.resource_groups.create_or_update(
        resource_group_name,
        {"location": location, "tags": {"managed-by": "kina", "created-by": get_username()}},
    )
    return resource_group_name


def list_resource_groups(credential: DefaultAzureCredential, subscription_id: str) -> list[tuple[str, str, str]]:
    client = ResourceManagementClient(credential, subscription_id)
    kina_instances = []
    for rg in client.resource_groups.list():
        if rg.tags is not None and rg.tags.get("managed-by") == "kina":
            kina_instances.append((rg.name, rg.location, rg.tags.get("created-by")))
    return kina_instances


def delete_resource_group(credential: DefaultAzureCredential, subscription_id: str, resource_group_name: str) -> None:
    if not resource_group_name.startswith("kina-"):
        raise ValueError("Only resource groups created by kina can be deleted.")
    client = ResourceManagementClient(credential, subscription_id)
    client.resource_groups.begin_delete(resource_group_name)
    return None
