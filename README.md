

# FediLive

FediLive is a data collection tool designed to quickly fetch **platform-wide public activities** from Mastodon instances during a user-defined time period for downstream analysis. A dataset collected via FediLive over a period of approximately two weeks has been published on [Zenodo](https://zenodo.org/records/14869106).

It currently provides **two running modes** via two seperated branches:

- **A. Single version**: a lightweight version without MongoDB, suitable for single-machine or simpler crawling tasks.
- **B. Multi version**: a distributed version with MongoDB support, suitable for multi-machine parallel crawling, task coordination, and large-scale snapshot collection.

---

[![License][license-image]][license-url] ![Version][version-image] ![Python][python-image]

[license-image]: https://img.shields.io/github/license/FDUDataNET/FediLive
[license-url]: https://github.com/FDUDataNET/FediLive
[version-image]: https://img.shields.io/badge/version-1.0.0-brightgreen
[python-image]: https://img.shields.io/badge/python-3.8--3.13-blue

## Citation

FediLive is developed and maintained by the [Big Data and Networking (DataNET) Group](https://fudan-datanet.mysxl.cn/) at Fudan University.

If you use FediLive or the example dataset in your research, please cite our paper:

```bibtex
@inproceedings{Min2025FediLive,
  author    = {Min, Shaojie and Wang, Shaobin and Luo, Yaxiao and Gao, Min and Gong, Qingyuan and Xiao, Yu and Chen, Yang},
  title     = {{FediLive: A Framework for Collecting and Preprocessing Snapshots of Decentralized Online Social Networks}},
  year      = {2025},
  booktitle = {Companion Proceedings of the ACM on Web Conference 2025},
  series    = {WWW '25},
  publisher = {Association for Computing Machinery},
  address   = {New York, NY, USA},
  pages     = {765--768},
  doi       = {10.1145/3701716.3715298},
  url       = {https://doi.org/10.1145/3701716.3715298}
}
```

## Overview

FediLive supports collecting the following types of public Mastodon data:

- **Posts and replies**
- **Reblogs and favourites**
- **Contexts** of posts/conversations
- **User interaction networks** for downstream preprocessing and analysis

### Which version should you choose?

#### Use the **Single version** if:

- you intend to run FediLive on a single machine,
- you do not intend to deploy MongoDB,
- your crawling task is relatively small or you prefer a lightweight setup.

#### Use the **Multi version** if:

- you have the ability to run FediLive on multiple machines in parallel,
- you need distributed task coordination,
- you intend to manage large-scale crawling more efficiently,
- you need centralized storage of instance status and crawl progress.

## Development Environment

FediLive has been tested on Ubuntu 20.04 LTS.

### Recommended environment

- **OS**: Ubuntu 20.04 LTS (64-bit)
- **Memory**: 8GB RAM or above
- **Storage**: 20GB available space or above
- **Python**: 3.8–3.13

### Additional requirement for Multi version

- **MongoDB**: 5.0.30 recommended

## Repository Branches

FediLive currently has two branches:

- **A. Single version**: `Single`
- **B. Multi version**: `Multi`

Clone the branch that matches your use case.

### A. Clone Single version

```bash
git clone -b Single git@github.com:FDUDataNET/FediLive.git
cd FediLive
```

### B. Clone Multi version

```bash
git clone -b Multi git@github.com:FDUDataNET/FediLive.git
cd FediLive
```

## Installation

The following installation steps are shared by both versions.

### 1. Create and activate a virtual environment (optional)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

The configuration process differs depending on whether you use the **A. Single version** or the **B. Multi version**.

---

## A. Single version Configuration

The Single version does **not** require MongoDB.

Edit `config/config.yaml` as follows:

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

### Configuration fields

#### API

- `instance_token`: token for retrieving the list of Mastodon instances from `instances.social`  
  Apply at: https://instances.social/api/token

- `livefeeds_token`: token used to collect posts from Mastodon instances  
  Tokens can be requested according to the Mastodon API documentation:  
  https://docs.joinmastodon.org/

- `email`: your contact email

#### Paths

- `instances_list`: file path used to save the retrieved list of instances

#### Logging

- `level`: logging level, such as `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`
- `file`: log file path

---

## B. Multi version Configuration

The Multi version is designed for **distributed parallel crawling across multiple machines**.

### Architecture

In the Multi version:

- one machine should be selected as the **central node**
- the central node stores instance information, crawling ranges, and coordinates crawling tasks
- the other machines serve as **worker nodes** to crawl data from instances
- each machine should have MongoDB installed
- in `config.yaml`:
  - `mongodb_central` should point to the central node database
  - `mongodb_local` should point to the current machine’s local database

Edit `config/config.yaml` like this:

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

whitelist:
  - "mastodon.social"
  - "mstdn.social"
```

### Configuration fields

#### MongoDB

- `mongodb_central`: connection information for the **central node** database
- `mongodb_local`: connection information for the **local machine** database

#### API

- `central_token`: token for collecting the list of Mastodon instances from `instances.social`  
  Apply at: https://instances.social/api/token
- `email`: your contact email

#### Paths

- `instances_list`: file path used to save the retrieved list of instances
- `token_list`: file containing Mastodon API tokens, one token per line

#### Logging

- `level`: logging level
- `file`: log file path

#### Whitelist

If the livefeeds time range is large, some large instances that are normally crawlable, such as `mastodon.social`, may occasionally encounter connection errors due to heavy request volume and may be blacklisted by `livefeeds_worker.py`.

You can add known stable large instances to the `whitelist` so they will **not** be blacklisted automatically.

## API Tokens

### A. Single version

You need:

- one `instance_token`
- one `livefeeds_token`

### B. Multi version

Populate `tokens/token_list.txt` with Mastodon API tokens, **one token per line**.

Make sure the number of tokens is **greater than the number of parallel processes** you plan to run.

These tokens are used to collect posts from various Mastodon instances.

## Usage

The usage differs slightly between the two versions. Shared steps are grouped together below, and different commands are shown separately.

### 1. Fetch Instance Information

This step retrieves the list of Mastodon instances.

#### A. Single version

```bash
python -m fetcher.masto_list_fetcher
```

#### B. Multi version

Run this on the **central node**:

```bash
python ./fetcher/masto_list_fetcher.py
```

### 2. Fetch Posts / Livefeeds

This step collects public posts during a specified time period.

#### A. Single version

You can run this on one or multiple machines in parallel.

```bash
python -m fetcher.livefeeds_worker --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
```

Parameters:

- `--processnum`: number of parallel processes
- `--start`: start time, format `YYYY-MM-DD HH:MM:SS`
- `--end`: end time, format `YYYY-MM-DD HH:MM:SS`

#### B. Multi version

Run this on multiple machines in parallel:

```bash
python ./fetcher/livefeeds_worker.py --id 0 --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
```

Parameters:

- `--id`: worker ID, starting from 0, used to select different API tokens
- `--processnum`: number of parallel processes on each host
- `--start`: start time, format `YYYY-MM-DD HH:MM:SS` (**UTC+0**)
- `--end`: end time, format `YYYY-MM-DD HH:MM:SS` (**UTC+0**)

### 3. Fetch Reblogs and Favourites

This step collects users who reblogged or favourited posts.

#### A. Single version

```bash
python -m fetcher.reblog_favourite --processnum 3
```

Parameters:

- `--processnum`: number of parallel processes

#### B. Multi version

```bash
python ./fetcher/reblog_favourite.py --processnum 3 --id 0
```

Parameters:

- `--processnum`: number of parallel processes
- `--id`: worker ID used to select different API tokens

### 4. Fetch Contexts

A context refers to the complete reply conversation of a post.

#### A. Single version

This feature is not documented in the original Single README.

#### B. Multi version

Run this on multiple machines in parallel:

```bash
python ./fetcher/context.py --processnum 3 --id 0
```

Parameters:

- `--processnum`: number of parallel processes
- `--id`: worker ID used to select different API tokens

### 5. Restart / Reset an Experiment

This operation is documented only for the Multi version.

#### B. Multi version

Run this on **all machines** to remove existing livefeeds, reblogs, favourites, and related crawl state stored in MongoDB.

**Make sure to back up your data before running this command.**

```bash
python ./fetcher/reboot.py
```

### 6. Reactivate Whitelisted Instances

If some large but normally crawlable instances were temporarily marked unavailable during crawling, you can reactivate them using the whitelist.

#### B. Multi version

```bash
python ./fetcher/reactivate_whitelist.py
```

## Notes

### General notes

- FediLive uses the [Mastodon REST API](https://docs.joinmastodon.org/) for data collection.
- Some errors may occur during crawling due to network instability, busy servers, heterogeneous instance behavior, or rate limits.
- These errors are generally handled within the code.

### Multi version-specific notes

The instance list retrieved in the first step may include not only Mastodon instances but also other platforms connected in the Fediverse ecosystem. As a result:

- some instances may not behave fully like Mastodon
- some requests may fail when using Mastodon REST API endpoints
- in these cases, the corresponding instance’s `processable` flag in MongoDB may be set to `false`
- if an instance is temporarily overloaded, its `processable` flag may be set to `server_busy`

You can inspect detailed crawl status using `mongosh`.

## Logging

All operations and errors are logged to the file specified in `config/config.yaml`.

Example configuration:

```yaml
logging:
  level: "INFO"
  file: "logs/app.log"
```

### Logging levels

- `DEBUG`: detailed information, mainly for diagnosing problems
- `INFO`: confirmation that things are working as expected
- `WARNING`: an indication that something unexpected happened, or may happen soon
- `ERROR`: a more serious problem that prevents part of the program from working correctly
- `CRITICAL`: a very serious error indicating that the program may not be able to continue


## MongoDB Setup Guide

This section is required **only for the Multi version**.

### 1. Install MongoDB

Visit the following pages to download and install MongoDB and mongosh:

- MongoDB Community Server:  
  https://www.mongodb.com/try/download/community
- MongoDB Shell:  
  https://www.mongodb.com/try/download/shell

Install MongoDB on each server that participates in crawling.

### 2. Modify the MongoDB configuration file

In your MongoDB config file (for example, `mongod.conf`), modify:

- `net.bindIp` to `0.0.0.0`
- `net.port` to a non-default value if needed

This allows worker machines to access the central node database.

For security reasons, it is strongly recommended to:

- avoid exposing the default port directly
- configure username/password authentication
- restrict network access where possible

### 3. Add an access user

Run the following commands:

```bash
mongosh --port your_port_number
use admin
db.createUser({
  user: "your_username",
  pwd: "your_password",
  roles: [{ role: "root", db: "admin" }]
})
```

### 4. Fill in `config/config.yaml`

After MongoDB is configured, fill the corresponding connection information into:

- `mongodb_central`
- `mongodb_local`

## Preprocessing Usage Guide

This section is mainly documented for the Multi version and can be used after data collection.

### Data Preparation

Place FediLive crawled JSON files in the `data/` directory using the following naming conventions:

- Reply data: `reply*.json`
- Boost/Favourite data: `boostersfavourites*.json`

### Build Interaction Network

```bash
python preprocess/load_network.py --data_dir ./data
```

### Sample output

```bash
Network loaded with 15420 nodes and 87364 edges
```

### Network Analysis

```python
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

```python
# Analyze by instance groups
instance_metrics = analyze_grouped_subgraphs(G, group_type='instance')

# Analyze by edge types
edge_metrics = analyze_grouped_subgraphs(G, group_type='edge_type')
```

## Recommended Quick Start

### A. Quick start for Single version

```bash
git clone -b Single git@github.com:FDUDataNET/FediLive.git
cd FediLive
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# edit config/config.yaml
python -m fetcher.masto_list_fetcher
python -m fetcher.livefeeds_worker --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
python -m fetcher.reblog_favourite --processnum 3
```

### B. Quick start for Multi version

```bash
git clone -b Multi git@github.com:FDUDataNET/FediLive.git
cd FediLive
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# install and configure MongoDB on all machines
# edit config/config.yaml
# fill tokens/token_list.txt
python ./fetcher/masto_list_fetcher.py
python ./fetcher/livefeeds_worker.py --id 0 --processnum 2 --start "2024-01-01 00:00:00" --end "2024-01-02 00:00:00"
python ./fetcher/reblog_favourite.py --processnum 3 --id 0
python ./fetcher/context.py --processnum 3 --id 0
```

## Version Differences at a Glance

| Feature | A. Single version | B. Multi version |
|---|---|---|
| MongoDB required | No | Yes |
| Single-machine crawling | Yes | Yes |
| Multi-machine distributed crawling | Limited / manual | Yes |
| Central task coordination | No | Yes |
| Token list file | No | Yes |
| Worker ID (`--id`) | No | Yes |
| Context fetching documented | No | Yes |
| Experiment reboot documented | No | Yes |
| Whitelist reactivation | No | Yes |
| Preprocessing guide included | Not documented | Yes |
