from ipaddress import ip_network

from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models._models_py3 import VirtualNetwork


def create_vnet(client: NetworkManagementClient, resource_group_name: str, region: str, cidr: str) -> VirtualNetwork:
    return client.virtual_networks.begin_create_or_update(
        resource_group_name=resource_group_name,
        virtual_network_name=f"kina-vnet-{region}",
        parameters={
            "location": region,
            "address_space": {"address_prefixes": [cidr]},
        },
    ).result()


def peer_vnet(client: NetworkManagementClient, resource_group_name: str, vnet_name: str, remote_vnet_id: str) -> None:
    client.virtual_network_peerings.begin_create_or_update(
        resource_group_name=resource_group_name,
        virtual_network_name=vnet_name,
        virtual_network_peering_name=f"{vnet_name.split('-')[-1]}-to-{remote_vnet_id.split('/')[-1].split('-')[-1]}",
        virtual_network_peering_parameters={
            "allow_virtual_network_access": True,
            "allow_forwarded_traffic": True,
            "allow_gateway_transit": False,
            "use_remote_gateways": False,
            "remote_virtual_network": {"id": remote_vnet_id},
        },
    ).result()
    return None


def create_subnet(
    client: NetworkManagementClient, resource_group_name: str, vnet_name: str, subnet_name: str, cidr: str
) -> None:
    client.subnets.begin_create_or_update(
        resource_group_name=resource_group_name,
        virtual_network_name=vnet_name,
        subnet_name=subnet_name,
        subnet_parameters={"address_prefix": cidr},
    ).result()
    return None


def create_virtual_networks(
    credential: DefaultAzureCredential,
    subscription_id: str,
    primary_region: str,
    primary_cidr: str,
    secondary_region: str,
    secondary_cidr: str,
    resource_group_name: str,
) -> tuple[str, str]:
    network_client = NetworkManagementClient(credential, subscription_id)
    primary_vnet = create_vnet(network_client, resource_group_name, primary_region, primary_cidr)
    secondary_vnet = create_vnet(network_client, resource_group_name, secondary_region, secondary_cidr)
    peer_vnet(network_client, resource_group_name, primary_vnet.name, secondary_vnet.id)
    peer_vnet(network_client, resource_group_name, secondary_vnet.name, primary_vnet.id)
    for virtual_network in [primary_vnet, secondary_vnet]:
        network_range = ip_network(virtual_network.address_space.address_prefixes[0])
        subnet_ip_map = {
            "kube_nodes": str(list(network_range.subnets(new_prefix=24))[0]),
            "kube_controller": str(list(network_range.subnets(new_prefix=24))[1]),
        }
        for subnet in subnet_ip_map:
            create_subnet(network_client, resource_group_name, virtual_network.name, subnet, subnet_ip_map[subnet])
    return primary_vnet.name, secondary_vnet.name
