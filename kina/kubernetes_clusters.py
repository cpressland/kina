from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.network import NetworkManagementClient

from kina.azure import get_location_availability_zones


def create_aks_cluster(
    credential: DefaultAzureCredential,
    subscription_id: str,
    virtual_network_names: list[str],
    resource_group_name: str,
) -> list[str]:
    aks_client = ContainerServiceClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    clusters = []

    for virtual_network_name in virtual_network_names:
        location = network_client.virtual_networks.get(resource_group_name, virtual_network_name).location
        subnet = network_client.subnets.get(resource_group_name, virtual_network_name, "kube_nodes")
        cluster_name = f"{resource_group_name}-{location}"
        aks_client.managed_clusters.begin_create_or_update(
            resource_group_name=resource_group_name,
            resource_name=cluster_name,
            parameters={
                "location": location,
                "dns_prefix": cluster_name,
                "identity": {"type": "SystemAssigned"},
                "nodeResourceGroup": f"{resource_group_name}-{location}-nodes",
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
                    }
                ],
                "networkProfile": {
                    "networkPlugin": "azure",
                    "networkPluginMode": "overlay",
                    "networkMode": "transparent",
                    "loadBalancerSku": "standard",
                    "podCidr": "172.20.0.0/14",
                    "serviceCidr": "172.16.0.0/16",
                    "dnsServiceIP": "172.16.0.10",
                    "ipFamilies": ["IPv4"],
                },
            },
        )
        clusters.append(cluster_name)
    return clusters
