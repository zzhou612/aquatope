import gevent  # isort:skip
from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip
import argparse
import json
import logging
import os
import signal
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import scipy
import torch
from botorch import fit_gpytorch_model
from botorch.acquisition.monte_carlo import (
    qExpectedImprovement,
    qNoisyExpectedImprovement,
)
from botorch.acquisition.objective import ConstrainedMCObjective
from botorch.exceptions import BadInitialCandidatesWarning
from botorch.models import FixedNoiseGP, ModelListGP, SingleTaskGP
from botorch.optim import optimize_acqf
from botorch.sampling.samplers import SobolQMCNormalSampler
from botorch.test_functions import Hartmann
from gpytorch.mlls.sum_marginal_log_likelihood import SumMarginalLogLikelihood

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(PROJECT_DIR))
sys.path.append(str(SCHED_DIR))

from bo_utils import (
    from_x_to_resource_config,
    sample_cost,
    sample_cost_parallel,
    sample_duration,
    sample_duration_parallel,
)
from manager import WORKFLOW_CONFIG

from utils.config import NUM_RESOURCES

device = torch.device("cuda:3" if torch.cuda.is_available() else "cpu")
dtype = torch.double
warnings.filterwarnings("ignore", category=BadInitialCandidatesWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)
neg_hartmann6 = Hartmann(negate=True)


def obj_function(X):
    # return neg_hartmann6(X)
    return sample_cost_parallel(X=X) * (-1)


def outcome_constraint(X):
    """Feasible if less than or equal to zero."""
    # return X.sum(dim=-1) - 3
    return sample_duration_parallel(X=X) - WORKFLOW_CONFIG["qos"]


def weighted_obj(X):
    """Feasibility weighted objective; -INF if not feasible."""
    # return neg_hartmann6(X) * (outcome_constraint(X) <= 0).type_as(X)
    return obj_function(X) + ((outcome_constraint(X) > 0) * (-100)).type_as(X)


def obj_callable(Z):
    return Z[..., 0]


def constraint_callable(Z):
    return Z[..., 1]


def generate_initial_data(n=10):
    # generate training data
    x_dim = len(WORKFLOW_CONFIG["functions"]) * NUM_RESOURCES
    train_x = torch.rand(n, x_dim, device=device, dtype=dtype)
    train_obj = obj_function(train_x).unsqueeze(-1)  # add output dimension
    train_con = outcome_constraint(train_x).unsqueeze(-1)  # add output dimension
    best_observed_value = weighted_obj(train_x).max().item()
    return train_x, train_obj, train_con, best_observed_value


def initialize_model(train_x, train_obj, train_con, state_dict=None):
    # define models for objective and constraint
    model_obj = SingleTaskGP(train_x, train_obj).to(train_x)
    model_con = SingleTaskGP(train_x, train_con).to(train_x)
    # combine into a multi-output GP model
    model = ModelListGP(model_obj, model_con)
    mll = SumMarginalLogLikelihood(model.likelihood, model)
    # load state dict if it is passed
    if state_dict is not None:
        model.load_state_dict(state_dict)
    return mll, model


def optimize_acqf_and_get_observation(
    acq_func, bounds, batch_size, num_restarts, raw_samples
):
    """Optimizes the acquisition function, and returns a new candidate and a noisy observation."""
    # optimize
    candidates, _ = optimize_acqf(
        acq_function=acq_func,
        bounds=bounds,
        q=batch_size,
        num_restarts=num_restarts,
        raw_samples=raw_samples,  # used for intialization heuristic
        options={"batch_limit": 5, "maxiter": 200},
    )
    # observe new values
    new_x = candidates.detach()
    new_obj = obj_function(new_x).unsqueeze(-1)  # add output dimension
    new_con = outcome_constraint(new_x).unsqueeze(-1)  # add output dimension
    return new_x, new_obj, new_con


def update_random_observations(best_random, batch_size):
    """Simulates a random policy by taking a the current list of best values observed randomly,
    drawing a new random point, observing its value, and updating the list.
    """
    x_dim = len(WORKFLOW_CONFIG["functions"]) * NUM_RESOURCES
    rand_x = torch.rand(batch_size, x_dim)
    next_random_best = weighted_obj(rand_x).max().item()
    best_random.append(max(best_random[-1], next_random_best))
    return best_random


def bo_loop(
    n_init=10,
    n_batch=20,
    mc_samples=32,
    batch_size=3,
    num_restarts=10,
    raw_samples=32,
    infeasible_cost=0,
    anomaly_detection=True,
    confidence=0.95,
    verbose=True,
):
    n_stages = len(WORKFLOW_CONFIG["functions"])
    bounds = torch.tensor(
        [[0.0] * NUM_RESOURCES * n_stages, [1.0] * NUM_RESOURCES * n_stages],
        device=device,
        dtype=dtype,
    )

    best_observed_nei, best_random = [], []

    # call helper functions to generate initial training data and initialize model
    (
        train_x_nei,
        train_obj_nei,
        train_con_nei,
        best_observed_value,
    ) = generate_initial_data(n=n_init)

    best_observed_value_nei = best_observed_value
    best_x = None
    mll_nei, model_nei = initialize_model(train_x_nei, train_obj_nei, train_con_nei)

    best_observed_nei.append(best_observed_value_nei)
    best_random.append(best_observed_value)

    # run N_BATCH rounds of BayesOpt after the initial random batch
    for iteration in range(1, n_batch + 1):
        t0 = time.monotonic()

        # fit the models
        fit_gpytorch_model(mll_nei)

        # define the qEI and qNEI acquisition modules using a QMC sampler
        qmc_sampler = SobolQMCNormalSampler(num_samples=mc_samples)

        # define a feasibility-weighted objective for optimization
        constrained_obj = ConstrainedMCObjective(
            objective=obj_callable,
            constraints=[constraint_callable],
            infeasible_cost=infeasible_cost,
        )

        qNEI = qNoisyExpectedImprovement(
            model=model_nei,
            X_baseline=train_x_nei,
            sampler=qmc_sampler,
            objective=constrained_obj,
        )

        # optimize and get new observation
        new_x_nei, new_obj_nei, new_con_nei = optimize_acqf_and_get_observation(
            acq_func=qNEI,
            bounds=bounds,
            batch_size=batch_size,
            num_restarts=num_restarts,
            raw_samples=raw_samples,
        )

        # update training points
        train_x_nei = torch.cat([train_x_nei, new_x_nei])
        train_obj_nei = torch.cat([train_obj_nei, new_obj_nei])
        train_con_nei = torch.cat([train_con_nei, new_con_nei])

        # remove outliers
        if anomaly_detection:
            non_outliers_indices = []
            for idx in range(len(train_x_nei)):
                subset_train_x = torch.cat([train_x_nei[0:idx], train_x_nei[idx + 1 :]])
                subset_train_obj = torch.cat(
                    [train_obj_nei[0:idx], train_obj_nei[idx + 1 :]]
                )
                diagnostic_model = SingleTaskGP(subset_train_x, subset_train_obj).to(
                    subset_train_x
                )
                posterior = diagnostic_model.posterior(
                    torch.unsqueeze(train_x_nei[idx], 0)
                )
                mean = posterior.mean.squeeze().item()
                var = posterior.variance.squeeze().item()
                ci = scipy.stats.norm.interval(confidence, loc=mean, scale=var)
                obj = weighted_obj(torch.unsqueeze(train_x_nei[idx], 0)).item()
                if ci[0] < obj and obj < ci[1]:
                    non_outliers_indices.append(idx)
            train_x_nei = train_x_nei[non_outliers_indices]
            train_obj_nei = train_obj_nei[non_outliers_indices]
            train_con_nei = train_con_nei[non_outliers_indices]

        # update progress
        best_random = update_random_observations(best_random, batch_size)
        best_value_nei = weighted_obj(train_x_nei).max().item()
        best_value_idx = weighted_obj(train_x_nei).argmax().item()
        best_x = train_x_nei[best_value_idx]
        best_observed_nei.append(best_value_nei)

        # reinitialize the models so they are ready for fitting on next iteration
        # use the current state dict to speed up fitting
        mll_nei, model_nei = initialize_model(
            train_x_nei,
            train_obj_nei,
            train_con_nei,
            model_nei.state_dict(),
        )

        t1 = time.monotonic()

        if verbose:
            print(
                f"\nBatch {iteration:>2}: best_value (random, qNEI) = "
                f"({max(best_random):>4.2f}, {best_value_nei:>4.2f}), "
                f"time = {t1-t0:>4.2f}.",
                end="",
            )
        else:
            print(".", end="")
    best_cost = -1 * best_value_nei
    resource_config = from_x_to_resource_config(x=best_x)
    return best_cost, resource_config
