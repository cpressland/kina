from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient


def get_location_availability_zones(
    credential: DefaultAzureCredential, subscription_id: str, location: str
) -> list[str]:
    client = SubscriptionClient(credential)
    loc = next((loc for loc in client.subscriptions.list_locations(subscription_id) if loc.name == location), None)
    return [zone.logical_zone for zone in (loc.availability_zone_mappings or [])]
