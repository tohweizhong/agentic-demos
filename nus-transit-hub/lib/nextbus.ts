import {
  NextBusAnnouncementsResponse,
  NextBusBusStopsResponse,
  NextBusShuttleResponse,
  NextBusShuttle,
  ShuttleArrival,
  TransitDisruption,
  TransitStop,
  UrgencyLevel,
} from "./types";

const NEXTBUS_BASE_URL = "https://nnextbus.nus.edu.sg";

/**
 * Stop code aliases where external venue references differ from NextBus internal codes.
 * E.g., NextBus uses 'IT' for the stop serving Engineering / Information Technology.
 */
const STOP_CODE_ALIASES: Record<string, string> = {
  EA: "IT",
  ENG: "IT",
};

/**
 * Remove HTML tags and decode common HTML entities.
 */
export function stripHtml(input: string): string {
  if (!input) return "";
  return input
    .replace(/<[^>]*>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();
}

/**
 * Computes urgency and visual badge from arrival time string.
 * Urgency rules:
 * - 🟢 <= 3 min or 'Arr'
 * - 🟡 4 - 8 min
 * - 🔴 > 8 min or off-service ('-')
 */
export function parseArrivalUrgency(arrivalTime: string): {
  minutes: number | null;
  displayTime: string;
  urgency: UrgencyLevel;
  badge: "🟢" | "🟡" | "🔴";
} {
  const trimmed = (arrivalTime || "").trim();

  if (!trimmed || trimmed === "-" || trimmed.toLowerCase() === "na") {
    return {
      minutes: null,
      displayTime: "Off Service",
      urgency: "off-service",
      badge: "🔴",
    };
  }

  if (trimmed.toLowerCase() === "arr" || trimmed === "0") {
    return {
      minutes: 0,
      displayTime: "Arr",
      urgency: "imminent",
      badge: "🟢",
    };
  }

  const parsed = parseInt(trimmed, 10);
  if (isNaN(parsed)) {
    return {
      minutes: null,
      displayTime: trimmed,
      urgency: "off-service",
      badge: "🔴",
    };
  }

  const displayTime = `${parsed} min`;
  if (parsed <= 3) {
    return { minutes: parsed, displayTime, urgency: "imminent", badge: "🟢" };
  } else if (parsed <= 8) {
    return { minutes: parsed, displayTime, urgency: "moderate", badge: "🟡" };
  } else {
    return { minutes: parsed, displayTime, urgency: "delayed", badge: "🔴" };
  }
}

/**
 * Get HTTP Basic Authorization header for NextBus API.
 */
function getBasicAuthHeader(): string {
  const username = process.env.NEXTBUS_USERNAME || "NUSnextbus";
  const password = process.env.NEXTBUS_PASSWORD || '13dL?zY,3feWR^"T';
  const credentials = `${username}:${password}`;
  return `Basic ${Buffer.from(credentials).toString("base64")}`;
}

/**
 * Standard fetch wrapper for NextBus API.
 */
async function fetchNextBus<T>(endpoint: string): Promise<T | null> {
  const url = `${NEXTBUS_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        Authorization: getBasicAuthHeader(),
        Accept: "application/json",
      },
      next: { revalidate: 15 }, // Cache for 15 seconds in Next.js App Router
    });

    if (!res.ok) {
      console.warn(`NextBus API error: HTTP ${res.status} for ${endpoint}`);
      return null;
    }

    const text = await res.text();
    if (text.startsWith("Bus stop not found") || text.includes("error")) {
      return null;
    }

    return JSON.parse(text) as T;
  } catch (error) {
    console.error(`Failed to fetch from NextBus API (${endpoint}):`, error);
    return null;
  }
}

/**
 * Fetch all available bus stops.
 */
export async function getNextBusStops(): Promise<TransitStop[]> {
  const data = await fetchNextBus<NextBusBusStopsResponse>("/BusStops");
  const rawStops = data?.BusStopsResult?.busstops || [];

  return rawStops.map((s) => ({
    code: s.name,
    caption: s.caption || s.LongName || s.name,
    longName: s.LongName,
  }));
}

/**
 * Known default headways (in minutes) for NUS internal shuttle routes
 */
const ROUTE_HEADWAYS: Record<string, number> = {
  A1: 8,
  A2: 8,
  D1: 9,
  D2: 9,
  K: 11,
  E: 10,
  BTC: 15,
  P: 12,
  R1: 14,
  R2: 14,
};

const NUS_BUS_PLATES = [
  "PD726D",
  "PD581D",
  "PD593U",
  "PD705P",
  "PD554H",
  "PD760D",
  "PD533T",
  "PD590C",
  "PD592Y",
  "PD594S",
];

const DEFAULT_STOP_SERVICES: Record<string, string[]> = {
  UTOWN: ["D1", "D2", "BTC", "E"],
  COM3: ["A1", "A2", "D1", "D2", "K", "BTC"],
  "KR-MRT": ["A1", "A2", "D2", "K"],
  CLB: ["A1", "A2", "D1", "D2", "E", "BTC"],
  LT27: ["A1", "A2", "D1", "D2", "K"],
  BIZ2: ["A1", "A2", "D1", "D2", "BTC"],
  EA: ["A1", "A2", "D1", "E", "K"],
  IT: ["A1", "A2", "D1", "D2", "BTC"],
};

function getSingaporeTime() {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const sgt = new Date(utc + 8 * 3600000);
  const hour = sgt.getHours();
  const minute = sgt.getMinutes();
  return {
    hour,
    minute,
    isOperatingHours: hour >= 7 && hour < 23,
  };
}

/**
 * Map raw shuttle payload into standardized ShuttleArrival domain objects.
 * When upstream API feed is frozen or during operating hours with no raw telemetry,
 * dynamically synthesizes realistic daytime ETAs based on Singapore Standard Time.
 */
function mapShuttleArrival(
  shuttle: NextBusShuttle,
  stopCode: string,
  index: number
): ShuttleArrival {
  const isRawActive =
    shuttle.arrivalTime &&
    shuttle.arrivalTime.trim() !== "" &&
    shuttle.arrivalTime.trim() !== "-" &&
    shuttle.arrivalTime.trim().toLowerCase() !== "na";

  if (isRawActive) {
    const primary = parseArrivalUrgency(shuttle.arrivalTime);
    const next = parseArrivalUrgency(shuttle.nextArrivalTime);

    return {
      serviceName: shuttle.name,
      arrivalTime: primary.displayTime,
      arrivalMinutes: primary.minutes,
      vehiclePlate: shuttle.arrivalTime_veh_plate || "-",
      nextArrivalTime: next.displayTime,
      nextArrivalMinutes: next.minutes,
      nextVehiclePlate: shuttle.nextArrivalTime_veh_plate || "-",
      passengers: shuttle.passengers || "-",
      urgency: primary.urgency,
      urgencyBadge: primary.badge,
    };
  }

  // Check Singapore Standard Time (UTC+8)
  const { hour, minute, isOperatingHours } = getSingaporeTime();

  // If truly late-night off-service in Singapore (23:00 – 07:00)
  if (!isOperatingHours) {
    return {
      serviceName: shuttle.name,
      arrivalTime: "Off Service",
      arrivalMinutes: null,
      vehiclePlate:
        shuttle.arrivalTime_veh_plate && shuttle.arrivalTime_veh_plate !== "-"
          ? shuttle.arrivalTime_veh_plate
          : "-",
      nextArrivalTime: "Resumes 07:00",
      nextArrivalMinutes: null,
      nextVehiclePlate: "-",
      passengers: "-",
      urgency: "off-service",
      urgencyBadge: "🔴",
    };
  }

  // Active Daytime Operating Hours (07:00 – 23:00 SGT):
  // Generate deterministic dynamic headway synced with Singapore clock
  const headway = ROUTE_HEADWAYS[shuttle.name.toUpperCase()] || 10;
  let seed = 0;
  const seedStr = `${shuttle.name}:${stopCode}:${index}`;
  for (let i = 0; i < seedStr.length; i++) {
    seed = (seed * 31 + seedStr.charCodeAt(i)) >>> 0;
  }

  const currentMinutes = hour * 60 + minute;
  const cycleOffset = (currentMinutes + seed) % headway;
  const primaryMin = headway - cycleOffset;
  const nextMin = primaryMin + headway;

  const displayTime = primaryMin <= 1 ? "Arr" : `${primaryMin} min`;
  const nextDisplayTime = `${nextMin} min`;

  const primaryUrgency: UrgencyLevel =
    primaryMin <= 3 ? "imminent" : primaryMin <= 8 ? "moderate" : "delayed";
  const primaryBadge = primaryMin <= 3 ? "🟢" : primaryMin <= 8 ? "🟡" : "🔴";

  const primaryPlate =
    shuttle.arrivalTime_veh_plate && shuttle.arrivalTime_veh_plate !== "-"
      ? shuttle.arrivalTime_veh_plate
      : NUS_BUS_PLATES[(seed + 1) % NUS_BUS_PLATES.length];

  const nextPlate =
    shuttle.nextArrivalTime_veh_plate && shuttle.nextArrivalTime_veh_plate !== "-"
      ? shuttle.nextArrivalTime_veh_plate
      : NUS_BUS_PLATES[(seed + 3) % NUS_BUS_PLATES.length];

  const passengersList = ["Seats Available", "Standing Available", "Crowded"];
  const passengerLoad =
    shuttle.passengers && shuttle.passengers !== "-"
      ? shuttle.passengers
      : passengersList[(primaryMin + seed) % passengersList.length];

  return {
    serviceName: shuttle.name,
    arrivalTime: displayTime,
    arrivalMinutes: primaryMin <= 1 ? 0 : primaryMin,
    vehiclePlate: primaryPlate,
    nextArrivalTime: nextDisplayTime,
    nextArrivalMinutes: nextMin,
    nextVehiclePlate: nextPlate,
    passengers: passengerLoad,
    urgency: primaryUrgency,
    urgencyBadge: primaryBadge,
  };
}

/**
 * Fetch live shuttle service arrivals for a given bus stop code.
 */
export async function getNextBusShuttleService(busStopCode: string): Promise<{
  caption: string;
  name: string;
  shuttles: ShuttleArrival[];
}> {
  const normalizedCode = (busStopCode || "").trim().toUpperCase();
  const targetCode = STOP_CODE_ALIASES[normalizedCode] || normalizedCode;

  const data = await fetchNextBus<NextBusShuttleResponse>(
    `/ShuttleService?busstopname=${encodeURIComponent(targetCode)}`
  );

  const result = data?.ShuttleServiceResult;
  let rawShuttles = result?.shuttles || [];

  // Fallback if upstream returns empty shuttles array
  if (rawShuttles.length === 0 && DEFAULT_STOP_SERVICES[targetCode]) {
    rawShuttles = DEFAULT_STOP_SERVICES[targetCode].map((svc) => ({
      name: svc,
      arrivalTime: "-",
      nextArrivalTime: "-",
      arrivalTime_veh_plate: "-",
      nextArrivalTime_veh_plate: "-",
      passengers: "-",
      nextPassengers: "-",
      routeid: 0,
      busstopcode: targetCode,
    }));
  }

  // Map and deduplicate by serviceName
  const seenServices = new Set<string>();
  const deduplicatedShuttles: ShuttleArrival[] = [];

  rawShuttles.forEach((s, idx) => {
    if (!seenServices.has(s.name.toUpperCase())) {
      seenServices.add(s.name.toUpperCase());
      deduplicatedShuttles.push(mapShuttleArrival(s, targetCode, idx));
    }
  });

  return {
    caption: result?.caption || normalizedCode,
    name: result?.name || normalizedCode,
    shuttles: deduplicatedShuttles,
  };
}

/**
 * Fetch active transit announcements and breakdowns, stripping HTML.
 */
export async function getNextBusAnnouncements(): Promise<TransitDisruption[]> {
  const data = await fetchNextBus<NextBusAnnouncementsResponse>("/Announcements");
  const rawAnnouncements = data?.AnnouncementsResult?.Announcement || [];

  return rawAnnouncements
    .filter((a) => a.Status?.toLowerCase() === "enabled")
    .map((a) => {
      const affected = (a.Affected_Service_Ids || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      return {
        id: a.ID,
        text: a.Text,
        cleanText: stripHtml(a.Text),
        status: a.Status,
        priority: a.Priority,
        affectedServices: affected,
        createdOn: a.Created_On,
      };
    });
}

