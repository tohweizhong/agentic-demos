import { NextRequest, NextResponse } from "next/server";
import {
  getNextBusAnnouncements,
  getNextBusShuttleService,
  getNextBusStops,
} from "@/lib/nextbus";
import { getFirstLessonCommute } from "@/lib/nusmods";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");

  try {
    switch (type) {
      case "stops": {
        const stops = await getNextBusStops();
        return NextResponse.json({ success: true, stops });
      }

      case "shuttle": {
        const stop = searchParams.get("stop") || "UTOWN";
        const shuttleData = await getNextBusShuttleService(stop);
        return NextResponse.json({ success: true, ...shuttleData });
      }

      case "disruptions": {
        const disruptions = await getNextBusAnnouncements();
        return NextResponse.json({ success: true, disruptions });
      }

      case "class": {
        const moduleCode = searchParams.get("module");
        if (!moduleCode) {
          return NextResponse.json(
            { success: false, error: "Module code is required" },
            { status: 400 }
          );
        }
        const commute = await getFirstLessonCommute(moduleCode);
        if (!commute) {
          return NextResponse.json(
            {
              success: false,
              error: `No timetable or venue found for module ${moduleCode.toUpperCase()}`,
            },
            { status: 404 }
          );
        }
        return NextResponse.json({ success: true, commute });
      }

      default: {
        return NextResponse.json(
          {
            success: false,
            error:
              "Invalid query type. Valid types are: stops, shuttle, disruptions, class",
          },
          { status: 400 }
        );
      }
    }
  } catch (error) {
    console.error("API /api/transit error:", error);
    return NextResponse.json(
      { success: false, error: "Internal Server Error" },
      { status: 500 }
    );
  }
}

