---
title: "GPU for CUDA experiments: the powerful cards"
date: 2026-09-06T09:00:00
draft: true
tags: ["hardware", "gpu"]
---

[Part 1](/homelab/gpu-guide-1/) was about getting a cheap CUDA-capable card for tinkering, and it ended with a short list of things that change once you go up-market. This is that list expanded: a tour of the powerful cards, from the top of the consumer range, through the workstation parts and the mid-range datacentre cards, up to the training flagships.

I'm not buying any of these for the house. But I work with them, and people keep asking which is which, why an H100 costs as much as a car, and whether that £250 Tesla on eBay is a bargain. Sometimes it is. So here's a reference.

A caveat on prices: the high end moves fast and the UK used market is thin. Treat every number below as "rough, early 2026, and probably wrong by the time you read it". Where a card isn't realistically buyable by an individual, I've said so - and for most of the datacentre parts, renting (see part 1) is the only sane option anyway.

## How to read the table

A few things that don't come up with budget cards:

**Form factor: PCIe vs SXM.** The flagships come in two shapes. The PCIe version is a normal (if enormous) expansion card. The SXM version is a bare board that bolts onto a baseboard socket on an HGX/DGX-style server - more power, more bandwidth, NVLink between modules, and completely useless without the matching chassis. If you see a cheap V100 or A100 "SXM2/SXM4" module on eBay, that's why it's cheap.

**Power connector: mind the EPS trap.** The passive datacentre cards (P40, P100, V100, A10, A40, A100 PCIe, L40S) take a single 8-pin **CPU/EPS** connector, not a PCIe 8-pin. The two are keyed differently and the pinouts don't match. Force a PCIe cable in, or use the wrong cheap adapter off eBay, and you can kill the card. Buy the correct CPU-8-pin adapter and check it against the card's manual before powering on.

**Passive cooling.** Covered in part 1: cards with no fan rely on a server's ducted, high-pressure airflow. In a desktop they thermal-throttle within seconds. People bodge a blower and a 3D-printed shroud onto the exhaust end - it works, it's loud, and you want to keep an eye on `nvidia-smi -q -d TEMPERATURE` while you do it.

**No display output.** Most datacentre cards, and some workstation ones, have no video ports at all. Fine for headless compute, no good as the only GPU in a machine you also want a screen on.

**ECC and MIG.** Datacentre and workstation cards have ECC VRAM, on by default, costing a little capacity and bandwidth (toggle with `nvidia-smi -e`). A100 and newer also support MIG, slicing one physical GPU into up to seven isolated instances - see [part 2](/homelab/gpu-guide-2/).

**NVLink is mostly gone.** Consumer NVLink ended with the RTX 3090. The Ada workstation cards dropped it too. It survives only on A100/H100/H200 SXM and a handful of "NVL" pairs. Everything else does multi-GPU over PCIe.

**Host firmware.** Large-BAR cards (anything from 24 GB up, and definitely A100/H100) need "Above 4G Decoding" and Resizable BAR enabled in the host UEFI, or the driver won't initialise them.

**Compute Capability floor.** From part 1: CUDA 13.0 wants CC 7.5 or higher. That cuts off Pascal (P40, P100 - CC 6.x) and Volta (V100 - CC 7.0). They still run, but pinned to CUDA 12.x and the older drivers that go with it.

## Summary

| Card | Price (UK) | CC | TDP | Passive | Power connector | Notable |
|---|---|---|---|---|---|---|
| RTX 5090 | £1919 MSRP, ~£2700-3500 street | 12.0 | 575 W | No | 1x 12V-2x6 | 32 GB GDDR7, 1.8 TB/s, PCIe 5.0, FP4. No NVLink. Chronic shortage. |
| RTX 4090 | ~£1500-2100 used | 8.9 | 450 W | No | 1x 12VHPWR | 24 GB GDDR6X, 1.0 TB/s. Discontinued. 3.5-slot cooler. |
| RTX PRO 6000 Blackwell | ~£7500-9000 | 12.0 | 600 W (Max-Q 300 W) | No (Server ed. yes) | 1x 12V-2x6 | 96 GB GDDR7 ECC. Same die as the 5090. Backordered. |
| RTX 6000 Ada | ~£4000-4500 used, ~£5500-6800 new | 8.9 | 300 W | No (blower) | 1x 12VHPWR / EPS-8 | 48 GB GDDR6 ECC, 960 GB/s, dual-slot. No NVLink. |
| RTX A6000 (Ampere) | ~£1700-2400 used, ~£3000-3800 new | 8.6 | 300 W | No (blower) | 1x EPS-8 | 48 GB GDDR6 ECC, 768 GB/s, dual-slot, 2-way NVLink. The value pick. |
| Tesla P40 | ~£250-400 used | 6.1 | 250 W | Yes | 1x EPS-8 | 24 GB GDDR5, 346 GB/s. No tensor cores, FP16 runs at 1/64 rate. Needs shroud + adapter. |
| Tesla P100 | ~£130-230 used | 6.0 | 250 W | Yes | 1x EPS-8 | 16 GB HBM2, 732 GB/s. Real 2:1 FP16, but no tensor cores. |
| Tesla V100 (PCIe) | ~£450-800 (16 GB), ~£900-1400 (32 GB) | 7.0 | 250 W | Yes | 1x EPS-8 | HBM2, 900 GB/s. First-gen tensor cores (FP16 only). Dropped by CUDA 13. |
| Tesla T4 | ~£450-700 used | 7.5 | 70 W | Yes | None (slot power) | 16 GB GDDR6, 320 GB/s. Tensor cores + NVENC. Single slot. Stays pricey. |
| NVIDIA A10 | ~£1400-2200 used | 8.6 | 150 W | Yes | 1x EPS-8 | 24 GB GDDR6, 600 GB/s, single slot. Ampere tensor cores. |
| NVIDIA L4 | ~£1900-2700 | 8.9 | 72 W | Yes | None (slot power) | 24 GB GDDR6, 300 GB/s, single slot. Strong AV1/NVENC. |
| NVIDIA L40S | ~£6500-9000 | 8.9 | 350 W | Yes | 1x 12VHPWR / EPS | 48 GB GDDR6 ECC, 864 GB/s, FP8. Dual-slot. |
| NVIDIA A100 40 GB (PCIe) | ~£4000-6000 used | 8.0 | 250 W | Yes | 1x EPS-8 | HBM2e, 1.56 TB/s. MIG, NVLink, TF32/BF16. |
| NVIDIA A100 80 GB | ~£6500-10000 used | 8.0 | 300 W (PCIe) / 400-500 W (SXM4) | Yes | 1x EPS-8 / SXM | HBM2e, ~1.9-2.0 TB/s. The LLM training workhorse. |
| NVIDIA H100 80 GB (PCIe) | ~£19000-27000 | 9.0 | 350 W (PCIe) / 700 W (SXM5) | Yes | 1x 12VHPWR / SXM | HBM2e 2 TB/s (PCIe), HBM3 3.35 TB/s (SXM). FP8 Transformer Engine. Export-controlled. |
| NVIDIA H200 | allocation only, ~£28000-35000 | 9.0 | 700 W | Yes (SXM) | SXM baseboard | 141 GB HBM3e, 4.8 TB/s. Same Hopper compute as H100, more/faster memory. |
| NVIDIA B200 | systems only, not sold individually | 10.0 | 1000 W | Yes (system) | SXM baseboard | 192 GB HBM3e, ~8 TB/s, dual-die, FP4. HGX/GB200 only. |

## Top of the consumer range

**RTX 5090.** The current consumer flagship, and for most people the ceiling before prices go silly. 32 GB is enough to run a quantised 70B model or fine-tune something mid-sized, and unlike the datacentre cards you can actually put one in a normal PC. The problem is getting one: it launched at £1919, it's been scarce since day one, and UK street prices sit well above £3000. There's no NVLink, so two of them don't pool memory - they just run separate jobs.

**RTX 4090.** The previous flagship, and still a very capable card. Production stopped when the 50-series launched, and the export ban on high-end GPUs to China pulled a lot of used stock off the Western market too, so used prices went *up* after discontinuation. 24 GB, no NVLink, and a cooler so large it fouls the adjacent slots on most boards. If you find one at a sane price it's a better buy than a scalped 5090.

## Workstation cards

These trade raw gaming performance for much more VRAM, ECC, blower coolers that work in a normal case, and a price premium for the pro driver branch.

**RTX PRO 6000 Blackwell.** 96 GB of GDDR7 on the same silicon as the 5090. This is the card the small AI shops actually want - enough memory to fine-tune or serve a large model on a single board, in a workstation, without a datacentre. Demand is well ahead of supply and lead times are long. Three variants: Workstation (axial fans, 600 W), Max-Q (300 W, same memory, half the throughput) and Server (passive).

**RTX 6000 Ada.** The prior generation: 48 GB, 300 W, dual-slot blower. No NVLink (Ada dropped it). Still sold new, still expensive, gradually being displaced by the Blackwell card above.

**RTX A6000 (Ampere).** The one worth knowing about. 48 GB of ECC GDDR6 in a single dual-slot blower card at 300 W, and used prices have fallen to the point where it's the cheapest sane route to 48 GB in one slot. Ampere means third-gen tensor cores with BF16 (see part 1), it has 2-way NVLink if you want 96 GB across a pair, and it drops straight into an ordinary tower. If I ever outgrow a 3090 at home, this is what I'd get. Don't confuse it with the newer "RTX 6000 Ada" - the naming is deliberately unhelpful.

## The eBay route: decommissioned datacentre cards

Part 1 mentioned this: ex-enterprise GPUs from cloud refresh cycles are the cheapest way to a lot of VRAM, as long as you accept old architectures and old software. All of these are passive, all need a fan bodge in a desktop, and the Pascal/Volta ones are stuck on CUDA 12.x.

**Tesla P40.** For a while this was *the* budget local-LLM card: 24 GB for around £150. Two catches. It has no tensor cores, and its FP16 throughput is deliberately crippled to 1/64 of FP32, so llama.cpp and friends run everything in FP32 or INT8 and it's slow. And now that CUDA 13 has dropped Pascal, it's a dead-end platform. Prices actually rose during the LLM boom and have since drifted back down as the software support ended. Still the cheapest 24 GB you can buy, if you know what you're getting.

**Tesla P100.** Less VRAM than the P40 (16 GB) but HBM2 at 732 GB/s and *proper* 2:1 FP16, so for anything memory-bandwidth-bound it's often the faster card despite being cheaper. No tensor cores. Same Pascal software cliff.

**Tesla V100.** The first card with tensor cores (first generation, FP16 only - no BF16, no INT8). 16 or 32 GB HBM2, 900 GB/s. The PCIe version is the practical one; the SXM2 modules are cheaper still but need a baseboard almost nobody has. Volta was dropped in CUDA 13.0, so it's CUDA 12.x from here.

**Tesla T4.** The odd one out: 70 W, single slot, no power connector, runs entirely off the PCIe slot. 16 GB, tensor cores, and a good NVENC block, which made it the standard cloud inference and transcoding card for years. Because it's still genuinely useful and sips power, it never got cheap - expect £500-700 where a same-age V100 is less. CC 7.5, so it's the oldest datacentre card still supported by current CUDA.

## Mid-range datacentre

Current-generation inference and light-training cards. Passive, PCIe, priced for businesses.

**NVIDIA A10.** 24 GB, 150 W, single slot, Ampere tensor cores with BF16. A sensible all-rounder if you find one used and have the airflow. **L4** is the Ada successor to the T4 - 24 GB, 72 W, slot-powered, single slot, excellent AV1 encode - aimed at inference and video pipelines. **L40S** is the big Ada inference card: 48 GB, 350 W, FP8 support, roughly "RTX 6000 Ada tuned for servers". **A30** and **A40** slot in between: A30 is a cut-down 24 GB HBM2 A100 for inference, A40 is a 48 GB GDDR6 card similar in spirit to the A6000.

## Top of the line

The training flagships. You will not buy these at retail as an individual - they're sold on allocation to cloud providers and OEMs, with waiting lists, and the Hopper and Blackwell parts are under US export controls. Rent them.

**NVIDIA A100.** The card that ran the first wave of large-model training. 40 or 80 GB HBM2e, 1.5-2.0 TB/s, MIG partitioning, NVLink, TF32 and BF16. Grey-market 80 GB cards turn up on eBay around £7000-10000; the 40 GB PCIe version is more like £4000-6000 and is the only one in this section a determined hobbyist might actually own.

**NVIDIA H100.** Hopper. The step up from A100 is the Transformer Engine with FP8, which roughly doubles useful throughput for LLM work, plus much more bandwidth (3.35 TB/s on the SXM part). 80 GB. The PCIe card is ~350 W; the SXM5 module is 700 W and needs an HGX baseboard. New prices are £20000+ and supply is allocated - most people meet an H100 only through a cloud VM.

**NVIDIA H200.** Same Hopper compute as the H100, but 141 GB of HBM3e at 4.8 TB/s. The extra memory is the whole point: it lets a big model run for inference on one GPU where an H100 would need two. Allocation only.

**NVIDIA B200.** Blackwell datacentre (CC 10.0 - note the consumer Blackwell cards report 12.0, a naming quirk from part 1). Dual-die, 192 GB HBM3e, around 8 TB/s, native FP4, 1000 W. Only sold inside HGX B200 systems and GB200 NVL72 racks, where each "superchip" pairs two of these with a Grace CPU and the whole rack is liquid-cooled. This is data-hall hardware; the closest you'll get is a per-hour instance.

## What this actually means for a home setup

Nothing above changes the part 1 conclusion. For learning CUDA, a cheap Ampere card is plenty. For running local LLMs at home the realistic ceiling is a used RTX 3090 (part 1) or, if you can stretch and want 48 GB in one slot, a used RTX A6000. Everything from the L40S upward is something you rent by the hour when a job genuinely needs it, and hand back when it's done.
