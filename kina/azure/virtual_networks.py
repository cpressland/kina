"""Functions to manage Azure Virtual Networks."""

from ipaddress import IPv4Network, ip_network

from azure.mgmt.network.models._models_py3 import VirtualNetwork
from rich.progress import Progress, TaskID

from kina.azure import client_network, subscription_id

_base_cidr = ip_network("10.0.0.0/16")


def generate_cidrs() -> tuple[IPv4Network, IPv4Network, IPv4Network]:
    """Generate CIDR blocks for virtual network, pod network, and service network.

    Returns:
        tuple[IPv4Network, IPv4Network, IPv4Network]: A tuple containing the virtual network, pod network, and service network CIDR blocks.

    """  # noqa: E501
    global _base_cidr  # noqa: PLW0603
    vnet_network = _base_cidr
    pod_network = ip_network((vnet_network.network_address + vnet_network.num_addresses, vnet_network.prefixlen))
    service_network = ip_network((pod_network.network_address + pod_network.num_addresses, pod_network.prefixlen))
    _base_cidr = ip_network(
        (service_network.network_address + service_network.num_addresses, service_network.prefixlen),
    )
    return vnet_network, pod_network, service_network


def create_vnet(
    resource_group_name: str,
    region: str,
    vnet_cidr: IPv4Network,
    pod_cidr: IPv4Network,
    svc_cidr: IPv4Network,
) -> VirtualNetwork:
    """Create a virtual network in the specified region.

    Args:
        resource_group_name (str): Name of the resource group to create the virtual network in.
        region (str): Azure region to create the virtual network in.
        vnet_cidr (IPv4Network): CIDR block for the virtual network.
        pod_cidr (IPv4Network): CIDR block for the pod network.
        svc_cidr (IPv4Network): CIDR block for the service network.

    Returns:
        VirtualNetwork: The created virtual network object.

    """
    return client_network.virtual_networks.begin_create_or_update(
        resource_group_name=resource_group_name,
        virtual_network_name=f"{resource_group_name}-{region}",
        parameters={
            "location": region,
            "tags": {
                "pod-network": str(pod_cidr),
                "service-network": str(svc_cidr),
                "dns-service-ip": str(svc_cidr.network_address + 10),
            },
            "address_space": {"address_prefixes": [vnet_cidr]},
        },
    ).result()


def peer_vnets(
    resource_group_name: str,
    vnets: list[str],
) -> None:
    """Peer multiple virtual networks together.

    Args:
        resource_group_name (str): Name of the resource group containing the virtual networks.
        vnets (list[str]): List of virtual network names to be peered.

    """
    for i in range(len(vnets)):
        peers = vnets[:i] + vnets[i + 1 :]
        for peer in peers:
            client_network.virtual_network_peerings.begin_create_or_update(
                resource_group_name=resource_group_name,
                virtual_network_name=vnets[i],
                virtual_network_peering_name=f"{vnets[i].split('-')[-1]}-to-{peer.split('-')[-1]}",
                virtual_network_peering_parameters={
                    "allow_virtual_network_access": True,
                    "allow_forwarded_traffic": True,
                    "allow_gateway_transit": False,
                    "use_remote_gateways": False,
                    "remote_virtual_network": {
                        "id": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/virtualNetworks/{peer}",  # noqa: E501
                    },
                },
            ).result()


def create_subnet(
    resource_group_name: str,
    vnet_name: str,
    subnet_name: str,
    cidr: str,
) -> None:
    """Create a subnet in the specified virtual network.

    Args:
        resource_group_name (str): Name of the resource group containing the virtual network.
        vnet_name (str): Name of the virtual network to create the subnet in.
        subnet_name (str): Name of the subnet to create.
        cidr (str): CIDR block for the subnet.

    Returns:
        None

    """
    client_network.subnets.begin_create_or_update(
        resource_group_name=resource_group_name,
        virtual_network_name=vnet_name,
        subnet_name=subnet_name,
        subnet_parameters={"address_prefix": cidr},
    ).result()


def create_virtual_networks(
    locations: list[str],
    resource_group_name: str,
    rich_progress: Progress | None = None,
    rich_task: TaskID | None = None,
) -> list[str]:
    """Create virtual networks in the specified locations.

    Args:
        locations (list[str]): List of Azure locations to create virtual networks in.
        resource_group_name (str): Name of the resource group to create the virtual networks in.
        rich_progress (Progress | None, optional): Optional Rich Progress instance for progress tracking. Defaults to None.
        rich_task (TaskID | None, optional): Optional task ID for progress tracking. Defaults to None.

    Returns:
        list[str]: List of virtual network names created.

    """  # noqa: E501
    networks = []
    for location in locations:
        if rich_progress and rich_task is not None:
            rich_progress.update(
                rich_task,
                description=f"Creating Virtual Network: {resource_group_name}-{location}",
                advance=1,
            )
        virual_network_cidr, pod_network_cidr, service_network_cidr = generate_cidrs()
        vnet = create_vnet(
            resource_group_name,
            location,
            virual_network_cidr,
            pod_network_cidr,
            service_network_cidr,
        )
        networks.append(vnet.name)
        subnets = [str(network) for network in ip_network(virual_network_cidr).subnets(new_prefix=24)]
        create_subnet(resource_group_name, vnet.name, "kube_nodes", subnets[0])
    if len(networks) > 1:
        peer_vnets(resource_group_name, networks)
    return networks
