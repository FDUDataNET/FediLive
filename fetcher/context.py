# fetcher/context.py

# fetcher/reblog_favourite.py
import requests
import time
import re
from datetime import datetime, timezone, timedelta
import argparse
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from multiprocessing import Process
import logging
import random
from utils import judge_sleep_limit_table, judge_api_islimit, create_unique_index, fetch_livefeed_id
from config import Config

logger = logging.getLogger(__name__)

limit_dict = {}
limit_set = set()

status_name = "context_status"


def get_context(instance, status_id, headers, local_collections):
    context_url = f"https://{instance}/api/v1/statuses/{status_id}/context"
    retry_thresh = 8

    retry_time = 0
    while True:
        try:
            response = requests.get(context_url, headers=headers, timeout=5)
            if response.status_code == 200:
                res_headers = {k.lower(): v for k, v in response.headers.items()}
                judge_sleep_limit_table(res_headers, instance,limit_dict,limit_set)
                data = response.json()
                logger.info(f"{instance}#{status_id}: success fetch context")
                if (len(data['ancestors']) >0) or (len(data['descendants']) >0):
                    data['sid'] = f"{instance}#{status_id}"
                    local_collections['context'].insert_one(data)
                    logger.info(f"{instance}#{status_id}: success save context")
                    return True
                else:
                    logger.info(f"{instance}#{status_id}: has no context")
                    return True
            elif response.status_code in [503, 429]:
                    retry_time += 1
                    time.sleep(10)
                    logger.warning(f"{instance}#{status_id}: Encountered 429 or 503 error, retrying...")
                    if retry_time > retry_thresh:
                        limit_set.add(instance)
                        limit_dict[instance] = datetime.now(timezone.utc) + timedelta(minutes=5)
                        return False
            else:
                logger.error(f"{instance}#{status_id}: error fetching context: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            retry_time += 1
            time.sleep(random.random())
            logger.warning(f"{instance}#{status_id}: Request timed out, retrying...")
            if retry_time > retry_thresh:
                return False
        except Exception as e:
            logger.exception(f"{instance}#{status_id}: Exception while connecting: {e}")
            return False


def process_task(token, config, local_collections, terminate_flag):
    """
    Worker process task for fetching reblogs and favourites.

    Args:
        config (Config): Configuration object.
        local_collections (dict): Local MongoDB collections.
        token : API token.
        terminate_flag (dict): Dictionary flag to terminate processes.
    """
    no_pending_counter = 0  # Counter to track consecutive iterations with no pending statuses
    inactivity_threshold = 10  # Number of consecutive iterations without pending statuses before termination
    
    while not terminate_flag['terminate']:
        try:
            info = fetch_livefeed_id(local_collections['livefeeds'], limit_set, limit_dict, status_name="context_status")
            if info:
                # Reset counter if a pending status is found
                no_pending_counter = 0
                headers = {'Authorization': f'Bearer {token}', 'Email': config.api.get('email', '')}
                success = get_context(info['instance_name'], info['id'], headers, local_collections)
                time.sleep(random.random())
                if success:
                    local_collections['livefeeds'].update_one(
                        {"_id": info["_id"]},
                        {"$set": {status_name: "completed"}}
                    )
                    logger.info(f"Successfully fetched context for {info['instance_name']}#{info['id']}")
                else:
                    local_collections['livefeeds'].update_one(
                        {"_id": info["_id"]},
                        {"$set": {status_name: "error"}}
                    )
                    logger.info(f"Error fetched context for {info['instance_name']}#{info['id']}")
            else:
                no_pending_counter += 1
                logger.info(f"No pending statuses found, sleeping... (attempt {no_pending_counter})")
                time.sleep(60)
                if no_pending_counter >= inactivity_threshold:
                    logger.info("No pending statuses found for a prolonged period. Terminating process.")
                    terminate_flag['terminate'] = True
                    break
        except Exception as e:
            # Ensure info is defined before using it in the error update
            if 'info' in locals() and info and '_id' in info:
                local_collections['livefeeds'].update_one(
                    {"_id": info["_id"]},
                    {"$set": {status_name: "fail", "fail_reason": str(e)}}
                )
            logger.exception(f"Exception during processing: {e}")
            time.sleep(5)


def main():
    """
    Main function to parse arguments and start worker processes.
    """
    parser = argparse.ArgumentParser(description='Mastodon Context Worker')
    parser.add_argument('--processnum', type=int, default=1, help='Number of parallel processes')
    parser.add_argument('--id', type=int, default=1, help='Number of parallel processes')
    args = parser.parse_args()
    
    config = Config()

    
    local_mongodb_uri = config.get_local_mongodb_uri()
    local_client = MongoClient(local_mongodb_uri)
    local_db = local_client['mastodon']
    local_livefeeds_collection = local_db['livefeeds']
    local_context_collection = local_db['context']

    create_unique_index(local_context_collection,'sid')

    with open(config.paths.get('token_list', 'tokens/token_list.txt'), 'r', encoding='utf-8') as f:
        tokens = f.read().splitlines()
    
    local_collections = {
        'livefeeds': local_livefeeds_collection,
        'context': local_context_collection
    }
    
    terminate_flag = {'terminate': False}
    token = tokens[args.id]
    process_list = []
    for i in range(args.processnum):
        p = Process(target=process_task, args=(token, config, local_collections, terminate_flag))
        p.start()
        process_list.append(p)
    
    try:
        for p in process_list:
            p.join()
    except KeyboardInterrupt:
        terminate_flag['terminate'] = True
        for p in process_list:
            p.terminate()
        logger.info("Terminated all processes.")

    local_client.close()
    logger.info("Context Worker task completed.")

if __name__ == "__main__":
    main()
    