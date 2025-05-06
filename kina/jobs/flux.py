"""Flux Operator for Kubernetes."""

from kina.azure.kubernetes import run_aks_command


def install_flux_operator(
    resource_group_name: str,
    cluster_name: str,
) -> None:
    """Install the Flux Operator on the specified AKS cluster.

    Args:
        credential (DefaultAzureCredential): Azure credentials for authentication.
        subscription_id (str): Azure subscription ID.
        resource_group_name (str): Name of the resource group containing the AKS cluster.
        cluster_name (str): Name of the AKS cluster to install the Flux Operator on.

    Returns:
        None

    """
    run_aks_command(
        resource_group_name,
        cluster_name,
        "helm install flux-operator oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator --namespace flux-system --create-namespace",  # noqa: E501
    )
