---
title: "Serenity, part 2: modernisation candidates"
date: 2026-08-01T12:00:00
draft: true
tags: ["hardware"]
---

[Serenity](/homelab/serenity/) has been doing its job - the dual Xeon E5-2609 ThinkStation handles ML experiments Firefly's little Pentium couldn't touch. But that post ended on a nagging thought: two NUMA domains, a GPU wired to only one socket, and a QPI link that everything else has to fight for bandwidth on. None of that is a *problem* exactly. It's just the kind of thing that makes me wonder whether a single, boring, modern socket would make more sense.

So: what would replace it? I'm looking at two used workstations, plus a handful of cheap ex-corporate desktops that would only earn a place in the table if a full-height, 2-slot-wide card - Serenity's RTX 3050 6GB - actually fits inside them:

- **Lenovo ThinkStation P520C** - Xeon W-2123, 32GB RAM, reusing the RTX 3050 6GB
- **Dell Precision 5820 Tower** - Xeon W-2235, 64GB RAM, 256GB SSD + 1TB HDD, comes with its own Quadro P2200 - roughly **3x the price** of the P520C option
- **Dell Precision T3620** (mini tower) - Core i7-6700 or Xeon E3-1270 v5, 16GB RAM
- **HP EliteDesk 800 G6** (mini tower) - Core i5-10500, 16GB RAM
- **Dell OptiPlex 3090** (Tower) - Core i5-10600, 16GB RAM
- **Dell OptiPlex 5000** (Tower) - Core i5-12500, 16GB RAM

Fit first, spec table second - I already learned that lesson once this post, ruling out a Dell OptiPlex SFF purely because it was low-profile-only.

## Fit check: the cheap desktop candidates

**Dell Precision T3620.** Four expansion slots, all full height: one PCI, one PCIe x4, and two PCIe x16 (one wired at x16, one at x4). Full-height brackets rule out the low-profile trap outright, and the second x16 slot sitting right next to the first gives a 2-slot-wide card somewhere to put its second slot's worth of shroud. Length is the part that actually needed checking - Dell's spec sheet doesn't publish a maximum card length, but people who've put a gaming GPU in this exact case report a practical depth limit of around 9.5in (~241mm) before it hits the drive cage. RTX 3050 6GB cards are small - reference dual-fan boards like ASUS's Dual RTX 3050 6GB run about 200mm - comfortably under that limit. Power's a non-issue too: the RTX 3050 6GB draws its full 70W from the slot, no 6/8-pin cable to find room for. **Fits.**

**HP EliteDesk 800 G6.** HP's own spec sheet lists four full-height slots, including one built for full-length double-wide cards, and HP will sell this exact tower factory-fitted with an RTX 2080 Super - a ~267mm, 2.7-slot card that needs supplementary power. If that's an official configuration, a 200mm, slot-power-only RTX 3050 6GB isn't worth spending more words on. **Fits, comfortably.**

**Dell OptiPlex 3090 and OptiPlex 5000 (Tower).** These don't pass, and the reason is instructive. Despite being labelled "Tower," Dell's current OptiPlex Tower chassis is a different animal from the T3620's actual mini-tower shell - both the 3090 and the 5000 measure about 155 x 292 x 324mm externally: shallower and narrower than the T3620, nowhere near a proper mid-tower. Two things confirm it's genuinely tight rather than just conservatively spec'd. First, Dell's own factory GPU option lists for both are small, low-power parts - GeForce GT 730, Radeon RX 640, Radeon 550 on the 3090. Second, the 5000's newer option list does include an "RTX 3050" - but it turns out to be a distinct 4GB, single-slot, blower-cooled OEM SKU around 180mm long, not the 6GB dual-slot retail card I actually have. [Confirm the exact SKU](/homelab/gpu-guide-1/) strikes again - "RTX 3050" doesn't mean one physical product, and Dell picked the one that fits its own shrunken case, not mine. Neither chassis publishes a max card length either, which itself is telling - a spec worth stating only exists once there's a card worth planning around. **Doesn't fit either machine.** Same fate as the OptiPlex SFF earlier, just for a different physical reason - no table entry for either.

So four of the six survive the gate: the P520C and 5820 (never in question, both proper towers), plus the T3620 and EliteDesk 800 G6. Worth the extra columns below.

## CPU specs

| | Xeon E5-2609 ×2 (Serenity/C30, current) | Xeon W-2123 (P520C) | Xeon W-2235 (Precision 5820) | Core i7-6700 (T3620) | Xeon E3-1270 v5 (T3620) | Core i5-10500 (EliteDesk 800 G6) |
|---|---|---|---|---|---|---|
| Microarchitecture | Sandy Bridge-EP (2012) | Skylake-W (2017) | Cascade Lake-W (2019) | Skylake (2015) | Skylake (2015) | Comet Lake (2020) |
| Sockets | 2 | 1 | 1 | 1 | 1 | 1 |
| Cores/threads per socket | 4 / 4 | 4 / 8 | 6 / 12 | 4 / 8 | 4 / 8 | 6 / 12 |
| Cores/threads, combined | 8 / 8 | - | - | - | - | - |
| Base / turbo clock | 2.4 GHz (no turbo) | 3.6 / 3.9 GHz | 3.8 / 4.6 GHz | 3.4 / 4.0 GHz | 3.6 / 4.0 GHz | 3.1 / 4.5 GHz |
| L3 cache | 10 MB/socket (20 MB combined) | 8.25 MB | 8.25 MB | 8 MB | 8 MB | 12 MB |
| TDP | 80W/socket (160W combined) | 120W | 130W | 65W | 80W | 65W |
| Socket | LGA2011 | LGA2066 | LGA2066 | LGA1151 | LGA1151 | LGA1200 |
| Chipset | C602 | C422 | C422 | C236 | C236 | Q470 |
| Memory | 4 channels/socket, DDR3-800/1066 | 4 channels, DDR4-2666 ECC RDIMM | 4 channels, DDR4-2933 ECC RDIMM | 2 channels, DDR4-2133, non-ECC only | 2 channels, DDR4-2133, ECC UDIMM supported | 2 channels, DDR4-2933, non-ECC only |
| Max memory bandwidth | 34.1 GB/s/socket (68.2 GB/s combined, split across 2 NUMA domains) | 85.3 GB/s, one unified pool | 94 GB/s, one unified pool | 34.1 GB/s, one unified pool | 34.1 GB/s, one unified pool | 46.9 GB/s, one unified pool |
| PCIe | 40 lanes PCIe 3.0/socket, on-die (GPU wired to only one socket) | 48 lanes PCIe 3.0, on-die | 48 lanes PCIe 3.0, on-die | 16 lanes PCIe 3.0 (CPU, GPU slot) + PCH lanes via shared DMI uplink | same as i7-6700 | 16 lanes PCIe 3.0 (CPU, GPU slot) + PCH lanes via shared DMI uplink |
| Inter-socket link | QPI 6.4 GT/s (~26 GB/s) | n/a (one socket) | n/a (one socket) | n/a (one socket) | n/a (one socket) | n/a (one socket) |
| NUMA | Yes, 2 domains | No | No | No | No | No |
| PassMark single-thread | 1,130 | 2,175 | 2,602 | 2,275 | 2,296 | 2,782 |
| PassMark CPU Mark | 5,860 combined | 8,455 | 14,187 | 8,036 | 8,331 | 12,927 |

(Sources: [PassMark E5-2609](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+E5-2609+%40+2.40GHz), [PassMark W-2123](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+W-2123+%40+3.60GHz&id=3136), [PassMark W-2235](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+W-2235+%40+3.80GHz&id=3821), [PassMark i7-6700](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Core+i7-6700+%40+3.40GHz&id=2598), [PassMark E3-1270 v5](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Xeon+E3-1270+v5+%40+3.60GHz&id=2651), [PassMark i5-10500](https://www.cpubenchmark.net/cpu.php?cpu=Intel+Core+i5-10500+%40+3.10GHz&id=3749).)

A few things stand out.

**NUMA just goes away, for all four candidates.** Every one of them is single socket - no QPI, no "which socket is the GPU on", no `numactl` pinning. That resolves the exact thing [the last post](/homelab/serenity/) ended on, workstation or cheap desktop alike.

**Memory bandwidth splits into three tiers.** The two workstations comfortably clear Serenity's combined 68.2 GB/s (85.3 GB/s on the W-2123, 94 GB/s on the W-2235 - the edge there comes from DDR4-2933 support against the W-2123's DDR4-2666, same 4 channels). The EliteDesk's dual-channel DDR4-2933 lands in the middle at 46.9 GB/s - below Serenity's combined figure but above what either socket manages alone today. The T3620 brings up the rear at 34.1 GB/s regardless of which CPU goes in it - only 2 memory channels either way, and coincidentally identical to one of Serenity's own NUMA-local pools right now.

**Multithreaded, the W-2235 leads, but the cheapest fit-checked candidate is the surprise runner-up.** 14,187 (W-2235) vs 12,927 (i5-10500) vs 8,455 (W-2123) vs 8,331 / 8,036 (T3620's two CPU options) vs 5,860 combined today. The EliteDesk's Comet Lake i5 beats a contemporary workstation Xeon on raw throughput, and its single-thread score (2,782) is the highest of any candidate here, current Serenity included - a five-year-old business desktop chip outrunning a pricier workstation part on paper is a good reminder that "workstation" buys more cores, more PCIe lanes, ECC and validated 24/7 operation, not necessarily faster clocks.

**ECC is a genuine three-way split now.** The P520C and 5820 get it by default - same C422 chipset, both Xeon W. On the T3620 it depends on which CPU ships in it: the chipset (C236) supports ECC UDIMMs, but only the Xeon E3-1270 v5 will actually use them - the i7-6700 configuration won't, regardless of what RAM is fitted. The EliteDesk 800 G6 doesn't get a choice either way: Q470 doesn't support ECC at all, whichever CPU sits in the socket.

**The 5820 also brings an SSD.** Serenity currently boots off a single 4TB HDD - fine for space, not fast. The 5820's 256GB SSD + 1TB HDD split (OS/software on flash, bulk data on spinning disk) is a real usability upgrade independent of anything CPU-related, and one none of the cheaper candidates were specified with.

## GPU: reuse, or take the bundled one?

The plan for the P520C, the T3620 and the EliteDesk 800 G6 is the same: move the RTX 3050 6GB across unchanged - GDDR6, 96-bit bus, 168 GB/s VRAM bandwidth, native interface PCIe 4.0 x8, 70W TDP, no external power connector needed.

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

There's still a repeat of the last post's "PCIe: same trap, different reason" for the RTX 3050 specifically - **none of the P520C, the 5820, the T3620 or the EliteDesk 800 G6 actually support PCIe 4.0.** Skylake-W, Cascade Lake-W, Skylake and Comet Lake all predate Intel's client PCIe 4.0 rollout (that started with Rocket Lake in 2021), so on any of these boards the RTX 3050 runs at PCIe 3.0 x8 - half its native interface bandwidth. In practice this probably doesn't matter much: independent PCIe-scaling tests show a card this size rarely saturates even a Gen3 x8 link. The Quadro P2200, for what it's worth, is native PCIe 3.0 x16 - no such mismatch, for whatever that's worth given it's not the card I'd actually use.

## Old vs. less-old vs. less-old-but-newer vs. surprisingly-not-bad

None of these four is actually *new* - 2015 to 2020 hardware, all bought used, same as Serenity's 2012 Xeons were bought used. The real change isn't "old vs new", it's "two contended NUMA domains vs one predictable socket", plus a solid jump in single-thread performance across the board (1,130 today, vs 2,175-2,782 depending on candidate), and a bigger one multithreaded with the W-2235 in particular (14,187 vs 5,860 combined today).

Half the candidates never had to prove themselves physically - the P520C and 5820 are proper workstation towers, room for anything. The other half did, and it cut the field down before a single benchmark mattered: the T3620 and EliteDesk 800 G6 passed, the OptiPlex 3090 and OptiPlex 5000 didn't, purely on whether a full-height 2-slot card has anywhere to go.

Of the four that made it to the table, the 5820 wins on raw spec - more bandwidth, more cores, an SSD, 64GB instead of 32GB - but costs roughly **3x the P520C**, and ships with a GPU that isn't one I'd keep. The EliteDesk 800 G6 is the real curiosity: cheapest of the lot, no ECC on offer at any price, yet its i5-10500 out-throughputs the P520C's Xeon and nearly matches the 5820's. The T3620 sits at the bottom of the performance table but is the only one where I get to choose whether ECC comes along, by choosing which CPU goes in the socket. Whether any of that headroom is worth chasing over just buying the cheapest one that fits depends on how much the extra performance actually matters versus banking the difference. No verdict yet - that's for a follow-up once I've actually run something on one of them.
