import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config

logger = logging.getLogger(__name__)

def reactivate_failed_instances(instances_collection, target_instance_names):
    """
    Finds instances with processable=False and resets them.

    Args:
        instances_collection (pymongo.collection.Collection): The MongoDB collection for instances.
        target_instance_names (list): List of instance names to check.
    """
    logger.info(f"Checking for failed instances in list: {target_instance_names}")

    query = {
        "name": {"$in": target_instance_names},
        "processable": False
    }
    update_operation = {
        "$inc": {"round": -1},
        "$set": {"processable": True}
    }

    try:
        result = instances_collection.update_many(query, update_operation)
        if result.modified_count > 0:
            logger.info(f"Successfully reactivated {result.modified_count} instance(s).")
        else:
            logger.info("No failed instances found to reactivate.")
    except PyMongoError as e:
        logger.error(f"A database error occurred during the update operation: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

def get_instances_collection(config: Config):
    """
    Helper function to get the MongoDB instances collection.

    Args:
        config (Config): The config object.

    Returns:
        pymongo.collection.Collection: The MongoDB collection.
    """
    client = MongoClient(config.get_central_mongodb_uri())
    db = client['mastodon']
    return db['instances'], client

def run_reactivation_task():
    """
    Reactivates failed instances using the whitelist from config.
    This function is suitable for being called by other Python programs.
    """
    config = Config()
    whitelist = getattr(config, "whitelist", None)
    if whitelist is None:
        logger.error("Config does not have 'whitelist' attribute.")
        return

    instances_collection, client = None, None
    try:
        logger.info("Connecting to MongoDB...")
        instances_collection, client = get_instances_collection(config)
        logger.info("Successfully connected to MongoDB.")
        logger.info("--- Starting instance reactivation task ---")
        reactivate_failed_instances(instances_collection, whitelist)
        logger.info("--- Task finished. ---")
    except PyMongoError as e:
        logger.error(f"Failed to connect to MongoDB. Please check URI and server status. Error: {e}")
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed.")

if __name__ == "__main__":
    run_reactivation_task()
