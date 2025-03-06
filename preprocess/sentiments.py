import json
import re
import html
import requests
import argparse
import time
from multiprocessing import Process, Queue

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--id', type=int, help='this worker id')
parser.add_argument('--processnum', type=int, default=1, help='processing num')
process_num = parser.parse_args().processnum
worker_id = parser.parse_args().id

livefeeds_file = "livefeeds.json"
sentiment_file = "data/sentimentscores.json"
error_log_file = "sentiscore_errorlog.txt"

def analyze_sentiment(text, max_retries=5, retry_delay=5):
    url = "http://localhost:9000"
    params = {
        'annotators': 'sentiment',
        'outputFormat': 'json',
    }
    data = {'text': text}
    
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.post(url, params=params, data=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                sentiment_polar = [0, 0, 0, 0, 0]
                for sentence in result['sentences']:
                    sentiment_polar = [sentiment_polar[i] + sentence["sentimentDistribution"][i] for i in range(5)]
                    return sentiment_polar/len(result['sentences'])
            else:
                print(f"Error: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.Timeout as e:
            print(f"Timeout error: {e}. Retrying in {retry_delay} seconds...")
            attempt += 1
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}. Retrying in {retry_delay} seconds...")
            attempt += 1
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None

def content_process(sentence, sid):
    cleaned_text = re.sub(r'<.*?>', '', sentence)
    if cleaned_text == '':
        decoded_text = ''
        return []
    decoded_text = html.unescape(cleaned_text)
    return analyze_sentiment(decoded_text, sid)

def process_task(data_slice, queue):
    result = dict()
    for status in data_slice:
        if status['language'] != 'en':
            continue
        try:
            senti_polar = content_process(status['content'], status['sid'])
            if len(senti_polar) == 0:
                continue
            result[status['sid']] = {'content':status['content'], 'senti_polar': senti_polar}
            print(f"{status['sid']} successfully get sentiment scores")
        except Exception as e:
            error_message = f"Error processing sid {status['sid']}: {str(e)}"
            print(error_message)
    queue.put(result)

if __name__ == "__main__":
    with open(livefeeds_file, 'r') as file:
        data = json.load(file)

    data_slices = [data[i::process_num] for i in range(process_num)]

    process_list = []
    
    queue = Queue()

    for i in range(process_num):
        p = Process(target=process_task, args=(data_slices[i],queue))
        p.start()
        process_list.append(p)

    for p in process_list:
        p.join()

    final_result = {}
    while not queue.empty():
        final_result.update(queue.get())
    
    with open(sentiment_file, "w") as save_f:
        json.dump(final_result, save_f, ensure_ascii=False, indent=4)
    
    print("Processing complete. Sentiment scores saved to db. Errors logged to db")
