---
title: "Security and privacy tweaks for standard Android"
date: 2026-11-09T21:00:00
draft: false
tags: ["android", "privacy", "security"]
---

A standard Android system can be made much more secure, and a bit more privacy-friendly. The options are scattered across different menus and most of them are not enabled by default. Google is not going to encourage you to share less data with Google.

As usual, there are trade-offs: between security and convenience, and sometimes between security and privacy.

A note on menu paths: I'm describing Android 16 on my Samsung. Each Android version is a little bit different. If you can't find a setting, use the search bar at the top of Settings. Older Android versions may not have some of the options at all.

## Security basics

### 1. A proper screen lock

A pattern is easy to guess by looking at the smudges on the screen or over your shoulder. A standard 4-digit PIN is better, but a longer one, 6-8 digits, is considerably more secure. Fingerprint or face unlock makes it bearable - you'll only need to type it after a restart.

It matters more than it seems: on modern Android, the screen lock is also what protects the encryption of your data.

While you're there:

- **Lock screen notifications** - check if it's set to hide sensitive content. Otherwise anyone can read your messages without unlocking the phone. Modern systems should have it on by default (or even no way to show full messages).
- **Lockdown** - enable "Show lockdown option". It disables fingerprint and face unlock until you enter the PIN. Useful in situations where someone could force you to put your finger on the phone - it's much easier than forcing you to tell them your PIN.

### 2. Theft protection

An update to Google Play Services at the end of 2024 added a set of features against phone theft (Settings > Security & privacy > Lost device protection > Theft protection, or search for "theft"). It uses motion sensors to detect someone snatching the phone from your hand and running away, and locks the screen. There are also two other options here:

- **Offline Device Lock** - locks the screen if the phone is disconnected from the network for too long (thieves like to turn on airplane mode).
- **Identity Check** - requires biometrics for sensitive actions, like changing the screen lock or disabling Find My Device (available on Android 15 and higher).

These options are almost free of inconvenience. A false positive just means you have to unlock your phone with a fingerprint.


### 3. Updates

Probably the most important security setting. There are two kinds:

- **Operating system update** - the monthly patch from the phone maker. Look at the date. If it's more than a few months old and there's nothing new to install, your phone may be out of support.
- **Google Play (and other stores) update** - applications plus software frameworks.

Generally, you should install both as soon as they show up. Yes, there might be side effects, new UI could be inconvenient or in rare cases something might break. Perhaps updating the OS right before a journey is not the best timing (though make sure your airline's app is up to date, before you discover your version won't display the boarding card - I'm looking at you Ryanair). But updates fix known vulnerabilities. If you lose your data due to an unpatched app, you only have yourself to blame.

If your phone doesn't get operating system updates any more, no setting will fix that - it's time to think about a new phone (or a custom OS that still supports it, but that's a more advanced topic).

### 4. Scheduled restart every night

You might be surprised what it has to do with security. Most Android malware, even the expensive spyware such as Pegasus, doesn't survive a reboot. Staying on the phone after a restart (persistence) is hard on a modern Android with verified boot, and attackers usually assume phones stay on for months. Automatically restarting the phone every night is the best and easiest form of damage control.

There's a second security benefit. Right after a restart, before you enter the PIN for the first time, the phone is in the "Before First Unlock" state: the encryption keys are not in memory, and most of your data can't be read even by forensic tools - even those used by security agencies. After the first unlock, the keys stay in memory until the next reboot, even when the screen is locked.

And a side effect: a freshly restarted phone is more responsive. Memory leaks and stuck background processes that keep using the CPU all get cleaned up.

This option tends to have different names, so search for "restart" in the settings. Some phones don't have it, you might try a 3rd party app.

**Limitations:**

- **Before the first unlock, the phone is half-asleep.** Calls work, but most apps can't access their data, so messaging apps won't show notifications until you enter the PIN. If the phone restarts at 3 a.m., you won't get any messages until you pick it up in the morning.
- **Alarms.** The built-in clock app works, but third-party alarm apps might not. Test it before you rely on it - preferably not on a day with an early flight.
- **SIM PIN.** If your SIM card has a PIN, the phone won't connect to the mobile network after a restart until you enter it. Pick a restart time when you'll pick up the phone soon after, or don't use a SIM PIN.
- **It doesn't help against "normal" malware.** A malicious app you installed yourself just starts again after the restart. Rebooting only helps against infections that live in memory.
- **Long-running things get interrupted.** Most apps that should be always on (e.g. those that sync files in the background or connect to devices) will be automatically restarted, but no guarantee.

For me, the balance was on the positive side, but do your own assessment. You might also choose a different schedule, e.g. one restart per week.

### 5. Consider using Advanced Protection

Android 16 has a single switch that turns on a bundle of stricter security settings: Settings > Security & privacy > Advanced Protection. Among other things, it blocks installing apps from outside the Play Store, blocks 2G networks, turns on theft protection and blocks USB data connection when the phone is locked. It also restarts the phone every 3 days - see, I'm not the only one who recommends it.

It's designed for people likely to be targeted, especially those living in places where journalists and activists might come under scrutiny (which, these deys, probably means Earth). **I don't use it**, because it blocks installing apps from [F-Droid](/android/f-droid/) - and that's a deal breaker for me. But if you don't need any apps from outside the Play Store, it's an easy win. Otherwise, you can enable some of its parts separately, which is what the rest of this post does.

## Permissions

### 6. Review app permissions

Settings > Security & privacy > Privacy > Permission manager shows permissions grouped by type: who has access to your location, camera, microphone, contacts, files. Go through the list. You'll probably find a few surprises, like a game that has access to your contacts.

A few rules of thumb:

- **Location** - "Allow only while using the app" is enough for almost everything. Very few apps need it all the time (fitness trackers, maybe). And many apps don't need a precise location at all - a weather app works fine with "approximate", which is accurate only to a few kilometres.
- **Photos and videos** - since Android 14, you can give an app access to selected photos only, instead of the whole gallery. Use it.
- **Contacts, call logs, SMS** - should be granted only to apps that obviously need them (phone, messaging). Many apps want to know your contacts "to see which of your friends also use it". Keep in mind that by sharing your contacts, you also compromise the privacy of other people.
- **Nearby devices** - many apps ask for it, few need it.

There's also the Privacy dashboard (Settings > Security & privacy > Privacy > Privacy dashboard), which shows which apps actually used location, camera and microphone in the last 24 hours (7 days on newer versions). It's a good way to find apps that use permissions more than you'd expect.

### 7. Accessibility permissions

Apps designed for people with disabilities have very broad permissions and bypass some of the standard security measures. For example, most banking and identity apps don't allow to read screen contents (screenshot wouldn't work), but a screen reader needs to read them anyway. Malware often uses this route. 

Search the settings for accessibility. If you don't use accessibility apps, make sure they are disabled. Also, if something shows up, but it's not made by your phone's manufacturer, be extremely wary. It might be disguised malware.

### 8. Remove permissions from unused apps

Android can automatically revoke permissions from apps you haven't used for a few months. It's usually on by default, but some apps disable it for themselves, and you can check it per app: open the app info > "Manage app if unused" (or "Remove permissions if app isn't used", depending on the version).

Even better: uninstall apps you don't use. Every installed app is a potential leak and a potential vulnerability.

## Google and ads

### 9. Delete the advertising ID

Android gives every phone an advertising ID - a unique identifier which apps can read to track you across apps and build an advertising profile. Settings > Security & privacy > Privacy > Ads > Delete advertising ID. After that, apps get a string of zeros instead.

On the same screen (or in "Ad privacy", depending on the version) there are options for ad topics and app-suggested ads - Google's "privacy-friendly" replacements for tracking. Turn them off too. You'll still see ads, they'll just be less personalised.

### 10. Google account activity

A lot of tracking happens on the Google account level, not on the phone. Settings > Google > Manage your Google Account > Data & privacy, or go to [myactivity.google.com](https://myactivity.google.com/) in a browser:

- **Web & App Activity** - your searches, Chrome history (if synced), activity in Google apps and in many third-party apps that use Google services. Turn it off, or at least set auto-delete to 3 months.
- **Timeline** (formerly Location History) - since 2024 it's stored on the phone, not on Google's servers, which is a big improvement. It's a trade-off - checking a past location is occasionally useful ("where did I see this shop?" "where was I when I lost my keys?") - unless, of course, someone else checks it.
- **YouTube History** - in theory, recommendations should get worse without it, but in my experience they're better - YouTube recommends content based on what you're watching at the moment, instead of what it thinks is interesting for you. Or just use [NewPipe](/android/fdroid-apps/#2-newpipe-instead-of-the-youtube-app).
- **Personalised ads** - in My Ad Center, turn it off.

It's also worth taking a look at what Google already has. Google Takeout allows you to download all of it. Be prepared, it can be a lot.

### 11. Usage and diagnostics

Settings > Security & privacy > Privacy > Usage & diagnostics. Turn it off - it sends Google information about how you use your phone, battery levels, app usage and crash reports.

Phone makers often have their own version of this. On Samsung, for example, there's "Customisation Service", diagnostic data and marketing information, usually agreed to during the initial setup. Search for "diagnostic" and "customisation" in Settings.

### 12. Assistant and Gemini

If you don't use a voice assistant, disable "Hey Google" / voice match so that the phone doesn't listen for the wake word. And since Gemini is replacing Assistant, check Gemini Apps Activity in your Google account - by default, conversations are stored and may be reviewed by humans to improve the product. A reasonable middle ground: allow it when your phone is connected to the car, so you can use it hands-free.

### 13. Keyboard

The keyboard sees everything you type: passwords, messages, searches. Gboard is actually not the worst offender - it does most of its learning on the phone. But check Gboard settings > Privacy and turn off "Share usage statistics" and the options for improving Gboard for everyone. Gboard also has incognito mode when it doesn't send text to Google. It turns on automatically on password entry fields and such. Unfortunately, you can't make it always on.

Third-party keyboards can be much worse. As mentioned in the intro, Citizen Lab found that many popular keyboards (mostly Chinese ones) sent keystrokes over the network with weak or no encryption. If you want to be sure, HeliBoard from F-Droid is a decent offline keyboard. It doesn't have network permission at all, so it can't leak anything. The downside: swipe typing requires a separate, closed-source library and word hints are worse.

## Network

### 14. MAC randomisation

Android can use a random MAC address for each network, so you can't be tracked between networks. New versions have it on by default. Make sure it's on for all saved networks (Wi-Fi > network settings > Privacy > "Use randomised MAC").

For the home network I switched it off, so that my router always gives my phone the same IP address.

### 15. More Wi-Fi and Bluetooth settings

- **Wi-Fi and Bluetooth scanning** - Settings > Location > Location services. With these on, the phone keeps scanning for networks and devices even when Wi-Fi and Bluetooth are turned off, to improve location accuracy. Turn them off. Same for **Google Location Accuracy**, which sends nearby Wi-Fi networks and cell towers to Google. GPS works fine without it, just takes a bit longer to find you.
- **Auto-connect to open networks** - turn off "Connect to public networks" in Wi-Fi preferences. On recent Android it's off by default.

### 16. Disable 2G

2G is an ancient standard with broken encryption, and it doesn't even authenticate the network. Fake base stations (IMSI catchers, "stingrays") work by forcing phones to downgrade to 2G. Most countries have switched off 2G already or are in the process. If you're in one of them, turn off Settings > Network & internet > SIMs > "Allow 2G".

The only downside is that in rare places without 4G/5G coverage, you may have no signal.

## Things I leave on

As I said, there are always trade-offs. I decided to keep some things on, even though they send the data:

- **Google Play Protect** - scans installed apps for malware. It sends information about your apps to Google, but it does detect malware quite accurately. It occasionally complains about F-Droid apps, but you can ignore that.
- **Find Hub (Find My Device)** - being able to locate, lock or wipe a lost phone is worth more to me than the privacy cost.
- **Emergency Location Service** - sends your location to emergency services when you call them. Only then.
- **Backup** - Google says that some of the backups of app data, call history, SMS and settings are end-to-end encrypted with your screen lock, so Google can't read them. Which part? That's vague, we know that Photos and MMS are not and can't be sure about the rest.

## Summary

None of this makes stock Android private. Google Play Services still runs with all its permissions, and most of what you do still passes through Google's servers in one way or another. But it's half an hour of clicking, it removes the worst leaks and closes some real security holes. Plus, knowing where these settings are helps on any Android phone, including those with a custom OS.

## Sources

### Security basics

- [New Android theft protection feature updates](https://security.googleblog.com/2024/10/android-theft-protection.html) - Google Security Blog
- [Mobile Security Alert: NSA Recommends Weekly Smartphone Reboots](https://zimperium.com/blog/mobile-security-alert-nsa-recommends-weekly-smartphone-reboots) - Zimperium
- [Improve device security with Advanced Protection for Android](https://support.google.com/android/answer/16339980?hl=en) - Google Help
- [Android Advanced Protection: what it is and how to use it](https://www.androidauthority.com/android-advanced-protection-3556885) - Android Authority

### Permissions

- [Grant partial access to photos and videos](https://developer.android.com/about/versions/14/changes/partial-photo-video-access) - Android Developers
- [Privacy dashboard gets a 7-day view](https://www.androidauthority.com/privacy-dashboard-7-day-3507535/) - Android Authority

### Google and ads

- [Advertising ID](https://support.google.com/googleplay/android-developer/answer/6048248?hl=en) - Google Play Console Help
- [Google will store Location History and Timeline on your device](https://9to5google.com/2023/12/12/google-location-history-timeline-device/) - 9to5Google
- [Gemini Apps Privacy Hub](https://support.google.com/gemini/answer/13594961?hl=en) - Google Help
- [Google Gemini keeps reviewed chats for three years](https://www.notebookcheck.net/Google-Gemini-keeps-reviewed-chats-for-three-years.1389300.0.html) - Notebookcheck
- [Major security flaws expose keystrokes of over 1 billion Chinese keyboard app users](https://thehackernews.com/2024/04/major-security-flaws-expose-keystrokes.html) - The Hacker News
- [The Not-So-Silent Type: vulnerabilities across keyboard apps (PDF)](https://citizenlab.ca/wp-content/uploads/2025/12/Report175-keyboardvuln-050824.pdf) - Citizen Lab
- [HeliBoard](https://github.com/HeliBorg/HeliBoard) - GitHub

### Network

- [Android users can now disable 2G to block Stingray attacks](https://www.bleepingcomputer.com/news/security/android-users-can-now-disable-2g-to-block-stingray-attacks) - BleepingComputer
- [Google recommends disabling 2G on Android](https://9to5google.com/2024/08/01/android-disable-2g/) - 9to5Google

### Things I leave on

- [Find My Device is now Find Hub](https://www.androidauthority.com/find-hub-3557104/) - Android Authority
- [Back up or restore data on your Android device](https://support.google.com/android/answer/2819582?hl=en-GB) - Google Help
