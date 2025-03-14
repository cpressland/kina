import random
import string

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient


def create_resource_group(credential: DefaultAzureCredential, subscription_id: str, location: str) -> str:
    resource_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    resource_group_name = f"kina-{resource_suffix}"
    resource_client = ResourceManagementClient(credential, subscription_id)
    resource_client.resource_groups.create_or_update(resource_group_name, {"location": location})
    return resource_group_name
