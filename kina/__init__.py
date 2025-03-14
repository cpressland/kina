from typing import Annotated

import typer
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
kubectl = typer.Typer(no_args_is_help=True, help="Manage local Kubectl Configuration")
app.add_typer(kubectl, name="kubectl")

config = {
    "subscription_id": None,
    "credential": DefaultAzureCredential(),
}


@app.callback()
def callback(subscription_id: Annotated[str, typer.Option()] | None = None) -> None:
    """
    Manage AKS Clusters with Kina.
    """
    config["subscription_id"] = subscription_id


@app.command()
def create(
    primary_region: str = "uksouth",
    primary_cidr: str = "10.0.0.0/20",
    secondary_region: str = "northeurope",
    secondary_cidr: str = "10.0.16.0/20",
) -> None:
    from kina.kubectl import add_cluster_to_kubeconfig
    from kina.kubernetes_clusters import create_aks_cluster
    from kina.resource_groups import create_resource_group
    from kina.virtual_networks import create_virtual_networks

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        rg_task = progress.add_task("Creating Resource Group...", total=1)
        vnet_task = progress.add_task("Creating Virtual Networks...", total=1)
        aks_task = progress.add_task("Creating AKS Clusters...", total=1)
        kubectl_task = progress.add_task("Configuring kubectl...", total=1)
        rg_name = create_resource_group(
            credential=config["credential"], subscription_id=config["subscription_id"], location=primary_region
        )
        progress.update(rg_task, description=f"Created Resource Group: {rg_name}", advance=1)
        vnet_names = create_virtual_networks(
            credential=config["credential"],
            subscription_id=config["subscription_id"],
            primary_region=primary_region,
            primary_cidr=primary_cidr,
            secondary_region=secondary_region,
            secondary_cidr=secondary_cidr,
            resource_group_name=rg_name,
        )
        progress.update(vnet_task, description=f"Created Virtual Networks: {', '.join(vnet_names)}", advance=1)
        cluster_names = create_aks_cluster(
            credential=config["credential"],
            subscription_id=config["subscription_id"],
            virtual_network_names=vnet_names,
            resource_group_name=rg_name,
        )
        progress.update(aks_task, description=f"Created AKS Clusters: {', '.join(cluster_names)}", advance=1)
        for cluster in cluster_names:
            add_cluster_to_kubeconfig(config["credential"], config["subscription_id"], rg_name, cluster)
        progress.update(kubectl_task, description="Configured kubectl", advance=1)


@app.command()
def list() -> None:
    from kina.resource_groups import list_resource_groups

    t = Table(title="Kina Instances")
    t.add_column("Name")
    t.add_column("Location")
    t.add_column("Created By")

    resource_groups = list_resource_groups(config["credential"], config["subscription_id"])
    for resource_group in resource_groups:
        t.add_row(resource_group[0], resource_group[1], resource_group[2])
    console = Console()
    console.print(t)


@app.command()
def delete(name: str) -> None:
    from kina.resource_groups import delete_resource_group

    delete_resource_group(config["credential"], config["subscription_id"], name)
    typer.echo(f"Deleted Kina Instance: {name}")


@kubectl.command()
def cleanup() -> None:
    from kina.kubectl import cleanup_kubeconfig

    cleanup_kubeconfig()
    typer.echo("Cleaned up kubectl configuration")


@kubectl.command()
def remove(name: str) -> None:
    from kina.kubectl import remove_from_kubeconfig

    remove_from_kubeconfig(name)
    typer.echo(f"Removed Kina Instance from Kubeconfig: {name}")


if __name__ == "__main__":
    app()
