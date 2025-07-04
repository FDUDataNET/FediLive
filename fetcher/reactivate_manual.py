# Some large instances may occasionally have connection errors due to the large number of tweets and the large number of crawls, which will cause their processable to be set to false. 
# This function is used to force the false processable to be true for those instances that you know belong to Mastodon. You can modify the value of target_instance_names in the main function.
import sys
import time
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config

# --- Logger Configuration ---
logger = logging.getLogger(__name__)

def reactivate_failed_instances(instances_collection,target_instance_names):
    """
    Finds instances with processable=False and resets them.

    This function queries the 'instances' collection for documents that are
    in the target list and currently have their 'processable' flag set to False.
    It then updates these documents by decrementing the 'round' field by 1 and
    setting 'processable' back to True.

    Args:
        instances_collection (pymongo.collection.Collection): The MongoDB collection
            for instances.
    """
    
    logger.info(f"Checking for failed instances in list: {target_instance_names}")

    # Define the query to find the target instances that are not processable
    query = {
        "name": {"$in": target_instance_names},
        "processable": False
    }

    # Define the update operation
    # $inc decrements the 'round' field, $set updates 'processable' to True
    update_operation = {
        "$inc": {"round": -1},
        "$set": {"processable": True}
    }

    try:
        # Use update_many to update all documents matching the query
        result = instances_collection.update_many(query, update_operation)
        
        # Log the outcome of the operation
        if result.modified_count > 0:
            logger.info(
                f"Successfully reactivated {result.modified_count} instance(s)."
            )
        else:
            logger.info("No failed instances found to reactivate.")
            
    except PyMongoError as e:
        logger.error(f"A database error occurred during the update operation: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def main():
    """
    Main function to set up the database connection and run the reactivation
    task in a loop.
    """
    config = Config()
    client = None  # Initialize client to None for the finally block
    # Initialize the list of instances to check
    target_instance_names = ["mastodon.social"]

    try:
        # Establish connection to MongoDB
        logger.info("Connecting to MongoDB...")
        client = MongoClient(config.get_central_mongodb_uri())
        # The ismaster command is cheap and does not require auth.
        logger.info("Successfully connected to MongoDB.")
        
        db = client['mastodon']
        instances_collection = db['instances']

        # Main loop to run the task periodically
        while True:
            logger.info("--- Starting instance reactivation task ---")
            reactivate_failed_instances(instances_collection,target_instance_names)
            logger.info("--- Task finished. Waiting for 60 seconds... ---")
            time.sleep(60)

    except PyMongoError as e:
        logger.error(f"Failed to connect to MongoDB. Please check URI and server status. Error: {e}")
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Shutting down.")
    finally:
        # Ensure the database connection is closed on exit
        if client:
            client.close()
            logger.info("MongoDB connection closed.")

if __name__ == "__main__":
    main()