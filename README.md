# AQUATOPE

AQUATOPE is a QoS-and-uncertainty-aware resource manager designed for multi-stage serverless workflows.

## Deployment

The container pool scheduler (`src/container_pool_scheduler`) and container resource manager (`src/container_resource_manager`) are implemented in Python3. The following dependencies need to be installed:  `gevent`, `pytorch`, `botorch`, `gpytorch`. For the container pool scheduler, run `train_lstm_encoder_decoder.py` and `train_prediction_network.py` to train the hybrid model before deployment. The container resource manager updates the resource configurations of registered workflow containers based on `workflow_config` file.

Benchmarks are located in `benchmark` directory. The serverless workflows are created with [OpenWhisk Composer](https://github.com/apache/openwhisk-composer-python). We use [Locust](https://github.com/locustio/locust) as the workload generator to create custom-shaped load based on [Azure Function Dataset](https://github.com/Azure/AzurePublicDataset/blob/master/AzureFunctionsDataset2019.md). The Locust scripts are located in `locust` directory.

By default, OpenWhisk only supports CPU sharing (in proportion to the allocated memory) and pre-defined static container pool configuration. To enable explicit CPU-limit-based resource scheduling, and dynamic adjustment of prewarmed container pool, [#4648](https://github.com/apache/openwhisk/pull/4648) and [#4790](https://github.com/apache/openwhisk/pull/4790) need to be merged.

## Publication

AQUATOPE: QoS-and-Uncertainty-Aware Resource Management for Multi-Stage Serverless Workflows.

```
@inproceedings{10.1145/3567955.3567960,
author = {Zhou, Zhuangzhuang and Zhang, Yanqi and Delimitrou, Christina},
title = {AQUATOPE: QoS-and-Uncertainty-Aware Resource Management for Multi-Stage Serverless Workflows},
year = {2022},
isbn = {9781450399159},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3567955.3567960},
doi = {10.1145/3567955.3567960},
pages = {1–14},
numpages = {14},
keywords = {resource management, machine learning for systems, quality of service, resource allocation, datacenter, function-as-a-service, serverless computing, Cloud computing, resource efficiency},
location = {Vancouver, BC, Canada},
series = {ASPLOS 2023}
}
```
