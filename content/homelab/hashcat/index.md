---
title: "Hashcat: learning why password choices actually matter"
date: 2026-07-25T17:00:00
draft: true
tags: ["security"]
---

[Part 1](/homelab/gpu-guide-1/#beyond-neural-networks-what-else-i-might-use-it-for) had password cracking on the original shopping list, alongside the neural network experiments. It's not AI at all, but it's the same underlying reason the card is useful for it: lots of small, independent, identical operations, which is exactly what a GPU is built for.

Worth saying plainly before any of this: only against hashes I own or generated myself, never anyone else's account. The point of this post isn't cracking anything real, it's understanding why "use a long password" and "use bcrypt, not MD5" are the advice they are, by watching the numbers directly instead of taking them on faith.

## Why a GPU cracks passwords fast

Checking whether a guess matches a hash means running the same hash function on it and comparing the output - a small, fixed, independent computation, repeated once per guess. That's the same shape of problem as shading a million pixels or multiplying matrix entries: no guess depends on any other, so thousands can run at once across the GPU's cores rather than one at a time on a CPU.

Crucially, this only matters for **fast** hash functions. MD5 and SHA-1 were built to hash a file quickly, and that speed is exactly the property that makes them bad for passwords - the same speed a GPU can throw thousands of cores at. Algorithms built specifically for passwords - bcrypt, scrypt, Argon2 - are deliberately slow, and deliberately memory-hungry in a way that doesn't parallelise nearly as well on a GPU's architecture. The gap in cracking speed between "someone hashed passwords with MD5" and "someone hashed passwords with Argon2" is enormous, and it's the main thing worth seeing directly.

## Installing

The driver and CUDA setup from [part 2](/homelab/gpu-guide-2/) already covers what hashcat needs:

```bash
sudo apt install hashcat
```

## Benchmarking

```bash
hashcat -b
```

This runs a fixed benchmark across a wide range of hash types and prints hashes-per-second for each. The gap described above shows up immediately as a number: MD5 lands in the billions of guesses per second on this card, while bcrypt lands in the thousands. Roughly six orders of magnitude, for what's conceptually "the same" operation, purely because of how each algorithm was designed.

## A dictionary attack

Generate a test hash to attack rather than using a real one:

```bash
echo -n "password123" | md5sum
```

```bash
hashcat -m 0 -a 0 <hash> rockyou.txt
```

`-m 0` selects MD5 as the hash type, `-a 0` selects a dictionary attack: try every entry from a wordlist. `rockyou.txt` - a well-known leaked password list, easy enough to find via any SecLists mirror - cracks anything actually common almost instantly, which is itself the lesson: if a password is in a public breach list already, its hash algorithm barely matters.

## A mask attack

For passwords that aren't dictionary words, a mask attack brute-forces a pattern instead of a fixed list - useful for testing "how long would a random password of this shape actually take":

```bash
hashcat -m 0 -a 3 <hash> ?u?l?l?l?l?l?d?d
```

`?u?l?l?l?l?l?d?d` means one uppercase letter, five lowercase, two digits - an 8-character password shaped like a lot of real ones. Swapping in `?a` (any printable character) and adding length shows the runtime climbing by orders of magnitude per extra character, which is the more convincing version of "longer is better" than just being told so.

## What this actually demonstrates

Running the same handful of guesses through both an MD5 hash and a bcrypt hash, side by side, turns two pieces of advice usually taken on faith into something measured directly on this card: password length matters because the search space grows exponentially, and hash algorithm choice matters because it changes the base rate that exponential growth is multiplying from - by a factor of a million, not a rounding error.
