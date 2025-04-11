import logging
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
import time
import math
from .utils import judge_sleep_limit_table, judge_api_islimit, save_error_log, create_unique_index

logger = logging.getLogger(__name__)

def fetch_livefeed_id(local_livefeeds_collection, limit_set, limit_dict, status_name, retry_thresh=10):
    """
    Fetches a status ID from the livefeeds collection that is pending processing.
    
    Args:
        local_livefeeds_collection (pymongo.collection.Collection): The livefeeds collection.
        limit_set (set): Set of instances under rate limit.
        local_collections (dict): Local MongoDB collections.
        retry_thresh (int, optional): Retry threshold. Defaults to 10.
    
    Returns:
        dict or None: The status information or None if not found.
    """
    retry_time = 0
    while True:
        judge_api_islimit(limit_dict,limit_set)
        candidates = list(local_livefeeds_collection.find(
            {
                status_name: "pending",
                "instance_name": {"$nin": list(limit_set)}
            }
        ).limit(5))
            
        for candidate in candidates:
            batch = local_livefeeds_collection.find_one_and_update(
                {"_id": candidate["_id"], "status": "pending"},
                {"$set": {status_name: "read"}}
            )
            if batch:
                logger.info(f"Found status ID: {batch['instance_name']}#{batch['id']}")
                return batch
        logger.info(f"No matching statuses found, retrying... Attempt {retry_time}")
        time.sleep(2)
        retry_time += 1
        if retry_time >= retry_thresh and not limit_set:
            logger.info("No eligible statuses found and limit_set is empty. Terminating task.")
            return None