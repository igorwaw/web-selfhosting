---
title: "Kubeflow, part 1: installing and configuring"
date: 2026-07-26T09:00:00
draft: true
tags: ["ai", "services"]
---

[Minikube](/homelab/minikube/) gave me a Kubernetes cluster to break things on, and [the GPU](/homelab/gpu-guide-2/) gave me something to break with. **[Kubeflow](https://www.kubeflow.org/)** is where the two meet: it's a collection of Kubernetes-native components for machine learning - notebooks, pipelines, hyperparameter tuning, model serving - all running as ordinary pods, controllers and CRDs on top of a cluster. At work, it's how a few hundred people share a GPU budget without stepping on each other. At home, on a single card, it solves no problem I actually have. I want to install it anyway, for the same reason I wanted Minikube in the first place: it's what I use at work, and the only way to actually learn a system this size is to stand it up and watch it fall over a few times.

## What this covers

- **Sizing Minikube for it** - the defaults that were fine for a bare cluster aren't close to enough
- **Trimming the install** - not every component earns its keep on one card and 16GB of RAM
- **Installing with kustomize** - the official method, warts included
- **Getting to the dashboard** - through Istio, the same tunnelling approach as the plain Minikube dashboard
- **Checking the GPU actually shows up** - proving the plumbing works, before doing anything useful with it in part 2

There's no shortage of existing write-ups on getting this running locally - IBM's [KubeflowDojo](https://github.com/IBM/KubeflowDojo/blob/master/HandsOn/Deployment/kubeflow-on-minikube.md) walks through a similar Minikube setup, and [DagsHub's local-install guide](https://dagshub.com/blog/how-to-install-kubeflow-locally/) covers a couple of alternative distributions if Minikube isn't your thing. Worth a look if you get stuck, but none of them were sized for Serenity's constraints, so what follows is what actually worked here.

## Setting expectations on hardware

This isn't running on Firefly. The NAS is busy enough as it is, and 8GB was never going to be enough for Kubeflow's control plane on top of everything else Firefly already does. Instead, the card and Minikube live on Serenity, a separate machine I set aside specifically for GPU work, with 16GB of RAM. Better, but still on the low end of what Kubeflow's own documentation asks for before a single notebook or pipeline run touches the GPU. The realistic options were: buy more RAM, don't bother, or install a deliberately reduced slice of Kubeflow and see how far it gets. I went with the third one - it's the one that involves the most learning per pound spent.

## Sizing Minikube

Serenity's Minikube is a fresh cluster, set up the same way as the [Firefly one](/homelab/minikube/), just started with enough resources in mind from the outset rather than the defaults:

```bash
minikube start --driver=docker --cpus=6 --memory=12000mb --disk-size=60g
```

12GB handed to the Minikube VM leaves 4GB for Serenity's own OS and the NVIDIA driver's own overhead. Not generous, but workable - and it's the main reason the next section exists.

Re-enable the GPU device plugin addon - this is the Kubernetes-side counterpart to the CDI setup from [part 2 of the GPU guide](/homelab/gpu-guide-2/): CDI is what lets a container runtime attach the card at all, this addon is what tells the Kubernetes scheduler a GPU resource exists to hand out:

```bash
minikube addons enable nvidia-device-plugin
kubectl get nodes -o json | jq '.items[].status.allocatable."nvidia.com/gpu"'
```

That should print `"1"`. If it prints nothing, the device plugin's pod (`kube-system` namespace) is worth a `kubectl logs` before going any further - it fails quietly if it can't find the CDI spec generated earlier.

## Trimming the install

Kubeflow's [manifests repo](https://github.com/kubeflow/manifests) ships one big `example/kustomization.yaml` that pulls in everything: Istio, cert-manager, Dex, oauth2-proxy, the central dashboard, Notebooks, Katib, Kubeflow Pipelines, KServe, the training operator, and a handful of supporting web apps. On a 6-core, 12GB VM, all of it starting at once is still a good way to watch pods get OOMKilled and stuck in `CrashLoopBackOff` while they fight over scheduling.

I don't need most of it. Katib (hyperparameter tuning), Pipelines and KServe are aimed at problems - many parallel experiments, serving models behind autoscaling - that don't exist with one GPU and one person using it. For this round, I want: the platform plumbing (Istio, cert-manager, Dex), the central dashboard, and Notebooks. Everything else can wait for a day it's actually needed.

Cloning the manifests and checking out the current release branch (check the repo's branch list for whichever is latest when you read this - the exact tag matters, more on that below):

```bash
git clone https://github.com/kubeflow/manifests.git
cd manifests
git checkout v1.10-branch
```

Then, in `example/kustomization.yaml`, I commented out the resource entries for `katib`, `pipeline` and `kserve` (and their dependencies that only exist for their sake), keeping the common platform pieces, `notebook-controller`, `jupyter-web-app`, `profiles`, `centraldashboard` and `volumes-web-app`. The file is a flat list of relative paths, so it's a matter of finding the right lines and prefixing them with `#`, not a real kustomize edit.

## Installing kustomize

The manifests need a specific major version of kustomize - not "whatever your package manager has", the build output has changed between versions in ways that break Kubeflow's manifests, and the repo's README names the version it was tested against. I got the matching binary directly rather than trusting Debian's package:

```bash
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/
kustomize version
```

## Applying the manifests

This is the part of Kubeflow's install docs that always makes me smile: the official instruction is a retry loop, not a single `kubectl apply`.

```bash
while ! kustomize build example | kubectl apply --server-side --force-conflicts -f -; do
  echo "Retrying..."
  sleep 20
done
```

The reason is ordering: CRDs need to exist before the custom resources that use them, webhooks need their certificates before anything can talk to them, and kustomize builds one flat list of YAML with no concept of "wait for that to be ready first". Rather than solve the dependency graph properly, the documented answer is to keep throwing the whole pile at the API server until nothing's left complaining about a missing CRD. Inelegant, but it does converge - on Serenity it took four or five passes and a few minutes before the loop exited on its own.

Watching it come up, spread across several namespaces:

```bash
kubectl get pods -n cert-manager
kubectl get pods -n istio-system
kubectl get pods -n auth
kubectl get pods -n kubeflow
```

Even trimmed, that's a lot of pods for one node. A few restarted once or twice while waiting on dependencies that weren't ready yet - normal, and worth leaving alone unless one settles into a genuine `CrashLoopBackOff` rather than just an early restart.

## Reaching the dashboard

Kubeflow's UI sits behind the Istio ingress gateway, with Dex handling authentication. Same shape of problem as the plain Minikube dashboard: it only makes sense on `127.0.0.1`, and Serenity is headless too, so I need a tunnel from my laptop.

```bash
kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80
```

`port-forward` binds to `127.0.0.1` on Serenity itself, exactly like `minikube dashboard` did on Firefly, so it's the same SSH tunnelling trick as before:

```bash
ssh -L 8080:127.0.0.1:8080 serenity
```

Then <http://localhost:8080> gets me Dex's login page. The manifests ship a default user for exactly this stage of getting something working - `user@example.com` / `12341234` - which exists purely so you have a login before you configure a real one. It's publicly documented, so it's not a secret in any sense, and it's only reachable through the tunnel above rather than exposed anywhere - but changing it is on the list before I trust this cluster with anything beyond experiments.

Logging in gets me the central dashboard: a sidebar for Notebooks, Pipelines (present in the menu even though I didn't install its backend - it'll just error if clicked), Volumes, Tensorboards. Enough to confirm the platform itself is alive.

## Confirming the GPU is visible

The actual test: creating a notebook server and asking it for a GPU. From the dashboard, *Notebooks → New Notebook*, and under resources there's a GPU count field - it's only populated because of the `nvidia-device-plugin` addon enabled earlier, otherwise it stays empty with nothing to request. Setting it to 1 and starting the server, then once it's running:

```bash
kubectl exec -n kubeflow-user-example-com <notebook-pod-name> -- nvidia-smi
```

Seeing the card's usual `nvidia-smi` output from inside a pod that Kubeflow itself scheduled, rather than a container I started by hand, is the actual milestone of this post - everything from the CDI spec in part 2 of the GPU guide through to the device plugin addon to Kubeflow's own resource request UI is working end to end.

## What's left for part 2

Getting here took more fighting with resource limits than I expected, and I've deliberately left out the pieces (Pipelines, Katib) that make Kubeflow more than "a nicer way to launch Jupyter on Kubernetes". That's fine for now - a working notebook with GPU access, on a cluster I understand the shape of, is exactly the base part 2 needs: actually running something in it.
