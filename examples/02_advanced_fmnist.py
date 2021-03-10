"""A slightly advanced example of using Cockpit with PyTorch for Fashion-MNIST."""
import time

import torch
from backpack import extend, extensions
from cockpit import Cockpit, CockpitPlotter, quantities
from cockpit.utils import schedules

from examples.utils.utils_examples import cnn, fmnist_data, get_logpath

# Build Fashion-MNIST classifier
fmnist_data = fmnist_data()
model = extend(cnn())  # Use a basic convolutional network
loss_fn = extend(torch.nn.CrossEntropyLoss(reduction="mean"))
indidivual_loss_fn = extend(torch.nn.CrossEntropyLoss(reduction="none"))

# Create SGD Optimizer
opt = torch.optim.SGD(model.parameters(), lr=5e-1)

# Create Cockpit and a plotter
# Customize the tracked quantities and their tracking schedule
quantities = [quantities.Distance(schedules.linear(interval=2))]
cockpit = Cockpit(model.parameters(), quantities=quantities)
plotter = CockpitPlotter()

# Main training loop
max_steps, global_step = 5, 0
for inputs, labels in iter(fmnist_data):
    opt.zero_grad()

    # forward pass
    outputs = model(inputs)
    loss = loss_fn(outputs, labels)
    losses = indidivual_loss_fn(outputs, labels).detach()

    # backward pass
    with cockpit(
        global_step,
        extensions.DiagHessian(),  # Other BackPACK quantities can be computed as well
        info={
            "batch_size": inputs.shape[0],
            "individual_losses": losses,
            "loss": loss,
        },
    ):
        loss.backward(create_graph=cockpit.create_graph(global_step))

    # optimizer step
    opt.step()
    global_step += 1

    print(f"Step: {global_step:5d} | Loss: {loss.item():.4f}")

    plotter.plot(
        cockpit,
        savedir=get_logpath(),
        show_plot=False,
        save_plot=True,
        savename_append=str(global_step),
    )

    if global_step >= max_steps:
        break

# Write Cockpit to json file.
cockpit.write(get_logpath())

# Plot results from file
plotter.plot(get_logpath())
time.sleep(3)