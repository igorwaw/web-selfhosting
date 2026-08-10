---
title: "Kubeflow, part 2: running experiments"
date: 2026-08-03T09:00:00
draft: true
tags: ["ai", "services"]
---

[Part 1](/homelab/kubeflow-1/) got as far as proving the plumbing works: a notebook server that can ask Kubernetes for a GPU and get one. That's a milestone for the install, but it's not actually doing anything - `nvidia-smi` printing the card's usual output from inside a pod Kubeflow scheduled is the platform saying "yes", not a workload. This part is about spending that "yes" on a few things Kubeflow is actually meant for, on hardware that's nowhere near what its own docs assume.

## What this covers

- **Training something real** in a notebook, instead of just checking the GPU is there
- **Kubeflow Volumes** - whether the workspace actually survives a notebook restarting
- **TensorBoard**, wired up through the dashboard rather than run by hand
- **Installing Katib after all** - the piece I skipped in part 1, and what a hyperparameter search looks like with exactly one GPU to run it on

## Training something real

Same starting point as part 1: *Notebooks → New Notebook* from the dashboard, GPU count set to 1. This time I picked the PyTorch + CUDA image from the built-in dropdown instead of the plain CPU one, which saves reinstalling half of PyTorch's dependency tree by hand once the notebook's up.

Inside, I ran the same [LoRA fine-tuning](/homelab/lora-finetuning/) script I'd used outside Kubeflow, unchanged. That's the point of the exercise: if the notebook pod is a normal enough container that a script written against plain Docker runs without modification, the Kubeflow layer underneath is doing its job invisibly.

```python
import torch
print(torch.cuda.is_available(), torch.cuda.get_device_name(0))
```

confirmed the same card the CDI setup exposed in [part 2 of the GPU guide](/homelab/gpu-guide-2/), and the training loop ran at the same speed as running it directly in a Docker container on Serenity - no measurable Kubernetes tax on GPU-bound work, which is what I'd expect once scheduling is done and the container's just running.

## Does the workspace survive

Kubeflow's "New Notebook" flow creates a PVC-backed workspace volume by default, mounted at `/home/jovyan`, separate from the notebook pod itself. The pod is disposable - it can be deleted and recreated by the controller - the volume isn't meant to be. Worth actually checking rather than trusting the docs:

```bash
kubectl get pvc -n kubeflow-user-example-com
kubectl delete pod -n kubeflow-user-example-com <notebook-pod-name>
```

The notebook controller noticed the pod was gone and started a replacement within a few seconds - same PVC reattached, same files in `/home/jovyan`, training checkpoint and all. Unsurprising if you already trust Kubernetes' pod/PVC separation, but worth the thirty seconds it takes to prove rather than assume, especially on a cluster this new to me.

## Wiring up TensorBoard

Logging a training run for TensorBoard from the notebook is the same one-liner as anywhere else:

```python
from torch.utils.tensorboard import SummaryWriter
writer = SummaryWriter("/home/jovyan/logs/run1")
```

Normally that means `pip install tensorboard`, running it by hand, and a `port-forward` to see it. Kubeflow's dashboard has a *Tensorboards* entry that skips that: point it at the log directory (the same PVC as the notebook, so no copying files around) and it creates a `Tensorboard` custom resource that runs the viewer as its own pod behind the same Istio gateway I already had tunnelled from part 1. One less `port-forward` to keep track of, which sounds trivial until you've got three of them open in different terminals and forgotten which is which.

## Installing Katib after all

Part 1 left Katib out on the grounds that hyperparameter tuning solves a problem - many parallel trials competing for a shared GPU budget - that doesn't exist with one card and one person. Still true. But Katib's actual job is running an `Experiment` CRD that spawns and manages trial Jobs; with a single GPU, "parallel" search just degrades to trials queued one after another, which is a perfectly fine way to learn what the CRD does even if it wastes the tool's actual selling point.

Back into `example/kustomization.yaml`, uncommenting the `katib` entry I'd disabled in part 1, then the same retry loop from before:

```bash
while ! kustomize build example | kubectl apply --server-side --force-conflicts -f -; do
  echo "Retrying..."
  sleep 20
done
```

A minimal `Experiment` - random search over two hyperparameters for a training script, one trial at a time:

```yaml
apiVersion: kubeflow.org/v1beta1
kind: Experiment
metadata:
  name: lora-lr-search
  namespace: kubeflow-user-example-com
spec:
  objective:
    type: minimize
    goal: 0.05
    objectiveMetricName: loss
  algorithm:
    algorithmName: random
  parallelTrialCount: 1
  maxTrialCount: 6
  maxFailedTrialCount: 2
  parameters:
    - name: lr
      parameterType: double
      feasibleSpace:
        min: "0.00005"
        max: "0.001"
    - name: rank
      parameterType: int
      feasibleSpace:
        min: "4"
        max: "16"
  trialTemplate:
    primaryContainerName: training-container
    trialParameters:
      - name: learningRate
        reference: lr
      - name: loraRank
        reference: rank
    trialSpec:
      apiVersion: batch/v1
      kind: Job
      spec:
        template:
          spec:
            containers:
              - name: training-container
                image: my-lora-trainer:latest
                command:
                  - "python3"
                  - "train.py"
                  - "--lr=${trialParameters.learningRate}"
                  - "--rank=${trialParameters.loraRank}"
            restartPolicy: Never
```

`parallelTrialCount: 1` is doing the honest thing given the hardware - Katib will happily accept a higher number and then just leave trials pending until the GPU frees up, which is a more confusing way to arrive at the same sequential result. `kubectl apply -f` that, and the Experiment's own controller takes over: spawning a trial Job, waiting for it to report a metric, killing it, spawning the next with different parameters. Watching it in the dashboard's *Experiments (AutoML)* tab beats `kubectl get jobs -w`, if only because it draws the objective metric per trial as it goes rather than leaving that to be pieced together from logs.

Six trials, run one after another, is not a hyperparameter search in any sense that would impress someone with a GPU budget. It is, however, the CRD, the controller and the trial-suggestion loop actually working end to end - which was the entire point of installing it in the first place.

## What this leaves out

Pipelines and KServe are still uninstalled, and I'm still not convinced either earns its keep on one machine - Pipelines orchestrates multi-step workflows I don't have, and KServe autoscales model serving I don't need. Notebooks, Volumes, TensorBoard and now Katib cover the part of Kubeflow that's genuinely useful solo: an environment with GPU access that survives restarts, plus a reasonable way to poke at hyperparameters without hand-rolling a sweep script. Good enough to call this series done for now.
