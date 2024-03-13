# AQUATOPE

AQUATOPE is a QoS-and-uncertainty-aware resource manager designed for multi-stage serverless workflows.

## Deployment

The container pool scheduler (`src/container_pool_scheduler`) and container resource manager (`src/container_resource_manager`) are implemented in Python3. The following dependencies need to be installed:  `gevent`, `pytorch`, `botorch`, `gpytorch`. For the container pool scheduler, run `train_lstm_encoder_decoder.py` and `train_prediction_network.py` to train the hybrid model before deployment. The container resource manager updates the resource configurations of registered workflow containers based on `workflow_config` file.

Benchmarks are located in `benchmark` directory. The serverless workflows are created with [OpenWhisk Composer](https://github.com/apache/openwhisk-composer-python). We use [Locust](https://github.com/locustio/locust) as the workload generator to create custom-shaped load based on [Azure Function Dataset](https://github.com/Azure/AzurePublicDataset/blob/master/AzureFunctionsDataset2019.md). The Locust scripts are located in `locust` directory.

By default, OpenWhisk only supports CPU sharing (in proportion to the allocated memory) and pre-defined static container pool configuration. To enable explicit CPU-limit-based resource scheduling, and dynamic adjustment of prewarmed container pool, [#4648](https://github.com/apache/openwhisk/pull/4648) and [#4790](https://github.com/apache/openwhisk/pull/4790) need to be merged.

Both container pool scheduler and container resource manager utilize `owlib` to interact with OpenWhisk framework to adjust the container pool and function resource configurations accordingly.

### Container Pool Scheduler

Before training the prediction model, we first construct and train the LSTM encoder-decoder to extract latent features from a serverless trace. The model `lstm_encoder_decoder` will be saved in `model_artifacts` directory.

```bash
python train_lstm_encoder_decoder.py \
    --n_input_steps <default=48> \
    --n_output_steps <default=12> \
    --num_days <number of days in the training dataset, default=7> \
    --num_epochs <default=128> \
    --batch_size <default=128> \
    --learning_rate <default=1e-4> \
    --variational_dropout_p <default=0.25> \
    --trace_id <Function ID in Azure Function Dataset> \
    --dataset_dir <Directory of Azure Function Dataset>
```

Then, we train a prediction network to forecast the number of active
containers in the next time window. The model `predict` will be saved in `model_artifacts` directory.

```bash
python train_lstm_encoder_decoder.py \
    --n_input_steps <default=48> \
    --n_output_steps <default=1> \
    --num_days <number of days in the training dataset, default=7> \
    --num_epochs <default=128> \
    --batch_size <default=128> \
    --learning_rate <default=1e-3> \
    --dropout_p <default=0.25> \
    --trace_id <Function ID in Azure Function Dataset> \
    --dataset_dir <Directory of Azure Function Dataset>
```

Finally, the `container_pool_scheduler` uses the pretrained LSTM encoder-decoder and prediction network to perform full inference and adjust the number of containers in the container pool accordingly.

```bash
python scheduler.py \
    --n_input_steps <default=48> \
    --n_output_steps <default=1> \ 
    --workflow_config <workflow configuration file>
```

### Container Resource Manager

Deploy the container resource manager and optimize the resource configurations of target workflows.

```bash
python manager.py \
    --n_init <default=10> \
    --n_batch <default=20> \
    --mc_samples <default=32> \
    --batch_size <default=3> \
    --num_restarts <default=10> \
    --raw_samples <default=32> \
    --infeasible_cost <default=0> \
    --anomaly_detection <default=true> \
    --confidence <default=0.95> \
    --workflow_config <workflow configuration file>
```

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
