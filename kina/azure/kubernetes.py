"""Functions to manage Azure Kubernetes Service."""

from time import sleep
from uuid import uuid4

from azure.core.exceptions import HttpResponseError
from rich.progress import Progress, TaskID

from kina.azure import (
    client_authorization,
    client_container,
    client_network,
    get_location_availability_zones,
    subscription_id,
)


def get_latest_aks_version(location: str) -> str:
    """Get the available Kubernetes versions for AKS clusters.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        location (str): Azure region to check for available Kubernetes versions.

    Returns:
        list[str]: List of available Kubernetes versions.

    """
    versions = client_container.managed_clusters.list_kubernetes_versions(location)
    return max(
        (patch for v in versions.values for patch in v.patch_versions),
        key=lambda ver: tuple(map(int, ver.split("."))),
    )


def create_aks_clusters(
    virtual_network_names: list[str],
    resource_group_name: str,
    rich_progress: Progress | None = None,
    rich_task: TaskID | None = None,
) -> list[str]:
    """Create Azure Kubernetes Service (AKS) clusters in the specified virtual networks.

    Args:
        virtual_network_names (list[str]): List of virtual network names to create AKS clusters in.
        resource_group_name (str): Name of the resource group to create the AKS clusters in.
        rich_progress (Progress | None, optional): Optional Rich Progress instance for progress tracking. Defaults to None.
        rich_task (TaskID | None, optional): Optional task ID for progress tracking. Defaults to None.

    Returns:
        list[str]: List of AKS cluster names created.

    """  # noqa: E501
    clusters = []

    for virtual_network_name in virtual_network_names:
        location = client_network.virtual_networks.get(resource_group_name, virtual_network_name).location
        vnet = client_network.virtual_networks.get(resource_group_name, virtual_network_name)
        subnet = client_network.subnets.get(resource_group_name, virtual_network_name, "kube_nodes")
        cluster_name = f"{resource_group_name}-{location}"
        if rich_progress and rich_task is not None:
            rich_progress.update(rich_task, description=f"Creating AKS Cluster: {cluster_name}", advance=1)
        client_container.managed_clusters.begin_create_or_update(
            resource_group_name=resource_group_name,
            resource_name=cluster_name,
            parameters={
                "location": location,
                "dns_prefix": cluster_name,
                "identity": {"type": "SystemAssigned"},
                "nodeResourceGroup": f"{resource_group_name}-{location}-nodes",
                "kubernetesVersion": get_latest_aks_version(location),
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
                        "availabilityZones": get_location_availability_zones(location),
                    },
                ],
                "securityProfile": {"imageCleaner": {"enabled": True, "intervalHours": 24}},
                "oidcIssuerProfile": {"enabled": True},
                "networkProfile": {
                    "networkPlugin": "azure",
                    "networkPluginMode": "overlay",
                    "networkDataplane": "cilium",
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


def configure_cluster_iam(
    resource_group: str,
    cluster_name: str,
) -> None:
    """Configure network IAM for the AKS cluster.

    Args:
        resource_group (str): Name of the resource group containing the AKS cluster.
        cluster_name (str): Name of the AKS cluster.

    Returns:
        None

    """
    role_ids = {
        "AcrPull": "7f951dda-4ed3-4680-a7ca-43fe172d538d",
        "NetworkContributor": "4d97b98b-1d4f-4787-a291-c67834d212e7",
    }
    for _ in range(30):
        try:
            cluster = client_container.managed_clusters.get(resource_group, cluster_name)
            principal_id = cluster.as_dict()["identity"]["principal_id"]
            kubelet_identity = cluster.as_dict()["identity_profile"]["kubeletidentity"]["object_id"]
            break
        except (KeyError, HttpResponseError):
            sleep(20)
            continue

    for role_id in role_ids.values():
        for identity in [principal_id, kubelet_identity]:
            for _ in range(30):
                try:
                    client_authorization.role_assignments.create(
                        scope=f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}",
                        role_assignment_name=str(uuid4()),
                        parameters={
                            "role_definition_id": f"/providers/Microsoft.Authorization/roleDefinitions/{role_id}",
                            "principal_id": identity,
                        },
                    )
                    break
                except HttpResponseError:
                    sleep(20)
                    continue


def run_aks_command(
    resource_group_name: str,
    cluster_name: str,
    command: str,
) -> None:
    """Run a command on the AKS cluster.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        resource_group_name (str): Name of the resource group containing the AKS cluster.
        cluster_name (str): Name of the AKS cluster.
        command (str): Command to run on the AKS cluster.

    Returns:
        None

    """
    client_container.managed_clusters.begin_run_command(
        resource_group_name=resource_group_name,
        resource_name=cluster_name,
        request_payload={"command": command},
    ).result()
