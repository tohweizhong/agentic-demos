# NUS Transit Hub Project Rules

## Tech Stack & Conventions
- Framework: Next.js 14 App Router with TypeScript and Tailwind CSS.
- Telegram Bot: Use `grammY` library. Support hybrid mode: local polling script (`scripts/bot-dev.ts`) and Vercel serverless webhook (`app/api/telegram/route.ts`).
- NPM Scripts: Preserve all default Next.js scripts (`"dev": "next dev"`, `build`, `start`, `lint`) and add `"bot:dev": "tsx scripts/bot-dev.ts"` to `package.json`.
- API Integrations:
  - NUS NextBus API: Base URL `https://nnextbus.nus.edu.sg/` with HTTP Basic Authentication (`NEXTBUS_USERNAME` / `NEXTBUS_PASSWORD`).
  - NUSMods API: Base URL `https://api.nusmods.com/v2/2025-2026/` (No auth required).

## Venue to Bus Stop Mapping Dictionary
Map classroom venue codes to nearest bus stops:
- `COM1`, `COM2`, `COM3` -> `COM 3` (`COM3`)
- `LT27`, `S17`, `SCIENCE` -> `LT 27 / Science` (`LT27`)
- `UT`, `UTOWN`, `ERC` -> `University Town` (`UTOWN`)
- `CLB`, `LIBRARY`, `AS` -> `Central Library / FASS` (`CLB`)
- `BIZ1`, `BIZ2`, `HSSML` -> `BIZ 2` (`BIZ2`)
- `EA`, `E1`, `E2`, `ENG` -> `Engineering` (`EA`)
- `KR-MRT`, `NUH` -> `Kent Ridge MRT` (`KR-MRT`)
- Fallback: `University Town` (`UTOWN`)

## Telegram Bot Feature Specifications
- `/start`: Welcome message with inline quick-action buttons for popular stops (`UTOWN`, `COM3`, `KR-MRT`, `CLB`).
- `/bus <stop>`: Formatted ETA list with visual urgency badges (🟢 <=3 min, 🟡 4-8 min, 🔴 >8 min / out of service).
- `/disruptions`: List of active vehicle breakdowns and transit advisories with HTML stripped.
- `/class <moduleCode>`: Queries NUSMods timetable, extracts 1st lesson day/time/venue, resolves nearest bus stop, and appends live shuttle arrivals.
- Inline Keyboard: Clicking a quick stop button returns live bus timings instantly.

## Web Dashboard Specifications
- Header with live badge and auto-refresh countdown timer (20s interval).
- Top Disruption Alert Banner displaying active announcements.
- Stop Selector Buttons for popular stops (UTown, COM 3, Kent Ridge MRT, Central Library, LT 27, BIZ 2).
- Responsive Shuttle Arrival Grid with countdown badges and bus plate numbers.
- Smart Commute Search Bar: Input module code (e.g. `CS2030S`) to display lesson schedule, venue, mapped bus stop, and nearby shuttle arrivals.

## Error Handling & Robustness
- Gracefully handle off-service hours (e.g. late night) with friendly messages.
- Filter out HTML tags from announcements.
- Strict TypeScript interfaces for all payloads. Avoid `any`.
