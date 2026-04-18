# ReserveBot 🍕

Automated restaurant booking app — currently configured for **Pizza 4P's Indiranagar** (Bengaluru).

## How It Works

1. **GitHub Actions** runs `pizza4ps_book.py` every day at **10:00 AM IST**
2. The script opens Pizza 4P's TableCheck page and tries **84 combinations** (7 days × 12 time slots)
3. If a slot is found → fills your details → confirms booking → emails you
4. If no slots → emails you a summary + screenshots

## Strategy

- Tries **Fri/Sat/Sun first**, then weekdays
- Time priorities: 12:00, 12:30, 1:00, 1:30, 7:00, 7:30, 8:00, 8:30, plus fallbacks
- Handles seating selection (Indoor/Balcony/Pizza Counter)
- Takes screenshots at each step for debugging

## Setup

### 1. GitHub Secrets (Settings → Secrets → Actions)

| Secret | Value |
|---|---|
| `BOOKING_FIRST_NAME` | Your first name |
| `BOOKING_LAST_NAME` | Your last name |
| `BOOKING_EMAIL` | Your email |
| `BOOKING_PHONE` | Your phone number |
| `GMAIL_USER` | Gmail address for notifications |
| `GMAIL_APP_PASSWORD` | Gmail app password |

### 2. That's it!

The workflow runs automatically every day. You can also trigger it manually from the [Actions tab](https://github.com/maxthecat2024/naru-booking/actions).

## Mobile App

The repo also contains a React Native (Expo) mobile app for monitoring and triggering bookings from your phone.

- **Android APK**: Download from [Actions → Build Mobile Apps](https://github.com/maxthecat2024/naru-booking/actions/workflows/build-mobile-apps.yml) artifacts
- **iOS**: Build locally with `npx expo run:ios`
