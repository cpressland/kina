"""Functions to manage Azure Kubernetes Service."""

from time import sleep

from azure.identity import DefaultAzureCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.network import NetworkManagementClient
from rich.progress import Progress, TaskID

from kina.azure.helpers import get_location_availability_zones


def get_latest_aks_version(credential: DefaultAzureCredential, subscription_id: str, location: str) -> str:
    """Get the available Kubernetes versions for AKS clusters.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        location (str): Azure region to check for available Kubernetes versions.

    Returns:
        list[str]: List of available Kubernetes versions.

    """
    aks_client = ContainerServiceClient(credential, subscription_id)
    versions = aks_client.managed_clusters.list_kubernetes_versions(location)
    return max(
        (patch for v in versions.values for patch in v.patch_versions),
        key=lambda ver: tuple(map(int, ver.split("."))),
    )


def create_aks_clusters(
    credential: DefaultAzureCredential,
    subscription_id: str,
    virtual_network_names: list[str],
    resource_group_name: str,
    no_cni: bool = False,
    rich_progress: Progress | None = None,
    rich_task: TaskID | None = None,
) -> list[str]:
    """Create Azure Kubernetes Service (AKS) clusters in the specified virtual networks.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        virtual_network_names (list[str]): List of virtual network names to create AKS clusters in.
        resource_group_name (str): Name of the resource group to create the AKS clusters in.
        no_cni (bool, optional): Flag to disable CNI. Defaults to False.
        rich_progress (Progress | None, optional): Optional Rich Progress instance for progress tracking. Defaults to None.
        rich_task (TaskID | None, optional): Optional task ID for progress tracking. Defaults to None.

    Returns:
        list[str]: List of AKS cluster names created.

    """  # noqa: E501
    aks_client = ContainerServiceClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    clusters = []

    for virtual_network_name in virtual_network_names:
        location = network_client.virtual_networks.get(resource_group_name, virtual_network_name).location
        vnet = network_client.virtual_networks.get(resource_group_name, virtual_network_name)
        subnet = network_client.subnets.get(resource_group_name, virtual_network_name, "kube_nodes")
        cluster_name = f"{resource_group_name}-{location}"
        if rich_progress and rich_task is not None:
            rich_progress.update(rich_task, description=f"Creating AKS Cluster: {cluster_name}", advance=1)
        aks_client.managed_clusters.begin_create_or_update(
            resource_group_name=resource_group_name,
            resource_name=cluster_name,
            parameters={
                "location": location,
                "dns_prefix": cluster_name,
                "identity": {"type": "SystemAssigned"},
                "nodeResourceGroup": f"{resource_group_name}-{location}-nodes",
                "kubernetesVersion": get_latest_aks_version(credential, subscription_id, location),
                "agent_pool_profiles": [
                    {
                        "name": "default",
                        "mode": "System",
                        "minCount": 2,
                        "maxCount": 6,
                        "enableAutoScaling": True,
                        "vm_size": "Standard_D2ads_v5",
                        "osSKU": "AzureLinux",
                        "vnet_subnet_id": subnet.id,
                        "osDiskSizeGB": 64,
                        "osDiskType": "Ephemeral",
                        "availabilityZones": get_location_availability_zones(credential, subscription_id, location),
                    },
                ],
                "securityProfile": {"imageCleaner": {"enabled": True, "intervalHours": 24}},
                "oidcIssuerProfile": {"enabled": True},
                "networkProfile": {
                    "networkPlugin": "none" if no_cni else "azure",
                    "networkPluginMode": None if no_cni else "overlay",
                    "networkMode": "transparent",
                    "loadBalancerSku": "standard",
                    "podCidr": vnet.tags.get("pod-network"),
                    "serviceCidr": vnet.tags.get("service-network"),
                    "dnsServiceIP": vnet.tags.get("dns-service-ip"),
                    "ipFamilies": ["IPv4"],
                },
            },
        )
        clusters.append(cluster_name)
    return clusters


def configure_network_iam(
    credential: DefaultAzureCredential,
    subscription_id: str,
    resource_group: str,
    cluster_name: str,
) -> None:
    """Configure network IAM for the AKS cluster.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        resource_group (str): Name of the resource group containing the AKS cluster.
        cluster_name (str): Name of the AKS cluster.

    Returns:
        None

    """
    auth_client = AuthorizationManagementClient(credential, subscription_id)
    aks_client = ContainerServiceClient(credential, subscription_id)
    for _ in range(30):
        try:
            cluster = aks_client.managed_clusters.get(resource_group, cluster_name)
            principal_id = cluster.as_dict()["identity"]["principal_id"]
            auth_client.role_assignments.create(
                scope=f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}",
                role_assignment_name=principal_id,
                parameters={
                    "role_definition_id": "/providers/Microsoft.Authorization/roleDefinitions/4d97b98b-1d4f-4787-a291-c67834d212e7",  # noqa: E501
                    "principal_id": principal_id,
                },
            )
            break
        except KeyError:
            sleep(20)
            continue
