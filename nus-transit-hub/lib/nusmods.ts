import { ClassCommuteInfo, NUSModsLesson, NUSModsModule } from "./types";
import { getNextBusShuttleService } from "./nextbus";

const NUSMODS_BASE_URL = "https://api.nusmods.com/v2/2025-2026";

/**
 * Venue to Bus Stop Mapping Dictionary based on project rules.
 */
interface BusStopMapping {
  keywords: string[];
  code: string;
  caption: string;
}

const VENUE_MAPPINGS: BusStopMapping[] = [
  {
    keywords: ["COM1", "COM2", "COM3"],
    code: "COM3",
    caption: "COM 3",
  },
  {
    keywords: ["LT27", "S17", "SCIENCE"],
    code: "LT27",
    caption: "LT 27 / Science",
  },
  {
    keywords: ["UT", "UTOWN", "ERC"],
    code: "UTOWN",
    caption: "University Town",
  },
  {
    keywords: ["CLB", "LIBRARY", "AS"],
    code: "CLB",
    caption: "Central Library / FASS",
  },
  {
    keywords: ["BIZ1", "BIZ2", "HSSML"],
    code: "BIZ2",
    caption: "BIZ 2",
  },
  {
    keywords: ["EA", "E1", "E2", "ENG"],
    code: "EA",
    caption: "Engineering",
  },
  {
    keywords: ["KR-MRT", "KRMRT", "NUH"],
    code: "KR-MRT",
    caption: "Kent Ridge MRT",
  },
];

const FALLBACK_STOP = {
  code: "UTOWN",
  caption: "University Town",
};

/**
 * Maps a classroom venue code (e.g. 'COM3-01-23', 'LT27', 'E1-06-03') to its nearest bus stop.
 */
export function mapVenueToBusStop(venue: string): { code: string; caption: string } {
  if (!venue) return FALLBACK_STOP;
  const upper = venue.toUpperCase().replace(/[\s\-_]/g, "");

  for (const mapping of VENUE_MAPPINGS) {
    for (const kw of mapping.keywords) {
      const cleanKw = kw.replace(/[\s\-_]/g, "");
      // Check prefix or inclusion (e.g., COM3 in COM30123)
      if (upper.startsWith(cleanKw) || upper.includes(cleanKw)) {
        return {
          code: mapping.code,
          caption: mapping.caption,
        };
      }
    }
  }

  return FALLBACK_STOP;
}

/**
 * Fetch module details and timetable from NUSMods API.
 */
export async function getModuleData(moduleCode: string): Promise<NUSModsModule | null> {
  const cleanCode = (moduleCode || "").trim().toUpperCase();
  if (!cleanCode) return null;

  try {
    const res = await fetch(`${NUSMODS_BASE_URL}/modules/${encodeURIComponent(cleanCode)}.json`, {
      next: { revalidate: 86400 }, // Cache timetable for 24 hours
    });

    if (!res.ok) {
      // If 404 or error, return null
      return null;
    }

    return (await res.json()) as NUSModsModule;
  } catch (error) {
    console.error(`Failed to fetch NUSMods data for ${cleanCode}:`, error);
    return null;
  }
}

/**
 * Resolves the 1st lesson for a module, maps to the nearest bus stop, and queries live shuttle arrivals.
 */
export async function getFirstLessonCommute(
  moduleCode: string
): Promise<ClassCommuteInfo | null> {
  const modData = await getModuleData(moduleCode);
  if (!modData || !modData.semesterData || modData.semesterData.length === 0) {
    return null;
  }

  // Find semester with non-empty timetable
  let targetLesson: NUSModsLesson | null = null;
  for (const sem of modData.semesterData) {
    if (sem.timetable && sem.timetable.length > 0) {
      targetLesson = sem.timetable[0];
      break;
    }
  }

  if (!targetLesson) {
    return null;
  }

  const busStop = mapVenueToBusStop(targetLesson.venue);
  const liveShuttle = await getNextBusShuttleService(busStop.code);

  return {
    moduleCode: modData.moduleCode,
    moduleTitle: modData.title,
    lessonType: targetLesson.lessonType,
    classNo: targetLesson.classNo,
    day: targetLesson.day,
    startTime: targetLesson.startTime,
    endTime: targetLesson.endTime,
    venue: targetLesson.venue || "TBA",
    busStopCode: busStop.code,
    busStopCaption: busStop.caption,
    arrivals: liveShuttle.shuttles,
  };
}

