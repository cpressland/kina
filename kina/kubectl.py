from pathlib import Path
from time import sleep

import yaml
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient

kubeconfig_path = Path("~/.kube/config").expanduser()


def add_cluster_to_kubeconfig(
    credential: DefaultAzureCredential, subscription_id: str, resource_group_name: str, cluster_name: str
) -> None:
    aks_client = ContainerServiceClient(credential, subscription_id)
    for _ in range(20):
        try:
            credentials = aks_client.managed_clusters.list_cluster_admin_credentials(resource_group_name, cluster_name)
            break
        except ResourceNotFoundError:
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
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        for context in kubeconfig["contexts"]:
            if cluster_name in context["name"]:
                kubeconfig["current-context"] = context["name"]
                break
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))


def remove_from_kubeconfig(resource_group_name: str) -> None:
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        kubeconfig["clusters"] = [c for c in kubeconfig["clusters"] if resource_group_name not in c["name"]]
        kubeconfig["contexts"] = [c for c in kubeconfig["contexts"] if resource_group_name not in c["name"]]
        kubeconfig["users"] = [c for c in kubeconfig["users"] if resource_group_name not in c["name"]]
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))


def cleanup_kubeconfig() -> None:
    if kubeconfig_path.exists():
        kubeconfig = yaml.safe_load(kubeconfig_path.read_text())
        kubeconfig["clusters"] = [c for c in kubeconfig["clusters"] if not c["name"].startswith("kina-")]
        kubeconfig["contexts"] = [c for c in kubeconfig["contexts"] if not c["name"].startswith("kina-")]
        kubeconfig["users"] = [c for c in kubeconfig["users"] if not c["name"].startswith("clusterUser_kina-")]
        kubeconfig_path.write_text(yaml.safe_dump(kubeconfig))
