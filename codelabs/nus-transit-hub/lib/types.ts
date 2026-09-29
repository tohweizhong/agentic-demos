/**
 * TypeScript interfaces for NUS NextBus, NUSMods, and internal transit models.
 */

// ==========================================
// NextBus API Raw Payload Types
// ==========================================

export interface NextBusStop {
  caption: string;
  name: string;
  LongName: string;
  ShortName: string;
  latitude: number;
  longitude: number;
}

export interface NextBusEta {
  plate: string;
  px: string;
  ts: string;
  jobid: number;
  eta: number;
  eta_s: number;
}

export interface NextBusShuttle {
  name: string;
  arrivalTime: string;
  nextArrivalTime: string;
  arrivalTime_veh_plate: string;
  nextArrivalTime_veh_plate: string;
  passengers: string;
  nextPassengers: string;
  routeid: number;
  busstopcode: string;
  _etas?: NextBusEta[];
}

export interface NextBusShuttleServiceResult {
  caption: string;
  name: string;
  TimeStamp: string;
  shuttles: NextBusShuttle[];
  hints?: string[];
}

export interface NextBusBusStopsResponse {
  BusStopsResult?: {
    busstops?: NextBusStop[];
  };
}

export interface NextBusShuttleResponse {
  ShuttleServiceResult?: NextBusShuttleServiceResult;
  message?: string;
}

export interface NextBusAnnouncement {
  ID: string;
  Text: string;
  Status: string;
  Priority: string;
  Affected_Service_Ids: string;
  Created_On: string;
  Created_By: string;
}

export interface NextBusAnnouncementsResponse {
  AnnouncementsResult?: {
    TimeStamp: string;
    Announcement?: NextBusAnnouncement[];
  };
}

// ==========================================
// NUSMods API Types
// ==========================================

export interface NUSModsLesson {
  classNo: string;
  lessonType: string;
  day: string;
  startTime: string;
  endTime: string;
  venue: string;
  weeks: number[] | { start: string; end: string } | number;
  size?: number;
  covidZone?: string;
}

export interface NUSModsSemesterData {
  semester: number;
  timetable: NUSModsLesson[];
  examDate?: string;
  examDuration?: number;
}

export interface NUSModsModule {
  acadYear: string;
  moduleCode: string;
  title: string;
  description?: string;
  department?: string;
  faculty?: string;
  semesterData: NUSModsSemesterData[];
}

// ==========================================
// Internal Domain Models for Frontend & Bot
// ==========================================

export type UrgencyLevel = "imminent" | "moderate" | "delayed" | "off-service";

export interface ShuttleArrival {
  serviceName: string;
  arrivalTime: string;
  arrivalMinutes: number | null;
  vehiclePlate: string;
  nextArrivalTime: string;
  nextArrivalMinutes: number | null;
  nextVehiclePlate: string;
  passengers: string;
  urgency: UrgencyLevel;
  urgencyBadge: "🟢" | "🟡" | "🔴";
}

export interface TransitStop {
  code: string;
  caption: string;
  longName?: string;
}

export interface TransitDisruption {
  id: string;
  text: string;
  cleanText: string;
  status: string;
  priority: string;
  affectedServices: string[];
  createdOn: string;
}

export interface ClassCommuteInfo {
  moduleCode: string;
  moduleTitle: string;
  lessonType: string;
  classNo: string;
  day: string;
  startTime: string;
  endTime: string;
  venue: string;
  busStopCode: string;
  busStopCaption: string;
  arrivals: ShuttleArrival[];
}

