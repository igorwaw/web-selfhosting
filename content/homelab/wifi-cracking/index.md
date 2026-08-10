---
title: "Cracking my own WiFi password with a GPU"
date: 2026-08-06T15:00:00
draft: true
tags: ["gpu", "security"]
---

[Hashcat](/homelab/hashcat/) already showed how much a GPU speeds up guessing a password hash. WPA/WPA2 WiFi passwords are guessable the same way - the handshake between a device and the access point is, in the end, just another hash to attack. This is the same experiment, aimed at my own router instead of a text file.

The usual warning applies, more so here than for the hashcat post: only run any of this against a network you own or have explicit permission to test. Capturing someone else's handshake without permission isn't a grey area.

## What's actually being attacked

WPA-Personal (both WPA1 and WPA2) derives its session keys from the passphrase using PBKDF2-HMAC-SHA1 with 4,096 iterations, salted with the network's SSID. That's a real KDF, not a fast hash - and it's exactly the mode I already benchmarked in the [hashcat post](/homelab/hashcat/#benchmarking): `WPA-PBKDF2-PMKID+EAPOL`, at 233 kH/s on this card. So no new software is needed on the GPU side; hashcat already covers this as mode 22000.

One consequence worth flagging before starting: WPA1 vs WPA2 makes no difference to crack speed, since both use the same PBKDF2 construction for the passphrase - the difference between them is the encryption cipher (TKIP vs CCMP) applied afterwards, not the key derivation. Switching my router to WPA1 for this test wouldn't buy anything. WPA3, on the other hand, replaces this whole mechanism with SAE, which isn't vulnerable to offline dictionary/mask attacks the same way - so the router needs to stay in WPA2 mode (or WPA2/WPA3 mixed, as long as a WPA2 client connects) for this to work at all.

## Hardware: a monitor-mode-capable adapter

Capturing a handshake or PMKID off the air needs a wireless adapter that supports monitor mode (and ideally packet injection, for deauthenticating a client to force a fresh handshake). Most laptop built-in cards are unreliable for this. *(To fill in: which adapter I ended up using, and whether monitor mode worked out of the box or needed a driver.)*

## Installing the capture tooling

The actual capture and format-conversion happens on the CPU, with separate tools from hashcat itself - `hcxdumptool` and `hcxtools`, the modern replacement for the old aircrack-ng-based workflow:

```bash
sudo apt install hcxdumptool hcxtools
```

## Capturing a handshake or PMKID

*(To fill in: actual `hcxdumptool` invocation and output, whether a PMKID was captured passively or a deauth was needed to force a 4-way handshake.)*

## Converting to hashcat's format

`hcxpcapngtool` turns the capture into the `.hc22000` format hashcat expects:

```bash
hcxpcapngtool -o capture.hc22000 capture.pcapng
```

## Cracking it

```bash
hashcat -m 22000 -a 0 capture.hc22000 rockyou.txt
```

Same dictionary-attack logic as the hashcat post: if the passphrase is anything already in a leaked wordlist, it falls immediately regardless of the KDF's iteration count. *(To fill in: dictionary attack result, then a mask attack against a deliberately shortened test passphrase, with actual timings from the 233 kH/s figure.)*

## What this should demonstrate

The plan is to run this twice: once against my actual passphrase (to see it hold up, or not), and once against a deliberately short passphrase set temporarily for the test, to put a real time-to-crack number next to the keyspace table from the hashcat post rather than just the theoretical one. *(To fill in once both runs are done.)*
