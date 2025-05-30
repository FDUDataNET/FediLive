# fetcher/livefeeds_worker.py
import sys
import requests
import time
import argparse
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from multiprocessing import Process
import random
import re
import logging
from utils import (
    create_unique_index, judge_sleep, update_round_idrange,
    transform_ISO2datetime, transform_str2datetime, compute_round_time
)
from config import Config

# Logger configuration: error-level logs only record to file, not output to console

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.addFilter(lambda record: record.levelno < logging.ERROR)
error_handler = logging.FileHandler("error.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(error_handler)

def compute_current_duration(current_round, global_duration, max_round):
    """
    Computes the current duration for the given round.
    
    Args:
        current_round (int): The current round number.
        global_duration (dict): Dictionary containing 'start_time' and 'end_time'.
        max_round (int): The maximum number of rounds.
    
    Returns:
        dict: Dictionary with 'start_time' and 'end_time' for the current round.
    """
    if current_round < max_round:
        new_start_time = global_duration['end_time'] - timedelta(hours=current_round)
    else:
        new_start_time = global_duration['start_time']
    new_end_time = global_duration['end_time'] - timedelta(hours=current_round-1)
    return {'start_time': new_start_time, 'end_time': new_end_time}

def fetch_instance(instances_collection, max_round):
    """
    Fetches an instance from the MongoDB collection based on the round number.
    
    Args:
        instances_collection (pymongo.collection.Collection): The instances collection.
        max_round (int): The maximum number of rounds.
    
    Returns:
        dict or None: The instance information or None if not found.
    """
    query = {
            "round": {"$lt":max_round},
            "processable": True,
            "livefeeds_status":"pending",
        }
    update = {
        "$inc": {"round": 1},
        "$set": {"livefeeds_status": "read"}
    }
    return instances_collection.find_one_and_update(
        query,
        update,
        return_document=True,
        sort=[("round", 1), ("statuses", -1)]
    )

def fetch_livefeeds(instance_info, config, collections, tokens, worker_id, global_duration, max_round):
    """
    Fetches livefeeds (tweets) from a specific Mastodon instance.
    
    Args:
        instance_info (dict): Information about the instance.
        config (Config): Configuration object.
        collections (dict): MongoDB collections.
        tokens (list): List of API tokens.
        worker_id (int): ID of the worker.
        global_duration (dict): Dictionary containing 'start_time' and 'end_time'.
        max_round (int): The maximum number of rounds.
    """
    instance_name = instance_info['name']
    current_round = instance_info['round']
    logger.info(f"Starting to fetch tweets from {instance_name}")
    livefeeds_url = f"https://{instance_name}/api/v1/timelines/public"
    last_page_flag = -1
    retry_time = 0
    id_range = {}
    if current_round != 0:
        id_range = instance_info.get(f'round{current_round-1}_id_range', {})
    token = tokens[worker_id % len(tokens)]
    headers = {'Authorization': f'Bearer {token}', 'Email': config.api.get('email', '')}
    r_in_currentround = 0
    params = {
            "local": True,
            "limit": 40
            }
    
    while True:
        r_in_currentround  = r_in_currentround+1
        if last_page_flag != -1:
            params['max_id'] = last_page_flag
        elif current_round != 0:
            params['max_id'] = id_range.get('min')
        
        try:
            response = requests.get(livefeeds_url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                res_headers = {k.lower(): v for k, v in response.headers.items()}
                judge_sleep(res_headers, instance_name)
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} tweets from {instance_name}.")

                # collect one toot from all instances rapidly to record the latest toot_id in specified duartion
                if current_round == 0:
                    for item in data:
                        created_at = transform_ISO2datetime(item['created_at'])
                        if global_duration['start_time'] <= created_at and created_at <= global_duration['end_time']:
                            id_range['max'] = item['id']
                            id_range['min'] = item['id']
                            item['instance_name'] = instance_name
                            item['sid'] = f"{instance_name}#{item['id']}"
                            item['loadtime'] = datetime.now()
                            item['status'] = 'pending'
                            item['context_status'] = 'pending'
                            try:
                                collections['livefeeds'].insert_one(item)
                                logger.info(f"round{current_round}: Saved toot {item['sid']}. {instance_name}.")
                            except DuplicateKeyError:
                                logger.warning(f"round{current_round}: Duplicate tweet found, skipping. {instance_name}.")
                            except Exception as e:
                                logger.error(f"round{current_round}: Error saving tweet: {e}. {instance_name}.")
                            update_round_idrange(collections['instances'],instance_info,id_range)
                            logger.info(f"round{current_round}: update_round_idrange to max:{id_range['max']}, min:{id_range['min']}. {instance_name}.")
                            return
                            
                        elif created_at < global_duration['start_time']:
                            logger.info(f"round{current_round}: {instance_name} has no toots in the specified duration.")
                            collections['instances'].update_one(
                                {"name": instance_name},
                                {"$set": {"round": max_round}}
                            )
                            return
                    logger.info(f"round{current_round}: all tweets from {instance_name} are newer than end_time.")
                    if 'link' not in res_headers or len(data) < 40:
                        return
                    match = re.search(r'max_id=(\d+)', res_headers.get('link', ''))
                    if match:
                        last_page_flag = match.group(1)
                        logger.info(f"round{current_round}: params add max_id {last_page_flag}. {instance_name}.")
                            
                # start to collect toots by round 
                else:
                    current_duration = compute_current_duration(current_round, global_duration, max_round)
                    if len(data) != 0:
                        if r_in_currentround == 1:
                            id_range['max'] = data[0]['id']
                            id_range['min'] = data[0]['id']
                    else:
                        logger.info(f"round{current_round}: {instance_name} has no tweets.")
                        collections['instances'].update_one(
                                {"name": instance_name},
                                {"$set": {"round": max_round}}
                            )

                    for item in data:
                        created_at = transform_ISO2datetime(item['created_at'])
                        if current_duration['start_time'] <= created_at <= current_duration['end_time']:
                            item['instance_name'] = instance_name
                            item['sid'] = f"{instance_name}#{item['id']}"
                            item['loadtime'] = datetime.now()
                            item['status'] = 'pending'
                            item['context_status'] = 'pending'
                            try:
                                collections['livefeeds'].insert_one(item)
                                id_range['min'] = item['id']
                                logger.info(f"round{current_round}: Saved a tweet from {instance_name}.")
                            except DuplicateKeyError:
                                logger.warning(f"round{current_round}: Duplicate tweet found, skipping. {instance_name}")
                            except Exception as e:
                                logger.error(f"round{current_round}: Error saving tweet: {e}. {instance_name}")
                        elif created_at < global_duration['start_time']:
                            logger.info(f"round{current_round}: {instance_name} has no tweets in the global duration.")
                            update_round_idrange(collections['instances'],instance_info,id_range)
                            collections['instances'].update_one(
                                {"name": instance_name},
                                {"$set": {"round": max_round}}
                            )
                            return
                        elif created_at < current_duration['start_time']:
                            update_round_idrange(collections['instances'],instance_info,id_range)
                            logger.info(f"round{current_round}: {instance_name} has no tweets in the current duration.")
                            return
                
                if 'link' not in res_headers or len(data) < 40:
                    return
                match = re.search(r'max_id=(\d+)', res_headers.get('link', ''))
                if match:
                    last_page_flag = match.group(1)
            elif response.status_code in [503, 429]:
                retry_time += 1
                time.sleep(10)
                logger.warning(f"round{current_round}: Encountered 429 or 503 error, retrying... {instance_name}")
                if retry_time > 8:
                    logger.warning(f"round{current_round}: Encountered 429 or 503 error, retrying, timed out 8 times, set processable to server_busy. {instance_name}")
                    collections['instances'].update_one(
                        {"name": instance_name},
                        {
                            "$set": {"processable": "server_busy"},
                            "$inc": {"round": -1} 
                        }
                    )
                    return
            else:
                logger.error(f"round{current_round}: Error fetching tweets from {instance_name}: {response.status_code}")
                collections['instances'].update_one(
                    {"name": instance_name},
                    {"$set": {"processable": False}}
                )
                return
        except requests.exceptions.Timeout:
            retry_time += 1
            time.sleep(10)
            logger.warning(f"round{current_round}: Request to {instance_name} timed out, retrying...")
            if retry_time > 8:
                logger.warning(f"round{current_round}: Request to {instance_name} timed out 8 times, set processable to false")
                collections['instances'].update_one(
                    {"name": instance_name},
                    {"$set": {"processable": False}}
                )
                return
        except Exception as e:
            logger.exception(f"round{current_round}: Exception while connecting to {instance_name}")
            collections['instances'].update_one(
                {"name": instance_name},
                {"$set": {"processable": False}}
            )
            return
        time.sleep(random.random())

def process_task(worker_id, config, mongo_args, tokens, global_duration, max_round):
    """
    Processes tasks by fetching instances and their tweets.
    After finishing one round (iterating through all rounds), it checks if there are any instances
    with "processable" set to "server_busy". If such instances exist and their reset count is less than 5,
    it resets their processable flag to True and increments the reset count, then starts a new round.
    The process continues until there are no eligible "server_busy" instances.
    
    Args:
        worker_id (int): The ID of the worker.
        config (Config): Configuration object.
        collections (dict): MongoDB collections.
        tokens (list): List of API tokens.
        global_duration (dict): Dictionary containing 'start_time' and 'end_time'.
        max_round (int): The maximum number of rounds.
    """

    central_client = MongoClient(mongo_args['central_mongo_uri'])
    central_db = central_client['mastodon']
    central_instances_collection = central_db['instances']

    local_client = MongoClient(mongo_args['local_mongo_uri'])
    local_db = local_client['mastodon']
    local_livefeeds_collection = local_db['livefeeds']
    local_error_collection = local_db['error_log']
    create_unique_index(local_livefeeds_collection, 'sid')

    collections = {
        'livefeeds': local_livefeeds_collection,
        'error_log': local_error_collection,
        'instances': central_instances_collection
    }
    while True:
        instance_info = fetch_instance(collections['instances'], max_round)
        if instance_info:
            logger.info(f"Found instance: {instance_info['name']}, starting processing round{instance_info['round']}.")
            fetch_livefeeds(instance_info, config, collections, tokens, worker_id, global_duration, max_round)
            collections['instances'].update_one({"name":instance_info['name']},{"$set":{"livefeeds_status":"pending"}})
            time.sleep(1)
        else:
            logger.info(f"No more instances to process.")
            # After completing a round, check if there are any instances marked as "server_busy" 
            # that have been reset less than 5 times.
            busy_count = collections['instances'].count_documents({
                "processable": "server_busy",
                "$or": [
                    {"reset_count": {"$exists": False}},
                    {"reset_count": {"$lt": 10}}
                ]
            })
            if busy_count > 0:
                logger.info("Resetting processable flag for eligible 'server_busy' instances to True.")
                # Update only those instances with reset_count not yet 5.
                collections['instances'].update_many(
                    {
                        "processable": "server_busy",
                        "$or": [
                            {"reset_count": {"$exists": False}},
                            {"reset_count": {"$lt": 10}}
                        ]
                    },
                    {
                        "$set": {"processable": True},
                        "$inc": {"reset_count": 1}
                    }
                )
            else:
                logger.info(f"No more instances need to reset processable to true from server_busy.")
                # return
            


def main():
    """
    Main function to parse arguments and start worker processes.
    """
    parser = argparse.ArgumentParser(description='Mastodon Livefeeds Worker')
    parser.add_argument('--id', type=int, required=True, help='Worker ID')
    parser.add_argument('--processnum', type=int, default=1, help='Number of parallel processes')
    parser.add_argument('--start', type=str, required=True, help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, required=True, help='End time (YYYY-MM-DD HH:MM:SS)')
    args = parser.parse_args()
    
    config = Config()
    central_mongodb_uri = config.get_central_mongodb_uri()
    #client = MongoClient(central_mongodb_uri)
    #db = client['mastodon']
    #instances_collection = db['instances']
    
    local_mongodb_uri = config.get_local_mongodb_uri()
    #local_client = MongoClient(local_mongodb_uri)
    #local_db = local_client['mastodon']
    #local_livefeeds_collection = local_db['livefeeds']
    #local_error_collection = local_db['error_log']
    

    
    with open(config.paths.get('token_list', 'tokens/token_list.txt'), 'r', encoding='utf-8') as f:
        tokens = f.read().splitlines()
    
    global_duration = {
        'start_time': transform_str2datetime(args.start),
        'end_time': transform_str2datetime(args.end)
    }
    
    max_round = compute_round_time(global_duration)
    logger.info(f"Maximum rounds: {max_round}")

    process_list = []
    for i in range(args.processnum):
        process_args = {
            'central_mongo_uri': central_mongodb_uri,
            'local_mongo_uri': local_mongodb_uri
        }
        p = Process(target=process_task, args=(args.id, config, process_args, tokens, global_duration, max_round))
        p.start()
        process_list.append(p)
    
    for p in process_list:
        p.join()
    
    #client.close()
    #local_client.close()
    logger.info("Livefeeds Worker task completed.")

if __name__ == "__main__":
    main()
