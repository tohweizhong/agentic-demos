# NUS Campus Transit Hub & Telegram Bot

An intelligent, real-time campus transit dashboard and Telegram bot for the National University of Singapore (NUS). Built with **Next.js 16 (App Router)**, **TypeScript**, **Tailwind CSS**, and **grammY**.

Live Web Dashboard: [https://nus-transit-hub-tau.vercel.app](https://nus-transit-hub-tau.vercel.app)  
Live Telegram Bot: [@nus_transit_wz_bot](https://t.me/nus_transit_wz_bot)

---

## 🚀 Key Features

1. **Modern Transit Departure Board UI**:
   - Airport/rail style departure terminal interface with dark OLED/zinc styling (`#090a0f`) and subtle ambient glows.
   - Live Singapore Standard Time (SGT) digital clock synced every second.
   - SVG circular countdown timer for the 20-second telemetry refresh interval.
   - Glowing urgency indicators: 🟢 Imminent (`<=3 min`), 🟡 Approaching (`4-8 min`), 🔴 Delayed / Off-Service (`>8 min`).
   - Bus vehicle plate numbers and passenger occupancy indicators.
   - Active transit disruption ticker with affected service badges (`A1`, `D1`, `K`, `R1`).

2. **Smart Commute Console (NUSMods Timetable Integration)**:
   - Search any NUS module code (e.g., `CS2030S`, `CS1101S`, `MA1521`).
   - Automatically resolves lesson timetable, day, time, and assigned lecture/tutorial venue.
   - Maps venues directly to the nearest NUS shuttle stop (e.g. `COM1-3` → `COM 3`, `UTOWN/ERC` → `UTown`, `LT27` → `LT 27 / Science`, `BIZ` → `BIZ 2`).
   - Displays a styled "Commute Boarding Pass" with live connecting shuttle buses at that stop.

3. **Hybrid Telegram Bot**:
   - Built with `grammY`.
   - **Production Mode**: Serverless webhook hosted at `app/api/telegram/route.ts` on Vercel (`std/http` adapter).
   - **Local Dev Mode**: Long-polling script via `npm run bot:dev`.
   - **Commands & Natural Input**:
     - Registered Telegram command menu: `/bus`, `/class`, `/disruptions`, `/start`.
     - Direct text input (no slash needed): type `UTOWN`, `COM3`, or module codes like `CS2030S` directly in chat!
     - Interactive inline keyboard for 1-tap quick stop timings.

---

## 🛠 Tech Stack

- **Framework**: Next.js 16 (App Router) with TypeScript & React 19
- **Styling**: Tailwind CSS v4 & Lucide Icons
- **Telegram Bot**: grammY (`grammy`)
- **APIs**:
  - **NUS NextBus API**: `https://nnextbus.nus.edu.sg/` (Basic Auth with public credentials)
  - **NUSMods API**: `https://api.nusmods.com/v2/2025-2026/` (Module timetables & venues)

---

## 📦 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Setup
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```
Fill in your credentials:
```env
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
NEXTBUS_USERNAME="NUSnextbus"
NEXTBUS_PASSWORD='13dL?zY,3feWR^"T'
```

### 3. Run Web Dashboard Locally
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Run Telegram Bot Locally (Polling Mode)
```bash
npm run bot:dev
```

---

## 🌐 Deploy to Vercel

```bash
# Deploy to production
npx vercel --prod
```

Configure environment variables in Vercel Project Settings:
- `TELEGRAM_BOT_TOKEN`
- `NEXTBUS_USERNAME`
- `NEXTBUS_PASSWORD`

Set the Telegram Webhook:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<YOUR-VERCEL-DOMAIN>/api/telegram"
```
