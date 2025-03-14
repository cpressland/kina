import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()


@app.command()
def hello_world(
    primary_region: str = "uksouth",
    primary_cidr: str = "10.0.0.0/20",
    secondary_region: str = "northeurope",
    secondary_cidr: str = "10.0.16.0/20",
) -> None:
    from azure.identity import DefaultAzureCredential

    from kina.kubernetes_clusters import create_aks_cluster
    from kina.resource_groups import create_resource_group
    from kina.virtual_networks import create_virtual_networks

    subscription_id = "6272fd2e-8961-4ff9-8332-f3606e3ee4b4"
    credential = DefaultAzureCredential()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        rg_task = progress.add_task("Creating Resource Group...", total=1)
        vnet_task = progress.add_task("Creating Virtual Networks...", total=1)
        aks_task = progress.add_task("Creating AKS Clusters...", total=1)
        rg_name = create_resource_group(credential=credential, subscription_id=subscription_id, location=primary_region)
        progress.update(rg_task, description=f"Created Resource Group: {rg_name}", advance=1)
        vnet_names = create_virtual_networks(
            credential=credential,
            subscription_id=subscription_id,
            primary_region=primary_region,
            primary_cidr=primary_cidr,
            secondary_region=secondary_region,
            secondary_cidr=secondary_cidr,
            resource_group_name=rg_name,
        )
        progress.update(vnet_task, description=f"Created Virtual Networks: {', '.join(vnet_names)}", advance=1)
        cluster_names = create_aks_cluster(
            credential=credential,
            subscription_id=subscription_id,
            virtual_network_names=vnet_names,
            resource_group_name=rg_name,
        )
        progress.update(aks_task, description=f"Created AKS Clusters: {', '.join(cluster_names)}", advance=1)


if __name__ == "__main__":
    app()
