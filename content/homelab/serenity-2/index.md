---
title: "Serenity, part 2: modernisation candidates"
date: 2026-08-01T12:00:00
draft: true
tags: ["hardware"]
---

[Serenity](/homelab/serenity/) has been doing its job - the dual Xeon E5-2609 ThinkStation handles ML experiments Firefly's little Pentium couldn't touch. But that post ended on a nagging thought: two NUMA domains, a GPU wired to only one socket, and a QPI link that everything else has to fight for bandwidth on. None of that is a *problem* exactly. It's just the kind of thing that makes me wonder whether a single, boring, modern socket would make more sense.

So: what would replace it? I'm looking at two used workstations, one of which would inherit Serenity's RTX 3050 6GB, the other bringing its own GPU:

- **Lenovo ThinkStation P520C** - Xeon W-2123, 32GB RAM, reusing the RTX 3050 6GB
- **Dell Precision 5820 Tower** - Xeon W-2235, 64GB RAM, 256GB SSD + 1TB HDD, comes with its own Quadro P2200 - roughly **3x the price** of the P520C option

Same exercise as last time: put the numbers next to the current machine and see what actually changes.

## CPU specs

| | Xeon E5-2609 ×2 (Serenity/C30, current) | Xeon W-2123 (P520C) | Xeon W-2235 (Precision 5820) |
|---|---|---|---|
| Microarchitecture | Sandy Bridge-EP (2012) | Skylake-W (2017) | Cascade Lake-W (2019) |
| Sockets | 2 | 1 | 1 |
| Cores/threads per socket | 4 / 4 | 4 / 8 | 6 / 12 |
| Cores/threads, combined | 8 / 8 | - | - |
| Base / turbo clock | 2.4 GHz (no turbo) | 3.6 / 3.9 GHz | 3.8 / 4.6 GHz |
| L3 cache | 10 MB/socket (20 MB combined) | 8.25 MB | 8.25 MB |
| TDP | 80W/socket (160W combined) | 120W | 130W |
| Socket | LGA2011 | LGA2066 | LGA2066 |
| Chipset | C602 | C422 | C422 |
| Memory | 4 channels/socket, DDR3-800/1066 | 4 channels, DDR4-2666 ECC RDIMM | 4 channels, DDR4-2933 ECC RDIMM |
| Max memory bandwidth | 34.1 GB/s/socket (68.2 GB/s combined, split across 2 NUMA domains) | 85.3 GB/s, one unified pool | 94 GB/s, one unified pool |
| PCIe | 40 lanes PCIe 3.0/socket, on-die (GPU wired to only one socket) | 48 lanes PCIe 3.0, on-die | 48 lanes PCIe 3.0, on-die |
| Inter-socket link | QPI 6.4 GT/s (~26 GB/s) | n/a (one socket) | n/a (one socket) |
| NUMA | Yes, 2 domains | No | No |
| PassMark single-thread | 1,130 | 2,175 | 2,602 |
| PassMark CPU Mark | 5,860 combined | 8,455 | 14,187 |

(Sources: [PassMark E5-2609](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+E5-2609+%40+2.40GHz), [PassMark W-2123](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+W-2123+%40+3.60GHz&id=3136), [PassMark W-2235](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+W-2235+%40+3.80GHz&id=3821).)

A few things stand out.

**NUMA just goes away.** Both candidates are single socket - no QPI, no "which socket is the GPU on", no `numactl` pinning. That resolves the exact thing [the last post](/homelab/serenity/) ended on.

**Both candidates beat Serenity's memory bandwidth outright, and the W-2235 edges out the W-2123.** 85.3 GB/s and 94 GB/s respectively, both in one unified pool - already *more* than Serenity's theoretical combined 68.2 GB/s, and all of it is usable, since there's no NUMA split to trip over. The W-2235's edge comes down to DDR4-2933 support against the W-2123's DDR4-2666, same 4 channels.

**Multithreaded, the W-2235 pulls well ahead of both.** 14,187 vs 8,455 vs 5,860 combined - about 2.4x the current dual-Xeon setup, and 1.7x the W-2123, on two extra cores and a higher clock across the board (130W TDP against 120W - a small increase for a large jump).

**Same chipset, so ECC comes along either way.** Both the P520C and the 5820 use C422 and Xeon W CPUs, so ECC RDIMM support carries over unchanged from what Serenity has now (C602). Not something to weigh between the two candidates - only relevant if I were still comparing against a consumer chipset, which is no longer on the table.

**The 5820 also brings an SSD.** Serenity currently boots off a single 4TB HDD - fine for space, not fast. The 5820's 256GB SSD + 1TB HDD split (OS/software on flash, bulk data on spinning disk) is a real usability upgrade independent of anything CPU-related, and one the P520C option wouldn't include unless I bought a drive separately.

## GPU: reuse, or take the bundled one?

The P520C plan is simple: move the RTX 3050 6GB across unchanged - GDDR6, 96-bit bus, 168 GB/s VRAM bandwidth, native interface PCIe 4.0 x8, 70W TDP, no external power connector needed.

The 5820 complicates that pleasantly, since it already comes with a Quadro P2200 fitted. Worth being honest about what that "free" GPU actually is before treating it as a bonus:

| | RTX 3050 6GB | Quadro P2200 |
|---|---|---|
| Architecture | Ampere (2024 refresh) | Pascal (2018) |
| Compute capability | 8.6 | 6.1 |
| CUDA cores | 2304 | 1280 |
| VRAM | 6GB GDDR6 | 5GB GDDR5X |
| Memory bandwidth | 168 GB/s | 200 GB/s |
| PCIe interface | 4.0 x8 | 3.0 x16 |
| TDP | 70W, no external power connector | 75W |
| Tensor Cores / BF16 | Yes | No |

Pascal predates Tensor Cores entirely, and [I picked the RTX 3050 6GB over cheaper Turing-generation cards specifically because BF16 support was worth paying for](/homelab/gpu-guide-1/). The Quadro P2200 is a generation older than even that - decent CUDA core count, even slightly more raw memory bandwidth, but for the exact ML workload Serenity exists for, it's a step backwards, not a bonus. Realistically the plan would be: move the RTX 3050 across regardless of which machine I pick, and either sell the Quadro or keep it as a spare display card for something that isn't Serenity.

There's still a repeat of the last post's "PCIe: same trap, different reason" for the RTX 3050 specifically - **neither the P520C nor the 5820 actually supports PCIe 4.0.** Skylake-W and Cascade Lake-W both predate Intel's client PCIe 4.0 rollout (that started with Rocket Lake in 2021), so on either board the RTX 3050 runs at PCIe 3.0 x8 - half its native interface bandwidth. In practice this probably doesn't matter much: independent PCIe-scaling tests show a card this size rarely saturates even a Gen3 x8 link. The Quadro P2200, for what it's worth, is native PCIe 3.0 x16 - no such mismatch, for whatever that's worth given it's not the card I'd actually use.

## Old vs. less-old vs. less-old-but-newer

Neither candidate is actually *new* - a 2017 workstation Xeon and a 2019 refresh of the same platform, both bought used, same as Serenity's 2012 Xeons were bought used. The real change isn't "old vs new", it's "two contended NUMA domains vs one predictable socket", plus a solid jump in single-thread performance either way (1,130 today, vs 2,175 or 2,602), and a bigger one multithreaded with the W-2235 (14,187 vs 5,860 combined today).

The 5820 is the better machine on every spec in the table - more bandwidth, more cores, an SSD, 64GB instead of 32GB. It's also roughly **3x the price** of the P520C option, and the GPU it ships with isn't one I'd actually keep. Whether that premium is worth it depends on how much the extra headroom matters versus just buying the P520C and putting the difference towards something else. No verdict yet - that's for a follow-up once I've actually run something on one of them.
