---
title: "Intro: reclaiming your phone"
date: 2026-10-08T10:00:00
draft: false
tags: ["android", "intro"]
---

Strictly speaking, this section is not about self hosting. There won't be much about servers here, phone apps are client software. But the spirit is the same: reclaiming some privacy and control over your data.

Your phone is the most personal computer you own. It knows where you are, who you contact, what you photograph, what you read. If you use a smartwatch, it also collects health data. By default, a lot of this ends up on Google's servers (or Apple's, but I'm only covering Android here), plus whatever each app vendor decides to collect. Self hosting your photos or files at home doesn't help much if the phone keeps sending everything somewhere else.

As with the server apps, I'm not going for perfect privacy. There's a law of diminishing returns, and in the case of Android it kicks in very quickly. Some things are easy though. I'll go through them in the next posts. But first, let's explain what we'll be working on.

## Why not iPhone?

Since the whole guide will be about Android, let's deal with this question first. You might have heard that iPhones are a better option if you care about privacy and security. Many of the claims are true. Apple makes its money mostly from hardware and services, not from ads, so it has less incentive to collect data about you. A lot of processing (like recognising faces in photos) is done on the phone instead of in the cloud. Updates are great too - iPhones get them for many years.

However, iPhones are less customisable. You get as much privacy as Apple decides is good for you, and there aren't many options to improve it.

- Apple decides what apps are available. On the EU market, alternative app marketplaces are allowed (since March 2024, thanks to the Digital Markets Act) - but the marketplaces need Apple's approval, and every app still has to be checked by Apple. Apple is formally compliant with the new law, but makes life harder for anyone who actually wants to use it.
- Apple's privacy ends where governments push back. In China, VPN apps were removed from the App Store in 2017, and since 2018 iCloud data of Chinese users is stored in the government-owned datacentre.
- You can't unlock the bootloader, install a different OS or root the phone.
- You can't verify any of the claims. iOS is closed source, so Apple's stance on privacy has to be taken on trust. And Apple collects data too: it runs its own ad business (Apple Ads, in the App Store and Apple News). In 2022 researchers found that the App Store and other Apple apps sent detailed analytics - what you searched for, which ads you saw - even with iPhone Analytics turned off.

Android starts from a lower privacy, but allows you to go further, if you're ready to put in some effort.

## Standard Android: open source, but not really

Android is, formally, an open source operating system. The Android Open Source Project (AOSP) publishes the source code under the Apache licence. Anyone can take it, build it and put it on a phone. That's what custom OSes do. But the Android you get on a phone from the shop is not just AOSP - it's AOSP plus a large, proprietary layer from Google.

### Google Play Services

Google Play Services is a system app that comes preinstalled on almost every Android phone sold outside China. It's not something you use directly - it runs in the background with very broad, privileged permissions and can't be uninstalled. It provides services to other apps:

- push notifications,
- location and maps,
- sign in with Google, account sync,
- in-app payments and subscriptions,
- device integrity checks (SafetyNet, now Play Integrity) - the thing that lets an app ask "is this a genuine, unmodified phone?",
- plus a long list of smaller APIs: nearby devices sharing, Find My Device, exposure notifications, safe browsing, and so on.

### How it grew

It didn't start that way. In early versions of Android, a lot of this functionality lived in the open source part of the system, and the default apps (browser, calendar, music player, keyboard, messaging) were open source too. Google apps were an optional extra.

Play Services showed up around 2012, and Google claimed the reason was to improve security. Phone makers were terrible at shipping OS updates, so Google stopped using standard Android APIs, which were often obsolete. Instead, it shipped an app that provided new versions of those APIs. And, since it's an app, not a core part of the OS, it can be easily updated just like any other app.

Old, open source versions of default system apps were slowly abandoned and replaced by closed Google equivalents. New APIs were added only to Play Services. Other app developers, quite reasonably, used whatever was easiest and worked on most phones.

Now, it's not that what Google said about improving security wasn't true. The new APIs really deal with vulnerabilities much faster. Plus they provide tons of new features. But the intended side effect is increased reliance on Google. Phone makers who want the Play Store on their devices have to license the whole Google Mobile Services package from Google, under Google's conditions, including passing Google's compatibility tests and preinstalling Google's apps (EU laws put some limits on this, but not much). In practice, an Android phone without Google services is a commercial non-starter outside China - just ask Huawei.

In recent years Google has been pushing for even more control. The EU pushes back, but so far it seems to be behind. AOSP development moved to Google's internal branches, with the source published only at release time, Pixel device code stopped being published, and Google started requiring that apps installed from outside the Play Store on certified phones come from verified developers - rolling out from late 2026 in a few countries, globally in 2027 (there is a way around it, but it was intentionally made hard).

### Why it makes tinkering hard

The result is that "open source Android" is in practice a skeleton. It is relatively easy (for skilled developers) to build AOSP, but out of the box a lot of apps will not work, because they use Play Services APIs. Or at least will be missing many important features such as notifications and cloud sync.

An alternative is to use an open source reimplementation like microG. They do a surprisingly good job of providing the most important APIs without treading on users' privacy, but it's a never-ending game of catching up with a closed target.

And then there is the integrity check. With SafetyNet and later Play Integrity, apps can ask Google whether the phone runs an unmodified, Google-certified system with a locked bootloader. Banking apps, payment apps, government apps, even some games refuse to work if the answer is no. Newer versions of these checks rely on hardware-backed attestation, which is much harder to fake.

Android still is far more open than iOS, because the options described below exist. But they come with a price. Which is why we're going to try a simpler option first.

### What about Chinese phones?

Phones sold in China are the big exception - they ship without Play Services. Not by choice of privacy-minded phone makers, though. Google services don't work in China since 2010-2014. Both sides are to blame: the Chinese government doesn't want to hand over the control of data to a foreign company, while Google is in dispute over censorship and hacking attacks. Google Play Services were never introduced in China.

So Chinese phone makers built their own replacements: app stores, push notification services, cloud sync and all other APIs. Huawei went furthest with Huawei Mobile Services, which became its only option worldwide after US sanctions cut it off from Google in 2019. (Global versions of Xiaomi, OPPO and other Chinese brands usually do ship with Google services.)

For obvious reasons, it's not a privacy win. You simply swap one data-hungry vendor for another, less transparent one, subject to Chinese law that requires companies to cooperate with state intelligence. And there are concrete findings: in 2021, Lithuania's National Cyber Security Centre found a censorship list of 449 phrases built into Xiaomi's system apps. Plus, the engineering is often sloppy: there were many cases of weak encryption, malware in app stores, overly broad app permissions.

## Levels of control

There are different levels of control you can have over your phone. The catch is that more control also means more difficulty: more effort to set up and more problems along the way.

### Level 3: replacing the OS

The most comprehensive option is to replace the operating system completely with a custom one, such as GrapheneOS, LineageOS or /e/OS. You can get rid of Google services entirely and decide what runs on your phone.

The downsides: only some phone models are supported, installing it requires unlocking the bootloader and wiping the phone, and many important apps won't work. Apps that depend on Google Play Services may not work properly with the open source alternative.

(GrapheneOS offers a sandboxed version of real Google Play Services, which works with most, but not all apps)

### Level 2: rooted OS

The middle ground is rooting the phone, but keeping Google Play Services. Most apps keep working, but you get full access to the system: you can remove or freeze preinstalled apps, block trackers system-wide, make full backups, control permissions much more precisely.

It still requires unlocking the bootloader which is increasingly hard. Some of the apps that don't work on custom OSes dislike rooted phones too. There are ways to hide the fact that your phone is rooted, but it's a constant chase: something that works today may stop working after the next update.

### Level 1: normal OS with some tweaks

The easiest option is to keep the stock OS, just change some settings and replace specific apps with more privacy-friendly alternatives. You won't get full control this way. But it's much easier, so there's really no excuse not to do it.


## Where do we start?

With the easiest version. It's useful on its own, and most of it carries over to the more advanced levels anyway - even if you change the OS later, you'll still want the same replacement apps.

## Sources

### Google Play Services and AOSP

- [Google's iron grip on Android: Controlling open source by any means necessary](https://arstechnica.com/gadgets/2013/10/googles-iron-grip-on-android-controlling-open-source-by-any-means-necessary/) - Ars Technica
- [Google Play Services launches](https://thenextweb.com/google/2012/09/26/google-play-services-launches-help-developers-integrate-google-properties-like-g-apps/) - The Next Web
- [Social gaming, location and more in Google Play Services](https://android-developers.googleblog.com/2013/05/social-gaming-location-and-more-in.html) - Android Developers Blog
- [Commission fines Google €4.34 billion for illegal practices regarding Android mobile devices](https://ec.europa.eu/commission/presscorner/detail/en/IP_18_4581) - European Commission
- [Huawei braces for difficult 2020 after Q4 slowdown](https://www.lightreading.com/business-management/huawei-braces-for-difficult-2020-after-q4-slowdown) - Light Reading
- [AOSP release lifecycle](https://source.android.com/docs/setup/contribute/release-lifecycle) - Android Open Source Project
- [Android 16 AOSP release without Pixel device trees](https://9to5google.com/2025/06/12/android-open-source-project-pixel-change/) - 9to5Google
- [Android sideloading changes timeline](https://www.androidauthority.com/android-sideloading-changes-timeline-3679204/) - Android Authority
- [Play Integrity improved verdicts](https://developer.android.com/google/play/integrity/improvements) - Android Developers
- [SafetyNet Attestation API deprecation](https://developer.android.com/training/safetynet/attestation) - Android Developers
- [Attestation compatibility guide](https://grapheneos.org/articles/attestation-compatibility-guide) - GrapheneOS

### What about Chinese phones?

- [Google Play blocked in China](https://www.pcworld.com/article/436503/google-play-taps-chinese-developers-for-paid-apps-despite-block.html) - PCWorld
- [Lithuania warns against Xiaomi and Huawei smartphones](https://www.bitdefender.com/blog/hotforsecurity/lithuania-warns-firms-not-to-use-xiaomi-and-huawei-smartphones-after-investigation-finds-security-and-censorship-concerns/) - Bitdefender
- [Lithuania urges citizens to ditch Chinese smartphones](https://chinadigitaltimes.net/2021/09/lithuania-urges-citizens-to-ditch-chinese-smartphones-over-censorship-data-security-concerns/) - China Digital Times
- [The Not-So-Silent Type: vulnerabilities across keyboard apps](https://citizenlab.ca/2024/04/vulnerabilities-across-keyboard-apps-reveal-keystrokes-to-network-eavesdroppers/) - Citizen Lab

### Why not iPhone?

- [Apple may be tracking you through App Store even when privacy settings are turned off](https://www.computing.co.uk/news/4059931/apple-tracking-app-store-privacy-settings-report) - Computing
- [Apple rebrands its advertising business as Apple Ads](https://appleinsider.com/articles/25/04/14/apple-rebrands-its-advertising-business-as-apple-ads) - AppleInsider
- [Third-party iPhone app stores coming with iOS 17.4](https://9to5mac.com/2024/01/25/third-party-iphone-app-stores-ios-17-4/) - 9to5Mac
- [Apple removes VPN services from the App Store in China](https://salon.com/2017/07/29/apple-removes-vpn-services-from-the-app-store-in-china-report) - Salon
- [Apple's iCloud in China set to move to state-controlled data center](https://www.datacenterknowledge.com/cloud/apple-s-icloud-in-china-set-to-move-to-state-controlled-data-center) - Data Center Knowledge
- [Apple can no longer offer Advanced Data Protection in the United Kingdom to new users](https://support.apple.com/en-us/122234) - Apple Support
- ["We will never build a backdoor" - Apple kills iCloud's end-to-end encryption feature in the UK](https://www.techradar.com/computing/cyber-security/we-will-never-build-a-backdoor-apple-kills-its-iclouds-end-to-end-encryption-feature-in-the-uk) - TechRadar
