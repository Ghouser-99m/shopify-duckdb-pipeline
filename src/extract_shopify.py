import os
import time
import logging
from typing import Iterator, Dict, Any

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2024-10"


class ShopifyClient:
    def __init__(self, shop: str = None, access_token: str = None):
        self.shop = shop or os.environ["SHOPIFY_SHOP"]
        self.access_token = access_token or os.environ["SHOPIFY_ACCESS_TOKEN"]
        self.base_url = f"https://{self.shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json",
            }
        )

    def _paginated_get(self, endpoint: str, params: Dict[str, Any] = None) -> Iterator[Dict]:
        url = f"{self.base_url}/{endpoint}"
        params = params or {"limit": 250}

        while url:
            resp = self.session.get(url, params=params)
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 1))
                logger.warning("Rate limited, sleeping %.1fs", retry_after)
                time.sleep(retry_after)
                continue
            resp.raise_for_status()

            data = resp.json()
            key = endpoint.split(".")[0]
            records = data.get(key, [])
            for record in records:
                yield record

            link_header = resp.headers.get("Link", "")
            next_url = None
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    next_url = link.split(";")[0].strip().strip("<>")
                    break

            url = next_url
            params = None

    def get_orders(self, status: str = "any", updated_at_min: str = None) -> Iterator[Dict]:
        params = {"limit": 250, "status": status}
        if updated_at_min:
            params["updated_at_min"] = updated_at_min
        yield from self._paginated_get("orders.json", params)

    def get_products(self) -> Iterator[Dict]:
        yield from self._paginated_get("products.json")

    def get_customers(self) -> Iterator[Dict]:
        yield from self._paginated_get("customers.json")


if __name__ == "__main__":
    client = ShopifyClient()
    count = 0
    for order in client.get_orders():
        count += 1
    logger.info("Fetched %d orders", count)
