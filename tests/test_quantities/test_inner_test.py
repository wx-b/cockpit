"""Compare ``InnerTest`` quantity with ``torch.autograd``."""

import pytest
import torch

from cockpit.context import get_batch_size, get_individual_losses
from cockpit.quantities import InnerTest
from cockpit.utils.schedules import linear
from tests.test_quantities.settings import (
    INDEPENDENT_RUNS,
    INDEPENDENT_RUNS_IDS,
    PROBLEMS,
    PROBLEMS_IDS,
)
from tests.test_quantities.utils import autograd_individual_gradients, get_compare_fn


class AutogradInnerTest(InnerTest):
    """``torch.autograd`` implementation of ``InnerTest``."""

    def extensions(self, global_step):
        """Return list of BackPACK extensions required for the computation.

        Args:
            global_step (int): The current iteration number.

        Returns:
            list: (Potentially empty) list with required BackPACK quantities.
        """
        return []

    def create_graph(self, global_step):
        """Return whether access to the forward pass computation graph is needed.

        Args:
            global_step (int): The current iteration number.

        Returns:
            bool: ``True`` if the computation graph shall not be deleted,
                else ``False``.
        """
        return self.should_compute(global_step)

    def _compute(self, global_step, params, batch_loss):
        """Evaluate the inner-product test.

        Args:
            global_step (int): The current iteration number.
            params ([torch.Tensor]): List of torch.Tensors holding the network's
                parameters.
            batch_loss (torch.Tensor): Mini-batch loss from current step.
        """
        losses = get_individual_losses(global_step)
        individual_gradients_flat = autograd_individual_gradients(
            losses, params, concat=True
        )
        grad = torch.cat([p.grad.flatten() for p in params])

        projections = torch.einsum("ni,i->n", individual_gradients_flat, grad)
        grad_norm = grad.norm()

        N_axis = 0
        batch_size = get_batch_size(global_step)

        return (
            (
                1
                / (batch_size * (batch_size - 1))
                * ((projections ** 2).sum(N_axis) / grad_norm ** 4 - batch_size)
            )
            .sqrt()
            .item()
        )


@pytest.mark.parametrize("problem", PROBLEMS, ids=PROBLEMS_IDS)
@pytest.mark.parametrize("independent_runs", INDEPENDENT_RUNS, ids=INDEPENDENT_RUNS_IDS)
def test_inner_test(problem, independent_runs):
    """Compare BackPACK and ``torch.autograd`` implementation of InnerTest.

    Args:
        problem (tests.utils.Problem): Settings for train loop.
        independent_runs (bool): Whether to use to separate runs to compute the
            output of every quantity.
    """
    interval, offset = 1, 2
    schedule = linear(interval, offset=offset)
    rtol, atol = 5e-3, 1e-5

    compare_fn = get_compare_fn(independent_runs)
    compare_fn(problem, (InnerTest, AutogradInnerTest), schedule, rtol=rtol, atol=atol)
