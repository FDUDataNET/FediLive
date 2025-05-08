FediLive
==================

FediLive is a data collection tool designed to quickly fetch **user interactions** from all Mastodon instances during a user-defined time period for downstream analysis.


___________________________________________________________________________

[![License][license-image]][license-url]

[license-image]:https://img.shields.io/github/license/FDUDataNET/FediLive
[license-url]: https://github.com/FDUDataNET/FediLive/blob/Multi/LICENSE

## Development Environment
Tested on Ubuntu 20.04 LTS. Please ensure your device meets the following requirements:  

OS: Ubuntu 20.04 LTS (64-bit)  
Memory: 8GB RAM (recommended)  
Storage: 20GB available space  
MongoDB: 5.0.30  
Python: 3.9

## Installation

1. **Clone the Repository**

    ```bash
    git clone -b Multi git@github.com:FDUDataNET/FediLive.git
    cd FediLive
    ```

2. **Create and Activate a Virtual Environment (Optional)**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure MongoDB and Logging**

    Ensure you have MongoDB installed and running. Edit the `config/config.yaml` file with your MongoDB connection details, API tokens, and logging preferences.  
    This is a distributed parallel crawling program for multiple machines. First, a machine must be selected as the central node. This node is used to store instance information and the range of crawled data and publish crawling tasks to working nodes. The remaining machines act as working nodes to crawl data from the instance.  
    Each machine must have MongoDB installed. In config.yaml, set mongodb_central to the central node and mongodb_local to the local machine itself. For the API, apply for central_token at https://instances.social/api/token. This token will be used to collect the list of Mastodon instances. For details, please see https://instances.social/.  

    To allow every machine to access the MongoDB on the central node, I suggest changing the net.bindIp setting in the MongoDB configuration file (mongo.conf) to 0.0.0.0. Additionally, I recommend changing the port and adding an access username and password to prevent access by unauthorized personnel. (If you are not sure how to configure it, please check [the recommended configuration tutorial](#mongodb-configure).)  
    You need to manually change these items and fill them into config.yaml.  
    ```yaml
    mongodb_central:
      username: "central_admin"
      password: "CentralPassword123!"
      host: "central.mongodb.server.com"
      port: 27017

    mongodb_local:
      username: "local_admin"
      password: "LocalPassword456!"
      host: "local.mongodb.server.com"
      port: 27018

    api:
      central_token: "your_central_api_token"
      email: "your_email@example.com"

    paths:
      instances_list: "instances_list.txt"
      token_list: "tokens/token_list.txt"

    logging:
      level: "INFO"
      file: "logs/app.log"
    ```

    - **Logging Configuration**:
      - `level`: Sets the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
      - `file`: Path to the log file where logs will be stored.

6. **Add API Tokens**

    Populate the `tokens/token_list.txt` file with your API tokens, one per line. Ensure the number of tokens exceeds the number of parallel processes you intend to run.

    These tokens will be used to collect toots from various Mastodon instances. Tokens can be requested following the guidelines at https://docs.joinmastodon.org/.


## Usage

### 1. Fetch Instance Information

Run this on the central node to fetch all Mastodon instances and store their information in MongoDB.

```bash
python ./fetcher/masto_list_fetcher.py
```

### 2. Fetch Toots
Run this on multiple machines in parallel.
```bash
python ./fetcher/livefeeds_worker.py --id 0 --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
```
Parameters:

--id: Worker ID (starting from 0), used to select different API tokens.  
--processnum: Number of parallel processes at each host.  
--start: Start time for fetching toots (format: YYYY-MM-DD HH:MM:SS) (UTC+0).  
--end: End time for fetching toots (format: YYYY-MM-DD HH:MM:SS) (UTC+0).  

### 3. Fetch Reblogs and Favourites
Run this on multiple machines in parallel.

```bash
python ./fetcher/reblog_favourite.py --processnum 3 --id 0
```
Parameters:

--processnum: Number of parallel processes.  

### 4. Restart the experiment
Run this on all machines to remove livefeeds and boosters favourites existed in MongoDB.
Make sure backup your data before running this.

```bash
python ./fetcher/reboot.py
``` 

### 5. Notes

When fetching toots, some errors may occur, but they are handled within the code. Note that the instances list obtained in <1. Fetch Instance Information> includes not only Mastodon instances but also other platforms connected to Mastodon. As a result, errors may arise during fetching toots, because FediLive use [Mastodon REST API](https://docs.joinmastodon.org/) to fetch toots; in such cases, the corresponding instance's "processable" flag in the database will be set to false. If the target instance is busy during crawling, its "processable" flag will be changed to "server_busy". You can check the detailed crawling status using mongosh.


## Logging
All operations and errors are logged to the file specified in the config/config.yaml under the logging section. By default, logs are saved to logs/app.log. You can adjust the logging level and log file path as needed.

Example configuration:
```bash
logging:
  level: "INFO"
  file: "logs/app.log"
```
Logging Levels:
DEBUG: Detailed information, typically of interest only when diagnosing problems.  
INFO: Confirmation that things are working as expected.
WARNING: An indication that something unexpected happened, or indicative of some problem in the near future.  
ERROR: Due to a more serious problem, the software has not been able to perform some function.  
CRITICAL: A very serious error, indicating that the program itself may be unable to continue running.  


## Datasets
We collected approximately two weeks of data using FediLive and have published it on Zenodo. You can download the dataset here: https://zenodo.org/records/14869106

## MongoDB Configure

### 1.Insatll MongoDB
Visit [https://www.mongodb.com/try/download/community](https://www.mongodb.com/try/download/community) to download MongoDB.  
Visit [https://www.mongodb.com/try/download/shell](https://www.mongodb.com/try/download/shell) to download mongosh.  
Then install MongoDB on your server.  

### 2.Modify the MongoDB configuration file
Change net.bindIp to 0.0.0.0  
Change net.port to non-default value (27017).  

### 3.Add an access user
In your terminal, run the following commands:  
```bash
mongosh --port your_port_number
use admin
db.createUser({
  user: "your_username",
  pwd: "your_password",
  roles: [{ role: "root", db: "admin" }]
})
```

### 4.Finished and modify /config/config.yaml
Fill in the corresponding values in config.yaml.  


## Preprocessing Usage Guide

### Data Preparation
Place FediLive crawled JSON files in the data/ directory with the following naming conventions:   

Reply data: reply*.json   
Boost/Favorite data: boostersfavourites*.json   

### Build Interaction Network
```bash
python preprocess/load_network.py --data_dir ./data
```
### Sample output:
```bash
Network loaded with 15420 nodes and 87364 edges
```

### Network Analysis
```bash
from preprocess.measure import calculate_metrics, analyze_cross_instance_statistics

# Calculate global metrics
metrics = calculate_metrics(G)
"""
Graph Metrics:
  Nodes: 15420
  Edges: 87364
  Density: 0.000368
  Average Degree: 5.668
  Clustering Coefficient: 0.142
  Average Shortest Path Length: 4.21
"""
# Cross-instance statistics
cross_stats = analyze_cross_instance_statistics(G)
"""
{
  'Total Edges': 87364,
  'Cross-Instance Edges': 23658,
  'Cross-Instance Edge Ratio': 0.271,
  'Nodes Involved in Cross-Instance Interactions': 8421,
  'Node Interaction Percentage': 54.63%
}
"""
```
### Group Analysis
```bash
# Analyze by instance groups
instance_metrics = analyze_grouped_subgraphs(G, group_type='instance')

# Analyze by edge types
edge_metrics = analyze_grouped_subgraphs(G, group_type='edge_type')
```
