# 🤖 ReserveBot — Mobile App + GitHub Actions

Automated booking agent for Naru Noodle Bar & Pizza 4P's (Bengaluru).
Cross-platform mobile app (iOS + Android) built with Expo/React Native.

---

## 📱 Mobile App — Quick Start

### Prerequisites
- Node.js 18+
- [Expo Go](https://expo.dev/client) installed on your phone (free, App Store / Play Store)

### Run in 3 commands
```bash
npm install -g expo-cli       # once
npm install                   # inside this folder
npx expo start                # scan QR with Expo Go
```

Scan the QR code in your terminal with Expo Go. The app opens instantly on your phone.

### What the app does
- **Home** — dashboard showing all your agents, live countdown timers, status badges, on/off toggle
- **Agent screen** — full configuration: your name/phone/email, party size, preferred days, time slots, special requests, GitHub repo link, run history
- **Add screen** — add any restaurant with custom emoji, colour, schedule, and your details

### Build for real install (optional)
```bash
npx expo build:ios      # requires Apple Developer account
npx expo build:android  # generates .apk you can sideload
```
Or use [EAS Build](https://docs.expo.dev/build/introduction/) for free cloud builds.

---

## ⚙️ GitHub Actions — Pizza 4P's

### Files to add to your GitHub repo (`naru-booking` or a new repo)

| File | Where to put it |
|------|----------------|
| `pizza4ps_book.py` | repo root |
| `pizza4ps-booking.yml` | `.github/workflows/` |

### Schedule
- Runs **every day at 10:00 AM IST** (4:30 UTC)
- Books next available **Friday, Saturday, or Sunday**
- Preferred slots: 12 PM → 1 PM → 7 PM → 8 PM
- Party of 2 (configured via GitHub Secrets)

### Secrets needed (same as Naru)
`GMAIL_USER` and `GMAIL_APP_PASSWORD` — already set in your `naru-booking` repo ✅

### Manual test
Actions tab → Pizza 4Ps Booking Agent → Run workflow

---

## 📦 Download Mobile App (Android APK)

You can download the latest version of the app directly from this GitHub repository!

1.  Go to the **Actions** tab at the top of the repo.
2.  Click on the latest run titled **"Build Mobile Apps"**.
3.  Scroll down to the **"Artifacts"** section.
4.  Download the `reservebot-android-apk` zip file.
5.  Extract it and install the `.apk` file on your Android phone!

---

## 🍜 Naru + 🍕 Pizza 4P's — side by side

| | Naru | Pizza 4P's |
|--|--|--|
| Booking system | AirMenus | TableCheck |
| Window | Monday 8 PM IST | Daily 10 AM IST |
| Fills up | ~90 seconds | Same day |
| Party | 1 | 2 |
| Script | `naru_book.py` | `pizza4ps_book.py` |
| Workflow | `naru-booking.yml` | `pizza4ps-booking.yml` |
