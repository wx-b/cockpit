"""This is an extension of the CockpitTracker class.

It contains all the iter_tracking functions, defining the computation needed for the
logged quantity.
These functions are then used in either track_before, track_after or track_epoch
of the CockpitTracker class.

self is a CockpitTracker."""

from math import sqrt

import numpy as np
from scipy.sparse.linalg import eigsh

from .utils_ev import HVPLinearOperator
from .utils_tracking import (
    _exact_variance,
    _fit_quadratic,
    _get_alpha,
    _layerwise_dot_product,
)


def track_f(self, batch_loss, point):
    """Tracks the function value at the (start or end) point.

    Args:
        batch_loss (float): Average loss over a batch
        point (str): Either "0" or "1" to signify that we are iter_tracking the
            starting or end point of an iteration.
    """
    self.iter_tracking["f" + point].append(batch_loss.item())


def track_var_f(self, batch_losses, point):
    """Tracks the variance of the function value at the (start or end) point.

    Args:
        batch_losses (list): List of individual losses in a batch.
        point (str): Either "0" or "1" to signify that we are iter_tracking the
            starting or end point of an iteration.
    """
    self.iter_tracking["var_f" + point].append(batch_losses.var().item())


def track_df(self, point):
    """Tracks the projected gradient (onto the search direction) at the
    (start or end) point.

    Args:
        point (str): Either "0" or "1" to signify that we are iter_tracking the
            starting or end point of an iteration.
    """
    self.iter_tracking["df" + point].append(
        _layerwise_dot_product(
            self.search_dir,
            [p.grad.data for p in self.parameters() if p.requires_grad],
        )
    )


def track_var_df(self, point):
    """Tracks the variance of the projected gradient (onto the search direction)
    at the (start or end) point.

    Args:
        point (str): Either "0" or "1" to signify that we are iter_tracking the
            starting or end point of an iteration.
    """
    self.iter_tracking["var_df" + point].append(
        _exact_variance(
            [p.grad_batch.data for p in self.parameters() if p.requires_grad],
            self.search_dir,
        )
    )


def track_grad_norms(self):
    """Tracks the L2 norm of the current gradient."""
    self.iter_tracking["grad_norms"].append(
        [p.grad.data.norm(2).item() for p in self.parameters() if p.requires_grad]
    )


def track_dtravel(self, learning_rate):
    """Tracks the distance traveled in each iteration.

    It is very important that this function is computed AFTER iter_tracking
    grad_norms.
    TODO This definition only applies to SGD without Momentum.

    Args:
        learning_rate (float): Learning rate used in this step.
    """
    self.iter_tracking["dtravel"].append(
        [el * learning_rate for el in self.iter_tracking["grad_norms"][-1]]
    )


def track_trace(self):
    """Tracks the trace of the Hessian."""
    self.iter_tracking["trace"].append(
        [p.diag_h.sum().item() for p in self.parameters() if p.requires_grad]
    )


def track_ev(self, batch_loss):
    """Track the max (and possibly min) eigenvalue of the Hessian.

    Args:
        batch_loss (float): Average loss over a batch
    """
    HVP = HVPLinearOperator(
        batch_loss,
        list(self.parameters()),
        grad_params=[p.grad for p in self.parameters()],
    )
    eigvals = eigsh(HVP, k=1, which="LA", return_eigenvectors=False)

    self.iter_tracking["max_ev"].append(np.float64(eigvals))


def track_d2init(self):
    """Tracks the L2 distance of the current parameters to their init."""
    self.iter_tracking["d2init"].append(
        [
            (init - p).norm(2).item()
            for init, p in zip(self.p_init, self.parameters())
            if p.requires_grad
        ]
    )


def track_alpha(self):
    """Tracks the effective relative step size.

    It is measured as were we "step" on the local 1D quadratic approximation.
    An alpha of 0 means that the step was to the minimum of the parabola.
    An alpha of -1 means we stayed at the same position of the quadratic.
    An alpha of 1 means we stepped on the other side of the quadratic.

    If we cannot make a quadratic fit (most likely due to variances of 0) alpha
    is set to None (via the `_get_alpha` function).
    """
    # We need to find the size of the step taken,
    # since dtravel can be a list, we need to aggregate it
    if type(self.iter_tracking["dtravel"][-1]) is list:
        t = sqrt(sum(t * t for t in self.iter_tracking["dtravel"][-1]))
    else:
        t = self.iter_tracking["dtravel"][-1]

    # Fit a noise-informed quadratic approximation to the obersvation of
    # function value and projected gradient plus their variance.
    mu = _fit_quadratic(
        t,
        [self.iter_tracking["f0"][-1], self.iter_tracking["f1"][-1]],
        [sum(self.iter_tracking["df0"][-1]), sum(self.iter_tracking["df1"][-1]),],
        [self.iter_tracking["var_f0"][-1], self.iter_tracking["var_f1"][-1]],
        [
            sum(self.iter_tracking["var_df0"][-1]),
            sum(self.iter_tracking["var_df1"][-1]),
        ],
    )

    # Get the relative (or local) step size
    self.iter_tracking["alpha"].append(_get_alpha(mu, t))
