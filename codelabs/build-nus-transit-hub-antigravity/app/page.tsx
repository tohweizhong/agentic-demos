"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Bus,
  Clock,
  AlertTriangle,
  Search,
  RefreshCw,
  MapPin,
  Calendar,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Users,
  Compass,
} from "lucide-react";
import { ClassCommuteInfo, ShuttleArrival, TransitDisruption } from "@/lib/types";

const POPULAR_STOPS = [
  { code: "UTOWN", label: "University Town", subtitle: "Education Hub", icon: "🎓" },
  { code: "COM3", label: "COM 3", subtitle: "Computing", icon: "💻" },
  { code: "KR-MRT", label: "Kent Ridge MRT", subtitle: "Circle Line", icon: "🚇" },
  { code: "CLB", label: "Central Library", subtitle: "Arts & Social Sci", icon: "📚" },
  { code: "LT27", label: "LT 27 / Science", subtitle: "Science & Medicine", icon: "🔬" },
  { code: "BIZ2", label: "BIZ 2", subtitle: "Business School", icon: "📈" },
];

const REFRESH_INTERVAL_SECONDS = 20;

export default function ModernTransitDashboard() {
  const [selectedStop, setSelectedStop] = useState<string>("UTOWN");
  const [stopCaption, setStopCaption] = useState<string>("University Town");
  const [shuttles, setShuttles] = useState<ShuttleArrival[]>([]);
  const [disruptions, setDisruptions] = useState<TransitDisruption[]>([]);
  const [loadingShuttles, setLoadingShuttles] = useState<boolean>(true);
  const [countdown, setCountdown] = useState<number>(REFRESH_INTERVAL_SECONDS);
  const [currentTime, setCurrentTime] = useState<string>("");

  // Commute search state
  const [searchModule, setSearchModule] = useState<string>("");
  const [searchingCommute, setSearchingCommute] = useState<boolean>(false);
  const [commuteResult, setCommuteResult] = useState<ClassCommuteInfo | null>(null);
  const [commuteError, setCommuteError] = useState<string | null>(null);

  // Live Singapore Standard Time clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString("en-SG", {
          timeZone: "Asia/Singapore",
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Shuttle Timings
  const fetchShuttleData = useCallback(async (stopCode: string) => {
    try {
      const res = await fetch(`/api/transit?type=shuttle&stop=${encodeURIComponent(stopCode)}`);
      const data = await res.json();
      if (data.success) {
        setShuttles(data.shuttles || []);
        setStopCaption(data.caption || stopCode);
      } else {
        setShuttles([]);
      }
    } catch (err) {
      console.error("Failed to load shuttle data:", err);
      setShuttles([]);
    } finally {
      setLoadingShuttles(false);
      setCountdown(REFRESH_INTERVAL_SECONDS);
    }
  }, []);

  // Fetch Disruptions
  const fetchDisruptions = useCallback(async () => {
    try {
      const res = await fetch(`/api/transit?type=disruptions`);
      const data = await res.json();
      if (data.success) {
        setDisruptions(data.disruptions || []);
      }
    } catch (err) {
      console.error("Failed to load disruptions:", err);
    }
  }, []);

  // Initial and reactive load on selected stop change
  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const [shuttleRes, disruptionRes] = await Promise.all([
          fetch(`/api/transit?type=shuttle&stop=${encodeURIComponent(selectedStop)}`),
          fetch(`/api/transit?type=disruptions`),
        ]);
        const shuttleData = await shuttleRes.json();
        const disruptionData = await disruptionRes.json();

        if (!ignore) {
          if (shuttleData.success) {
            setShuttles(shuttleData.shuttles || []);
            setStopCaption(shuttleData.caption || selectedStop);
          } else {
            setShuttles([]);
          }
          if (disruptionData.success) {
            setDisruptions(disruptionData.disruptions || []);
          }
          setLoadingShuttles(false);
        }
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load transit data:", err);
          setLoadingShuttles(false);
        }
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [selectedStop]);

  // Countdown timer & auto-refresh
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          fetchShuttleData(selectedStop);
          return REFRESH_INTERVAL_SECONDS;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [selectedStop, fetchShuttleData]);

  // Handle Smart Commute Search
  const handleCommuteSearch = async (e?: React.FormEvent, customCode?: string) => {
    if (e) e.preventDefault();
    const code = (customCode || searchModule).trim().toUpperCase();
    if (!code) return;

    setSearchingCommute(true);
    setCommuteError(null);
    setCommuteResult(null);

    try {
      const res = await fetch(`/api/transit?type=class&module=${encodeURIComponent(code)}`);
      const data = await res.json();

      if (data.success && data.commute) {
        setCommuteResult(data.commute);
      } else {
        setCommuteError(
          data.error || `Could not find lesson timetable or venue for module ${code}.`
        );
      }
    } catch (err) {
      console.error("Commute search error:", err);
      setCommuteError("Unable to retrieve module commute data. Please try again.");
    } finally {
      setSearchingCommute(false);
    }
  };

  // SVG Circular progress values
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (countdown / REFRESH_INTERVAL_SECONDS) * circumference;

  // Active shuttles summary
  const activeRoutesCount = useMemo(() => {
    return shuttles.filter((s) => s.urgency !== "off-service").length;
  }, [shuttles]);

  const nearestArrivalText = useMemo(() => {
    const active = shuttles
      .filter((s) => s.arrivalMinutes !== null)
      .sort((a, b) => (a.arrivalMinutes || 0) - (b.arrivalMinutes || 0));
    if (active.length > 0) {
      return `${active[0].serviceName} in ${active[0].arrivalTime}`;
    }
    return "All routes off-service";
  }, [shuttles]);

  return (
    <div className="min-h-screen bg-[#090a0f] text-zinc-100 antialiased selection:bg-orange-500 selection:text-white font-sans relative overflow-x-hidden">
      {/* Background ambient lighting effects */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-orange-600/10 rounded-full blur-[128px]" />
        <div className="absolute top-1/3 right-1/4 w-[32rem] h-[32rem] bg-blue-600/10 rounded-full blur-[140px]" />
        <div className="absolute inset-0 bg-[radial-gradient(#181926_1px,transparent_1px)] [background-size:24px_24px] opacity-40" />
      </div>

      {/* Main Container */}
      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Terminal Header */}
        <header className="sticky top-0 z-40 bg-[#090a0f]/85 backdrop-blur-xl border-b border-zinc-800/80 shadow-2xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              {/* Brand and Status */}
              <div className="flex items-center gap-3.5">
                <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-orange-500 via-orange-600 to-amber-600 flex items-center justify-center text-white shadow-lg shadow-orange-500/25 ring-1 ring-orange-400/40">
                  <Bus className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className="text-lg font-black tracking-tight text-white flex items-center gap-1.5">
                      NUS TRANSIT <span className="text-orange-500">HUB</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 shadow-sm shadow-emerald-900/30">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                      </span>
                      LIVE SGT
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-zinc-400 mt-0.5 font-mono">
                    <span>NEXTBUS TELEMETRY</span>
                    <span>•</span>
                    <span className="text-zinc-300">{currentTime || "00:00:00 SGT"}</span>
                  </div>
                </div>
              </div>

              {/* Station Ribbon & Refresh Ring */}
              <div className="flex items-center justify-between md:justify-end gap-3 pt-2 md:pt-0 border-t border-zinc-800/60 md:border-none">
                {/* Station quick telemetry */}
                <div className="hidden sm:flex items-center gap-3 px-3.5 py-1.5 rounded-xl bg-zinc-900/80 border border-zinc-800 text-xs">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Compass className="h-3.5 w-3.5 text-orange-400" />
                    <span>Active Routes:</span>
                    <span className="font-mono font-bold text-zinc-200">
                      {activeRoutesCount}/{shuttles.length}
                    </span>
                  </div>
                  <div className="h-3 w-px bg-zinc-700" />
                  <div className="text-zinc-400">
                    Next: <span className="font-semibold text-emerald-400">{nearestArrivalText}</span>
                  </div>
                </div>

                {/* SVG Radial Countdown & Refresh Button */}
                <div className="flex items-center gap-2">
                  <div className="relative flex items-center justify-center h-9 w-9 bg-zinc-900 rounded-xl border border-zinc-800">
                    <svg className="h-8 w-8 -rotate-90">
                      <circle
                        cx="16"
                        cy="16"
                        r={radius}
                        className="stroke-zinc-800 fill-none"
                        strokeWidth="2.5"
                      />
                      <circle
                        cx="16"
                        cy="16"
                        r={radius}
                        className="stroke-orange-500 fill-none transition-all duration-1000 ease-linear"
                        strokeWidth="2.5"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                      />
                    </svg>
                    <span className="absolute font-mono text-[11px] font-bold text-zinc-300">
                      {countdown}
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      setLoadingShuttles(true);
                      fetchShuttleData(selectedStop);
                      fetchDisruptions();
                    }}
                    disabled={loadingShuttles}
                    className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 text-zinc-200 transition-all active:scale-95 disabled:opacity-50 cursor-pointer shadow-sm hover:border-orange-500/50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 text-orange-400 ${loadingShuttles ? "animate-spin" : ""}`} />
                    <span>Sync</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Body */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
          {/* Active Disruption Ticker Banner */}
          {disruptions.length > 0 && (
            <div className="rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-zinc-900/60 p-4 shadow-xl backdrop-blur-md relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-amber-400 to-orange-500" />
              <div className="flex items-start gap-3.5 pl-1">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0 mt-0.5">
                  <AlertTriangle className="h-5 w-5 animate-pulse" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono uppercase tracking-wider font-bold text-amber-400">
                      TRANSIT SERVICE ADVISORY
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      {disruptions.length} ACTIVE
                    </span>
                  </div>

                  <div className="space-y-2">
                    {disruptions.map((d) => (
                      <div
                        key={d.id}
                        className="bg-black/30 rounded-xl p-3 border border-amber-500/20 text-xs sm:text-sm text-zinc-200 leading-relaxed"
                      >
                        <p className="font-medium text-amber-100">{d.cleanText}</p>
                        {d.affectedServices.length > 0 && (
                          <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
                            <span className="text-[11px] font-semibold text-amber-400/90 font-mono">
                              AFFECTED SERVICES:
                            </span>
                            {d.affectedServices.map((svc) => (
                              <span
                                key={svc}
                                className="px-2 py-0.5 rounded-md text-xs font-mono font-black bg-amber-500/30 text-amber-200 border border-amber-400/30"
                              >
                                {svc}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Departure Terminal Section */}
          <section className="space-y-4">
            {/* Terminal Stop Selector Bar */}
            <div className="bg-zinc-900/70 border border-zinc-800 rounded-2xl p-3 backdrop-blur-md shadow-lg">
              <div className="flex items-center justify-between mb-2.5 px-1.5">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-orange-500" />
                  <span className="text-xs font-mono uppercase tracking-wider font-bold text-zinc-400">
                    DEPARTURE TERMINAL SELECTOR
                  </span>
                </div>
                <span className="text-xs font-mono text-zinc-500">
                  CODE: <span className="text-orange-400 font-bold">{selectedStop}</span>
                </span>
              </div>

              {/* Station Tabs */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                {POPULAR_STOPS.map((stop) => {
                  const isSelected = selectedStop === stop.code;
                  return (
                    <button
                      key={stop.code}
                      onClick={() => {
                        setSelectedStop(stop.code);
                        setLoadingShuttles(true);
                      }}
                      className={`group relative flex flex-col items-start p-3 rounded-xl border text-left transition-all cursor-pointer overflow-hidden ${
                        isSelected
                          ? "bg-gradient-to-b from-orange-500/20 to-orange-950/40 border-orange-500/80 shadow-md shadow-orange-950/40"
                          : "bg-zinc-950/60 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-800/50"
                      }`}
                    >
                      {/* Active indicator bar */}
                      {isSelected && (
                        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-orange-400 to-amber-500" />
                      )}

                      <div className="flex items-center justify-between w-full mb-1">
                        <span className="text-base">{stop.icon}</span>
                        <span
                          className={`font-mono text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            isSelected
                              ? "bg-orange-500 text-black font-extrabold"
                              : "bg-zinc-800 text-zinc-400 group-hover:text-zinc-200"
                          }`}
                        >
                          {stop.code}
                        </span>
                      </div>

                      <div className="font-semibold text-xs text-zinc-100 line-clamp-1">
                        {stop.label}
                      </div>
                      <div className="text-[10px] text-zinc-400 font-mono mt-0.5">
                        {stop.subtitle}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Departure Board Cards */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-orange-400" />
                  <h2 className="text-sm font-mono uppercase tracking-wider font-bold text-zinc-300">
                    LIVE SHUTTLE DEPARTURES • {stopCaption.toUpperCase()}
                  </h2>
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  {shuttles.length} SERVICES MONITORED
                </span>
              </div>

              {loadingShuttles ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div
                      key={i}
                      className="h-40 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 p-5 animate-pulse"
                    />
                  ))}
                </div>
              ) : shuttles.length === 0 ? (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-10 text-center space-y-3 backdrop-blur-md">
                  <div className="h-14 w-14 rounded-2xl bg-zinc-800/80 flex items-center justify-center mx-auto text-zinc-400 border border-zinc-700/60">
                    <ShieldAlert className="h-7 w-7 text-orange-400" />
                  </div>
                  <h3 className="text-base font-bold text-zinc-200">Terminal Inactive / Off-Service</h3>
                  <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed">
                    No active shuttle buses detected for <span className="text-zinc-200 font-semibold">{stopCaption}</span>. Regular internal shuttle hours operate approximately 07:00 – 23:00.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {shuttles.map((shuttle) => {
                    const isImminent = shuttle.urgency === "imminent";
                    const isModerate = shuttle.urgency === "moderate";
                    const isOff = shuttle.urgency === "off-service";

                    return (
                      <div
                        key={shuttle.serviceName}
                        className={`group relative rounded-2xl border bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 p-4.5 backdrop-blur-md transition-all duration-200 hover:scale-[1.01] hover:shadow-xl hover:border-zinc-700 ${
                          isImminent
                            ? "border-emerald-500/40 hover:border-emerald-500/60 shadow-emerald-950/20"
                            : isModerate
                            ? "border-amber-500/40 hover:border-amber-500/60 shadow-amber-950/20"
                            : "border-zinc-800 hover:border-zinc-700"
                        }`}
                      >
                        {/* Glow accent */}
                        <div
                          className={`absolute top-0 right-0 w-24 h-24 rounded-full blur-2xl pointer-events-none -mr-8 -mt-8 ${
                            isImminent
                              ? "bg-emerald-500/15"
                              : isModerate
                              ? "bg-amber-500/15"
                              : "bg-transparent"
                          }`}
                        />

                        {/* Card Header: Route & Primary Status */}
                        <div className="flex items-center justify-between mb-3.5">
                          <div className="flex items-center gap-3">
                            <span className="font-mono font-black text-2xl tracking-tight px-3 py-1 rounded-xl bg-zinc-950 text-white border border-zinc-700/80 shadow-inner">
                              {shuttle.serviceName}
                            </span>
                            <div>
                              <div className="text-[11px] font-mono text-zinc-400 uppercase font-semibold">
                                NUS INTERNAL
                              </div>
                              <div className="text-[10px] text-zinc-500">Scheduled Loop</div>
                            </div>
                          </div>

                          {/* Urgency Badge */}
                          <div
                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl border font-mono text-xs font-bold ${
                              isImminent
                                ? "bg-emerald-950/90 text-emerald-300 border-emerald-500/50 shadow-sm shadow-emerald-900/40"
                                : isModerate
                                ? "bg-amber-950/90 text-amber-300 border-amber-500/50 shadow-sm shadow-amber-900/40"
                                : "bg-zinc-800/80 text-zinc-400 border-zinc-700/60"
                            }`}
                          >
                            <span className="text-sm">{shuttle.urgencyBadge}</span>
                            <span className="tracking-wide">
                              {isImminent ? "IMMINENT" : isModerate ? "APPROACHING" : isOff ? "OFF-SERVICE" : "DELAYED"}
                            </span>
                          </div>
                        </div>

                        {/* Primary ETA Display */}
                        <div className="bg-black/40 rounded-xl p-3 border border-zinc-800/80 flex items-center justify-between mb-3">
                          <div>
                            <span className="text-[10px] font-mono text-zinc-500 uppercase font-bold block">
                              NEXT ARRIVAL
                            </span>
                            <div className="flex items-baseline gap-1.5 mt-0.5">
                              <span
                                className={`text-2xl font-black font-mono tracking-tight ${
                                  isImminent
                                    ? "text-emerald-400 drop-shadow-[0_0_12px_rgba(52,211,153,0.3)]"
                                    : isModerate
                                    ? "text-amber-400 drop-shadow-[0_0_12px_rgba(251,191,36,0.3)]"
                                    : "text-zinc-400"
                                }`}
                              >
                                {shuttle.arrivalTime}
                              </span>
                            </div>
                          </div>

                          {shuttle.vehiclePlate !== "-" && (
                            <div className="text-right">
                              <span className="text-[10px] font-mono text-zinc-500 uppercase font-bold block">
                                BUS PLATE
                              </span>
                              <span className="inline-block mt-0.5 px-2 py-0.5 rounded-md bg-zinc-800/90 border border-zinc-700 font-mono text-xs font-bold text-zinc-200">
                                {shuttle.vehiclePlate}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Subsequent Departure & Telemetry Footer */}
                        <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-400 font-mono">
                          <div className="flex items-center gap-1.5">
                            <Clock className="h-3 w-3 text-zinc-500" />
                            <span>Following:</span>
                            <span className="font-semibold text-zinc-300">
                              {shuttle.nextArrivalTime}
                            </span>
                            {shuttle.nextVehiclePlate !== "-" && (
                              <span className="text-[10px] text-zinc-500">
                                ({shuttle.nextVehiclePlate})
                              </span>
                            )}
                          </div>

                          {shuttle.passengers !== "-" && (
                            <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                              <Users className="h-3 w-3 text-zinc-500" />
                              <span>{shuttle.passengers}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>

          {/* Section 2: Integrated Terminal Console (Smart Commute Finder) */}
          <section className="rounded-2xl border border-zinc-800 bg-gradient-to-b from-zinc-900/80 via-zinc-900/50 to-zinc-950 p-5 sm:p-7 shadow-2xl backdrop-blur-md space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-orange-500/20 text-orange-400 border border-orange-500/30">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <h2 className="text-base font-bold font-mono tracking-tight text-white uppercase">
                    SMART COMMUTE CONSOLE • NUSMODS TIMETABLE RESOLVER
                  </h2>
                </div>
                <p className="text-xs text-zinc-400">
                  Enter any module code to map lesson venue to closest shuttle stop and inspect live arrival connections.
                </p>
              </div>

              {/* Quick Module Tags */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] font-mono text-zinc-500 uppercase">Quick query:</span>
                {["CS2030S", "CS1101S", "MA1521", "IS1108"].map((code) => (
                  <button
                    key={code}
                    type="button"
                    onClick={() => {
                      setSearchModule(code);
                      handleCommuteSearch(undefined, code);
                    }}
                    className="px-2 py-0.5 rounded-md bg-zinc-800 hover:bg-orange-500/20 hover:text-orange-300 hover:border-orange-500/40 border border-zinc-700/80 font-mono text-[11px] text-zinc-300 transition-colors cursor-pointer"
                  >
                    {code}
                  </button>
                ))}
              </div>
            </div>

            {/* Terminal Input Form */}
            <form onSubmit={handleCommuteSearch} className="flex flex-col sm:flex-row gap-2.5">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  value={searchModule}
                  onChange={(e) => setSearchModule(e.target.value)}
                  placeholder="QUERY MODULE (e.g. CS2030S, CS1101S, MA1521)..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-zinc-700 bg-zinc-950/80 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all font-mono tracking-wide"
                />
              </div>
              <button
                type="submit"
                disabled={searchingCommute || !searchModule.trim()}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-semibold text-xs font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 cursor-pointer shadow-lg shadow-orange-500/20"
              >
                {searchingCommute ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Resolving...
                  </>
                ) : (
                  <>
                    <span>Execute Lookup</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            {/* Commute Error */}
            {commuteError && (
              <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs font-mono text-rose-300 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{commuteError}</span>
              </div>
            )}

            {/* Commute Boarding Pass / Ticket Result */}
            {commuteResult && (
              <div className="rounded-2xl border border-orange-500/40 bg-zinc-950/90 p-5 sm:p-6 shadow-2xl relative overflow-hidden space-y-5">
                <div className="absolute top-0 right-0 w-48 h-48 bg-orange-500/10 rounded-full blur-3xl pointer-events-none" />

                {/* Ticket Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono font-black text-lg px-2.5 py-0.5 rounded-lg bg-orange-500 text-black">
                        {commuteResult.moduleCode}
                      </span>
                      <h3 className="font-bold text-white text-base">
                        {commuteResult.moduleTitle}
                      </h3>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400 font-mono">
                      <span className="flex items-center gap-1.5 text-zinc-300">
                        <Calendar className="h-3.5 w-3.5 text-orange-400" />
                        {commuteResult.day}, {commuteResult.startTime} – {commuteResult.endTime}
                      </span>
                      <span>•</span>
                      <span>
                        {commuteResult.lessonType} ({commuteResult.classNo})
                      </span>
                    </div>
                  </div>

                  <div className="sm:text-right">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase font-bold block">
                      ASSIGNED VENUE
                    </span>
                    <span className="font-mono text-base font-black text-orange-400 mt-0.5 block">
                      {commuteResult.venue}
                    </span>
                  </div>
                </div>

                {/* Transit Route Connector Pathway */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center bg-zinc-900/90 p-4 rounded-xl border border-zinc-800">
                  {/* Origin Step */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase font-bold block">
                      DESTINATION CLASSROOM
                    </span>
                    <div className="text-sm font-bold text-white flex items-center gap-1.5">
                      <span>{commuteResult.venue}</span>
                    </div>
                  </div>

                  {/* Transit Arrow */}
                  <div className="flex items-center justify-center gap-2 text-orange-400 font-mono text-xs py-1 md:py-0">
                    <div className="h-px flex-1 bg-zinc-700 hidden md:block" />
                    <span className="px-2 py-0.5 rounded bg-orange-500/20 border border-orange-500/30 text-[10px] font-bold">
                      TRANSIT LINK
                    </span>
                    <ArrowRight className="h-4 w-4" />
                    <div className="h-px flex-1 bg-zinc-700 hidden md:block" />
                  </div>

                  {/* Destination Stop */}
                  <div className="md:text-right space-y-1">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase font-bold block">
                      RECOMMENDED BUS STOP
                    </span>
                    <div className="text-sm font-bold text-emerald-400 flex items-center md:justify-end gap-1.5">
                      <MapPin className="h-4 w-4" />
                      <span>{commuteResult.busStopCaption}</span>
                      <span className="text-xs font-mono text-zinc-400">
                        ({commuteResult.busStopCode})
                      </span>
                    </div>
                  </div>
                </div>

                {/* Live Shuttles Heading to Nearest Stop */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-zinc-400 uppercase font-bold">
                      LIVE SHUTTLES AT {commuteResult.busStopCaption.toUpperCase()}:
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedStop(commuteResult.busStopCode);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                      className="text-orange-400 hover:text-orange-300 font-semibold flex items-center gap-1 cursor-pointer"
                    >
                      <span>Jump to terminal board</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  {commuteResult.arrivals.length === 0 ? (
                    <div className="p-3 bg-zinc-900/60 rounded-xl border border-zinc-800 text-xs text-zinc-500 italic text-center">
                      No live shuttles currently broadcasting for this stop.
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      {commuteResult.arrivals.map((s) => (
                        <div
                          key={s.serviceName}
                          className="bg-zinc-900/90 p-3 rounded-xl border border-zinc-800 flex items-center justify-between font-mono"
                        >
                          <span className="font-black text-sm text-white px-2 py-0.5 rounded bg-black border border-zinc-700">
                            {s.serviceName}
                          </span>
                          <div className="flex items-center gap-1.5 text-xs">
                            <span>{s.urgencyBadge}</span>
                            <span className="font-bold text-zinc-200">{s.arrivalTime}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        </main>

        {/* Terminal Footer */}
        <footer className="border-t border-zinc-800/80 py-6 px-4 bg-[#090a0f]/90 text-center text-xs text-zinc-500 font-mono">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>NUS CAMPUS TRANSIT HUB • ENGINE V2.0</div>
            <div>NEXTBUS API + NUSMODS API INTEGRATION</div>
            <div className="text-zinc-400">TELEGRAM BOT: @nus_transit_wz_bot</div>
          </div>
        </footer>
      </div>
    </div>
  );
}
