# fetcher/reboot.py
from pymongo import MongoClient
import re
import logging
from config import Config

logger = logging.getLogger(__name__)

def remove_round_flag_instances(collection):
    """
    Processes all documents in the given collection with the following steps:
    1. Update the "round" field in every document to -1.
    2. For documents where "processable" is "server_busy", update its value to True.
    3. Remove all keys matching the regex pattern "^round.*_id_range$".
    """

    # 1. Update the "round" field in all documents to -1
    collection.update_many({}, {"$set": {"round": -1}})
    logger.info("Updated 'round' field to -1 for all documents.")

    # 2. For documents where "processable" is "server_busy", update its value to True
    collection.update_many({"processable": "server_busy"}, {"$set": {"processable": True}})
    logger.info("Updated 'processable' from 'server_busy' to True.")

    # 3. Remove keys matching the pattern "^round.*_id_range$" from all documents
    pattern = re.compile(r'^round.*_id_range$')

    # Iterate over all documents and check for keys to remove
    for doc in collection.find({}):
        unset_fields = {}
        for key in doc.keys():
            if pattern.match(key):
                unset_fields[key] = ""  # For $unset, the value can be an empty string
        if unset_fields:
            collection.update_one({"_id": doc["_id"]}, {"$unset": unset_fields})
    logger.info(f"Removed round_*_id_range key")

def drop_collection(collections,name):
    """
    Drops the provided collection.
    If an error occurs during the drop operation, it logs the error.
    """
    
    try:
        collections[name].drop()
        logger.info(f"Droped local {name}.")
    except Exception as e:
        logger.error(f"Droped local {name} ERROR: {e}")


def main():
    """
    Main function:
    1. Loads the configuration to retrieve central and local MongoDB URIs.
    2. Connects to the 'instances' collection from the central MongoDB database
       and the 'livefeeds' collection from the local MongoDB database.
    3. Calls remove_round_flag_instances to process the 'instances' collection.
    4. Calls drop_livefeeds to delete the 'livefeeds' collection.
    """

    config = Config()
    central_mongodb_uri = config.get_central_mongodb_uri()
    client = MongoClient(central_mongodb_uri)
    db = client['mastodon']
    instances_collection = db['instances']
    
    local_mongodb_uri = config.get_local_mongodb_uri()
    local_client = MongoClient(local_mongodb_uri)
    local_db = local_client['mastodon']
    local_livefeeds_collection = local_db['livefeeds']
    local_context_collection = local_db['context']


    collections = {
        'livefeeds': local_livefeeds_collection,
        'instances': instances_collection,
        'context' : local_context_collection
    }

    remove_round_flag_instances(collections['instances'])
    drop_collection(collections,'livefeeds')
    drop_collection(collections,'boostersfavourites')
    drop_collection(collections,'context')

if __name__ == "__main__":
    main()