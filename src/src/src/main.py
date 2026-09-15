import argparse
import logging

from dotenv import load_dotenv

load_dotenv()

from src.extract_shopify import ShopifyClient
from src.load_duckdb import DuckDBLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500

ENTITY_MAP = {
    "orders": lambda client: client.get_orders(),
    "products": lambda client: client.get_products(),
    "customers": lambda client: client.get_customers(),
}


def run_entity(shopify_client: ShopifyClient, loader: DuckDBLoader, entity: str):
    logger.info("Starting sync for entity: %s", entity)
    records_iter = ENTITY_MAP[entity](shopify_client)

    batch = []
    total = 0
    first_batch = True
    for record in records_iter:
        batch.append(record)
        if len(batch) >= BATCH_SIZE:
            loader.load_records(f"raw_{entity}", batch, write_disposition="replace" if first_batch else "append")
            total += len(batch)
            batch = []
            first_batch = False

    if batch:
        loader.load_records(f"raw_{entity}", batch, write_disposition="replace" if first_batch else "append")
        total += len(batch)

    logger.info("Finished %s: %d records loaded", entity, total)


def main():
    parser = argparse.ArgumentParser(description="Sync Shopify data into DuckDB")
    parser.add_argument(
        "--entities",
        default="products",
        help="Comma-separated list of entities to sync",
    )
    args = parser.parse_args()
    entities = [e.strip() for e in args.entities.split(",") if e.strip()]

    shopify_client = ShopifyClient()
    loader = DuckDBLoader()

    for entity in entities:
        if entity not in ENTITY_MAP:
            logger.warning("Unknown entity '%s', skipping", entity)
            continue
        run_entity(shopify_client, loader, entity)

    loader.close()
    logger.info("Done. Data written to %s", loader.db_path)


if __name__ == "__main__":
    main()
