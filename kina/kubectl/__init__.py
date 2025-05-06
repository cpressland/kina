"""Module for Kubectl-related functionality."""

from os import environ
from pathlib import Path
from time import sleep

import yaml
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from kina.azure import client_container

path = environ.get("KUBECONFIG", "~/.kube/config")
kubeconfig_path = Path(path).expanduser()


def add_cluster_to_kubeconfig(
    resource_group_name: str,
    cluster_name: str,
) -> None:
    """Add AKS cluster credentials to kubeconfig.

    Args:
        resource_group_name (str): Name of the resource group containing the AKS cluster.
        cluster_name (str): Name of the AKS cluster.
        rich_progress (Progress | None, optional): Optional Rich Progress instance for progress tracking. Defaults to None.
        rich_task (TaskID | None, optional): Optional task ID for progress tracking. Defaults to None.

    Returns:
        None

    """  # noqa: E501
    for _ in range(20):
        try:
            credentials = client_container.managed_clusters.list_cluster_admin_credentials(
                resource_group_name,
                cluster_name,
            )
            break
        except (ResourceNotFoundError, ResourceExistsError):
            sleep(20)
    kubeconfig = credentials.kubeconfigs[0].value.decode("utf-8")

    if kubeconfig_path.exists():
        existing_config = yaml.safe_load(kubeconfig_path.read_text())
        new_config = yaml.safe_load(kubeconfig)
        existing_config["clusters"].extend(new_config["clusters"])
        existing_config["contexts"].extend(new_config["contexts"])
        existing_config["users"].extend(new_config["users"])
        kubeconfig_path.write_text(yaml.safe_dump(existing_config))
    else:
        kubeconfig_path.parent.mkdir(parents=True, exist_ok=True)
        kubeconfig_path.write_text(kubeconfig)


def set_current_context(cluster_name: str) -> None:
    """Set the current context in kubeconfig to the specified AKS cluster.

    Args:
        cluster_name (str): Name of the AKS cluster to set as current context.

    Returns:
        None

    """
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        for context in kubeconfig["contexts"]:
            if cluster_name in context["name"]:
                kubeconfig["current-context"] = context["name"]
                break
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))


def remove_from_kubeconfig(resource_group_name: str) -> None:
    """Remove AKS cluster credentials from kubeconfig.

    Args:
        resource_group_name (str): Name of the resource group containing the AKS cluster.

    Returns:
        None

    """
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        kubeconfig["clusters"] = [c for c in kubeconfig["clusters"] if resource_group_name not in c["name"]]
        kubeconfig["contexts"] = [c for c in kubeconfig["contexts"] if resource_group_name not in c["name"]]
        kubeconfig["users"] = [c for c in kubeconfig["users"] if resource_group_name not in c["name"]]
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))


def cleanup_kubeconfig() -> None:
    """Clean up kubeconfig by removing all clusters, contexts, and users that start with "kina-".

    Returns:
        None

    """
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        kubeconfig["clusters"] = [c for c in kubeconfig["clusters"] if not c["name"].startswith("kina-")]
        kubeconfig["contexts"] = [c for c in kubeconfig["contexts"] if not c["name"].startswith("kina-")]
        kubeconfig["users"] = [c for c in kubeconfig["users"] if not c["name"].startswith("clusterUser_kina-")]
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))
