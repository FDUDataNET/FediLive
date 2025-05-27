# fetcher/utils.py
import logging
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone
import time
import math

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
        ).limit(10))
            
        for candidate in candidates:
            batch = local_livefeeds_collection.find_one_and_update(
                {"_id": candidate["_id"], status_name: "pending"},
                {"$set": {status_name: "read"}}
            )
            if batch:
                logger.info(f"Found status ID: {batch['instance_name']}#{batch['id']}")
                return batch
        logger.info(f"No matching statuses found, retrying... Attempt {retry_time}")
        time.sleep(30)
        retry_time += 1
        if retry_time >= retry_thresh and not limit_set:
            logger.info("No eligible statuses found and limit_set is empty. Terminating task.")
            return None

def parse_datetime(dt_str):
    """
    Parse an ISO 8601 formatted datetime string.
    
    This function automatically handles trailing 'Z' by converting it to '+00:00'
    and returns a datetime object with timezone information.
    
    Args:
        dt_str (str): An ISO 8601 formatted datetime string, e.g., 
                      "2025-03-05T12:34:56+00:00" or "2025-03-05T12:34:56Z".
                      
    Returns:
        datetime or None: The parsed datetime object if successful, otherwise None.
    """
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.error(f"Error parsing datetime string: {dt_str}. Error: {e}")
        return None
    # If timezone information is missing, default to UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def create_unique_index(collection, index_name):
    """
    Create a unique index on the specified field in a MongoDB collection.
    
    Args:
        collection (pymongo.collection.Collection): The MongoDB collection.
        index_name (str): The field name on which to create a unique index.
    """
    existing_indexes = collection.index_information()
    if index_name not in existing_indexes:
        try:
            collection.create_index([(index_name, 1)], unique=True)
            logger.info(f"Unique index on '{index_name}' created for collection '{collection.name}'.")
        except DuplicateKeyError:
            logger.error(f"Duplicate key error: A document violates the unique constraint on '{index_name}'.")
        except Exception as e:
            logger.error(f"Error creating index '{index_name}': {e}")
    else:
        logger.info(f"Unique index on '{index_name}' already exists for collection '{collection.name}'.")

def judge_sleep(res_headers, instance_name):
    """
    Handle rate limiting based on the API response headers by sleeping if necessary.
    
    If the 'x-ratelimit-remaining' header is 0 or less, the function calculates the sleep 
    time based on the 'x-ratelimit-reset' header and then sleeps until that time.
    
    Args:
        res_headers (dict): The API response headers.
        instance_name (str): The name of the Mastodon instance.
        
    Returns:
        bool: Returns False if it slept (indicating a delay), otherwise True.
    """
    # Convert all header keys to lowercase
    res_headers = {k.lower(): v for k, v in res_headers.items()}
    if int(res_headers.get('x-ratelimit-remaining', 2)) <= 5:
        target_time_str = res_headers.get('x-ratelimit-reset')
        if target_time_str:
            target_time = parse_datetime(target_time_str.replace('T', ' '))
            if target_time:
                current_time = datetime.now(timezone.utc)
                sleep_time = (target_time - current_time).total_seconds()
                if sleep_time > 0:
                    logger.info(f"[{instance_name}] Rate limit reached. Sleeping until {target_time.isoformat()}")
                    time.sleep(sleep_time)
                    return False
    return True

def rename_key(d, old_key, new_key):
    """
    Rename a key in a dictionary if it exists.
    
    Args:
        d (dict): The dictionary.
        old_key (str): The current key name.
        new_key (str): The new key name.
        
    Returns:
        dict: The modified dictionary.
    """
    if old_key in d:
        d[new_key] = d.pop(old_key)
    return d

def save_error_log(collection, data_name, object_name, content, res_code='None', error_message='None'):
    """
    Save an error log entry to the specified MongoDB collection.
    
    Args:
        collection (pymongo.collection.Collection): The MongoDB collection for error logs.
        data_name (str): The name of the data source.
        object_name (str): The name of the object involved in the error.
        content (str): Content related to the error.
        res_code (str, optional): Response code. Defaults to 'None'.
        error_message (str, optional): Error message. Defaults to 'None'.
    """
    current_time = datetime.now()
    log_entry = {
        'loadtime': current_time,
        "data_name": data_name,
        "object": object_name,
        "content": content,
        "response_code": res_code,
        "error_message": error_message
    }
    try:
        collection.insert_one(log_entry)
        logger.info(f"Saved error log: {log_entry}")
    except Exception as e:
        logger.error(f"Failed to save error log: {e}")

def transform_ISO2datetime(time_str):
    """
    Convert an ISO 8601 formatted string to a datetime object.
    
    Args:
        time_str (str): An ISO 8601 formatted time string, e.g., "2025-03-05T12:34:56.789Z".
        
    Returns:
        datetime: The corresponding datetime object.
    """
    dt_naive = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt_naive.replace(tzinfo=timezone.utc)

def transform_str2datetime(time_str):
    """
    Convert a formatted time string to a datetime object.
    
    Args:
        time_str (str): A time string in the format 'YYYY-MM-DD HH:MM:SS'.
        
    Returns:
        datetime: The corresponding datetime object.
    """
    dt_naive = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return dt_naive.replace(tzinfo=timezone.utc)

def compute_round_time(global_duration):
    """
    Compute the number of rounds based on a duration.
    
    Args:
        global_duration (dict): A dictionary containing 'start_time' and 'end_time' (both datetime objects).
        
    Returns:
        int: The number of rounds (ceiling of the total hours).
    """
    time_diff = global_duration['end_time'] - global_duration['start_time']
    hours_diff = time_diff.total_seconds() / 3600
    return math.ceil(hours_diff)

def judge_sleep_limit_table(res_headers, instance_name, limit_dict, limit_set):
    """
    Check rate limiting information from API response headers to determine whether to sleep or record limit state.
    
    - If 'x-ratelimit-remaining' <= 0, calculate sleep time based on 'x-ratelimit-reset' and sleep.
    - If 'x-ratelimit-remaining' <= 50 and the reset time is in the future, record the limit state.
    
    Args:
        res_headers (dict): The API response headers.
        instance_name (str): The instance name.
        limit_dict (dict): Dictionary to store the instance's limit reset time (in ISO format).
        limit_set (set): Set of instance names that are currently rate-limited.
        
    Returns:
        bool or None: Returns False if it slept, True if limit state was recorded, or None if no action was taken.
    """
    res_headers = {k.lower(): v for k, v in res_headers.items()}
    remaining = int(res_headers.get('x-ratelimit-remaining', 2))
    target_time_str = res_headers.get('x-ratelimit-reset')
    
    if not target_time_str:
        return None

    target_time = parse_datetime(target_time_str.replace('T', ' '))
    if not target_time:
        return None

    current_time = datetime.now(timezone.utc)
    
    # Sleep if the remaining limit is 0 or less.
    if remaining <= 0:
        sleep_time = (target_time - current_time).total_seconds()
        if sleep_time > 0:
            logger.info(f"{current_time} sleep to {target_time}")
            time.sleep(sleep_time)
            return False

    # If remaining limit is low, record the rate limit state.
    if remaining <= 50 and target_time > current_time:
        limit_dict[instance_name] = target_time.isoformat()
        limit_set.add(instance_name)
        logger.info(f"Added {instance_name} into limit dict with reset time {target_time.isoformat()}")
        return True

def judge_api_islimit(limit_dict, limit_set):
    """
    Check if the rate limit has expired for each instance in the limit dictionary.
    
    For each instance, if the stored reset time is less than or equal to the current time,
    remove the instance from the limit set and delete the corresponding entry in limit_dict.
    
    Args:
        limit_dict (dict): Dictionary storing instances' rate limit reset times in ISO format.
        limit_set (set): Set of instance names currently under rate limit.
    """
    current_time = datetime.now(timezone.utc)
    keys_to_remove = []
    
    for key, value in limit_dict.items():
        target_time = parse_datetime(value)
        if not target_time:
            continue
        if target_time <= current_time:
            limit_set.discard(key)
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del limit_dict[key]

def update_round_idrange(instances_collection, instance_info, current_round_id_range):
    """
    Update the id_range information for the current round of a given instance in MongoDB.
    
    Args:
        instances_collection (pymongo.collection.Collection): The MongoDB collection with instance information.
        instance_info (dict): A dictionary containing instance details (must include 'name' and 'round').
        current_round_id_range: The current round's id_range value.
    """
    try:
        # Build the field name dynamically using the instance's round.
        field_name = f"round{instance_info['round']}_id_range"
        instances_collection.update_one(
            {"name": instance_info['name']},
            {"$set": {field_name: current_round_id_range}}
        )
        logger.info(f"Updated {instance_info['name']}'s {field_name} to {current_round_id_range}.")
    except Exception as e:
        logger.error(f"Update {instance_info['name']}'s current_round_id_range ERROR: {e}")
