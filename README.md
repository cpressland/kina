# Kina - Kubernetes in Azure

Inspired by [`kind`](https://github.com/kubernetes-sigs/kind), Kina aims to spawn Kubernetes clusters in Azure and add them to your local kubectl config with minimal fuss.

> [!WARNING]
> These clusters are not suitable for production workloads and have several developer features enabled by default.

## Installation

Kina is managed via uv. While tools like pip or pipx may work, only uv is officially supported.

`$ uv tool install kina`

If this is your first time using `uv`, make sure it's tools directory is in your `PATH`, e.g. `~/.local/bin`.

## Usage

### Create an AKS Cluster

> [!TIP]
> Kina reads your `~/.azure/azureProfile.json` for configuration, specifically using the currently active Subscription ID as the base for resource creation.

`$ kina create`

This creates a Kubernetes cluster in `uksouth` using the latest version and sensible defaults for local development. You can override the location with the `--location` flag:

### Create Multiple VNet-Peered AKS Clusters

To test multi-cluster service meshes (e.g. Linkerd, Istio) or eBPF-based solutions like Cilium, you can spawn multiple VNet-peered clusters:

`$ kina create --locations="uksouth,ukwest,northeurope,westeurope"`

Kina assigns IP ranges as follows:
* Virtual Network CIDR: `10.0.0.0/16`
* Pod CIDR: `10.1.0.0/16`
* Service CIDR: `10.2.0.0/16`

Subsequent locations increment accordingly:
* Virtual Network CIDR: `10.3.0.0/16`
* Pod CIDR: `10.4.0.0/16`
* Service CIDR: `10.5.0.0/16`

And so on.

### Listing Kina Instances

List your Kina clusters with: `$ kina list`

You can specify output formats using --output, e.g. table, json, or names.

```shell
$ kina list
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name        ┃ Location(s) ┃ Created By                      ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ kina-1eoyoe │ uksouth     │ example@example.onmicrosoft.com │
└─────────────┴─────────────┴─────────────────────────────────┘

$ kina list -o json
[
  {
    "name": "kina-1eoyoe",
    "locations": "uksouth",
    "created_by": "example@example.onmicrosoft.com"
  }
]

$ kina list -o names
kina-1eoyoe
```

## FAQs

**Q:** Sometimes I get a DNS lookup failure, e.g. `Unable to connect to the server: dial tcp: lookup kina-277rtg-uksouth-ey6vbz58.hcp.uksouth.azmk8s.io: no such host`:

**A:** Because we create the AKS Clusters asynchronously, sometimes we've actually configured `kubectl` before Microsoft has published a DNS record for the cluster. Wait a few minutes and try again.

**Q:** How can I setup cilium clustermesh using this?

**A:** Simply install Cilium on two or more clusters you create with this tool, e.g.:

On Cluster 1: `$ cilium install --version 1.17.2 --set azure.resourceGroup="<resource group name>" --set cluster.id=1 --set ipam.operator.clusterPoolIPv4PodCIDRList="{10.1.0.0/16}"` then enable clustermesh with `$ cilium clustermesh enable --context "<cluster name>"`

On Cluster 2: `$ cilium install --version 1.17.2 --set azure.resourceGroup="<resource group name" --set cluster.id=2 --set ipam.operator.clusterPoolIPv4PodCIDRList="{10.4.0.0/16}"` then enable clustermesh with `$ cilium clustermesh enable --context "<cluster name>"`

Now you're ready to enable clustermesh between these clusters, `cilium clustermesh connect --context "<cluster 1>" --destination-context "<cluster 2>"`

Finally, run a connection test: `$ cilium connectivity test --context "<cluster 1>" --multi-cluster "<cluster 2>"`

**Q:** Why wouldn't this tool just use the Cilium Dataplane that AKS ships with?

**A:** Microsoft's distribution of Cilium does not support Clustermesh.
