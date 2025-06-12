FediLive
==================

FediLive is a data collection tool designed to quickly fetch *user interactions* from all Mastodon instances during a user-defined time period for downstream analysis.

___________________________________________________________________________

[![License][license-image]][license-url] ![Version][version-image] ![Python][python-image]

[license-image]:https://img.shields.io/github/license/FDUDataNET/FediLive
[license-url]: https://github.com/FDUDataNET/FediLive/blob/Single/LICENSE
[version-image]: https://img.shields.io/badge/version-1.0.0-brightgreen
[python-image]: https://img.shields.io/badge/python-3.7--3.13-blue


## Citation
FediLive is developed and maintained by the [Big Data and Networking (DataNET) Group](https://fudan-datanet.mysxl.cn/) at Fudan University.

If you use FediLive in your research, please cite our paper:
  ```bash
  @inproceedings{Min2025FediLive,
    author    = {Min, Shaojie and Wang, Shaobin and Luo, Yaxiao and Gao, Min and Gong, Qingyuan and Xiao, Yu and Chen, Yang},
    title     = {{FediLive: A Framework for Collecting and Preprocessing Snapshots of Decentralized Online Social Networks}},
    year      = {2025},
    booktitle = {Companion Proceedings of the ACM on Web Conference 2025},
    series    = {WWW '25},
    publisher = {Association for Computing Machinery},
    address   = {New York, NY, USA},
    pages     = {765–768},
    doi       = {10.1145/3701716.3715298},
    url       = {https://doi.org/10.1145/3701716.3715298}
  }
  ```



## Installation

1. **Clone the Repository**

   ```bash
   git clone -b Single git@github.com:FDUDataNET/FediLive.git
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

4. **Configure tokens and Logging**

   Edit the `config/config.yaml` file with your API tokens, file save paths and logging preferences.

   ```yaml
   api:
     instance_token: "your_instance_api_token"
     livefeeds_token: "your_mastodon_api_token"
     email: "your_email@example.com"
   
   paths:
     instances_list: "instances_list.txt"
   
   logging:
     level: "INFO"
     file: "logs/app.log"
   ```

   - **API Tokens**:
    - `instance_token`: Apply for instance_token at https://instances.social/api/token. This token will be used to collect the list of Mastodon instances. For details, please see https://instances.social/.
    - `livefeeds_token`: This token will be used to collect toots from various Mastodon instances. Tokens can be requested following the guidelines at https://docs.joinmastodon.org/.
  
   - **Paths**：file save paths
   - `instances_list`: Save the retrieved list of instances.

   - **Logging Configuration**:
     - `level`: Sets the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
     - `file`: Path to the log file where logs will be stored.


## Usage

### 1. Fetch Instance Information

Run this on the central node to fetch all Mastodon instances and store their information in MongoDB.

```bash
python -m fetcher.masto_list_fetcher
```

### 2. Fetch Tweets

You can run this on multiple machines in parallel.

```bash
python -m fetcher.livefeeds_worker --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
```

Parameters:

--processnum: Number of parallel processes.  
--start: Start time for fetching tweets (format: YYYY-MM-DD HH:MM:SS).  
--end: End time for fetching tweets (format: YYYY-MM-DD HH:MM:SS).  

### 3. Fetch Reblogs and Favourites

```bash
python -m fetcher.reblog_favourite --processnum 3
```

Parameters:

--processnum: Number of parallel processes.  

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

