import { Bot, InlineKeyboard } from "grammy";
import { getNextBusAnnouncements, getNextBusShuttleService } from "./nextbus";
import { getFirstLessonCommute } from "./nusmods";
import { ShuttleArrival } from "./types";

/**
 * Creates and configures the grammY Telegram Bot instance.
 */
export function createBot(token?: string): Bot {
  const botToken = token || process.env.TELEGRAM_BOT_TOKEN || "";
  const bot = new Bot(botToken || "EMPTY_TOKEN");

  // Inline keyboard with popular quick stops
  const quickStopsKeyboard = new InlineKeyboard()
    .text("🎓 UTown", "stop:UTOWN")
    .text("💻 COM 3", "stop:COM3")
    .row()
    .text("🚇 Kent Ridge MRT", "stop:KR-MRT")
    .text("📚 Central Library", "stop:CLB");

  /**
   * Helper to format shuttle arrivals into Telegram Markdown message.
   */
  function formatShuttleMessage(
    stopCaption: string,
    stopCode: string,
    shuttles: ShuttleArrival[]
  ): string {
    if (!shuttles || shuttles.length === 0) {
      return (
        `🚏 *Bus Stop: ${escapeMarkdown(stopCaption)} (${stopCode})*\n\n` +
        `🌙 *Shuttle buses are currently off-service.*\n` +
        `Operating hours are typically 07:00 - 23:00 on weekdays/Saturdays.`
      );
    }

    const lines: string[] = [
      `🚏 *Live Bus Timings: ${escapeMarkdown(stopCaption)} (${stopCode})*\n`,
    ];

    let hasActiveService = false;

    for (const s of shuttles) {
      const isOffService = s.urgency === "off-service";
      if (!isOffService) hasActiveService = true;

      const plateStr = s.vehiclePlate !== "-" ? ` \`[${s.vehiclePlate}]\`` : "";
      const nextPlateStr = s.nextVehiclePlate !== "-" ? ` \`[${s.nextVehiclePlate}]\`` : "";

      lines.push(
        `🚌 *Service ${s.serviceName}*\n` +
          `  └ Next: ${s.urgencyBadge} *${s.arrivalTime}*${plateStr}\n` +
          `  └ Subsequent: ${s.nextArrivalTime}${nextPlateStr}`
      );
    }

    if (!hasActiveService) {
      lines.push(
        `\n⚠️ _All shuttle services for this stop are currently showing off-service or inactive._`
      );
    }

    return lines.join("\n");
  }

  // /start command
  bot.command("start", async (ctx) => {
    const welcome =
      `👋 *Welcome to NUS Campus Transit Bot!*\n\n` +
      `Your smart companion for navigating NUS shuttle buses and class commutes.\n\n` +
      `⚡ *Available Commands:*\n` +
      `• \`/bus <stop>\` - Live shuttle ETAs (e.g. \`/bus UTOWN\`, \`/bus COM3\`)\n` +
      `• \`/class <module>\` - Lesson info & nearest bus stop (e.g. \`/class CS2030S\`)\n` +
      `• \`/disruptions\` - Live vehicle breakdowns & service advisories\n\n` +
      `👇 *Quick check popular bus stops:*`;

    await ctx.reply(welcome, {
      parse_mode: "Markdown",
      reply_markup: quickStopsKeyboard,
    });
  });

  // /bus <stop> command
  bot.command("bus", async (ctx) => {
    const rawStop = (ctx.match || "").trim().toUpperCase();

    if (!rawStop) {
      await ctx.reply(
        `ℹ️ *Please provide a bus stop code.*\n\n` +
          `Example: \`/bus UTOWN\` or \`/bus COM3\`\n\n` +
          `Quick select below:`,
        {
          parse_mode: "Markdown",
          reply_markup: quickStopsKeyboard,
        }
      );
      return;
    }

    try {
      const data = await getNextBusShuttleService(rawStop);
      const message = formatShuttleMessage(data.caption, data.name, data.shuttles);

      await ctx.reply(message, {
        parse_mode: "Markdown",
        reply_markup: quickStopsKeyboard,
      });
    } catch (error) {
      console.error("Error in /bus command:", error);
      await ctx.reply("❌ Unable to fetch bus timings at this moment. Please try again later.");
    }
  });

  // /disruptions command
  bot.command("disruptions", async (ctx) => {
    try {
      const disruptions = await getNextBusAnnouncements();

      if (disruptions.length === 0) {
        await ctx.reply(
          `✅ *All Clear!*\n\nNo active vehicle breakdowns or transit disruptions reported.`,
          { parse_mode: "Markdown" }
        );
        return;
      }

      const lines = [`🚨 *Active NUS Transit Advisories & Disruptions:*\n`];

      disruptions.forEach((d, idx) => {
        const services =
          d.affectedServices.length > 0 ? `\n*Affected Services:* ${d.affectedServices.join(", ")}` : "";
        lines.push(`${idx + 1}. ${escapeMarkdown(d.cleanText)}${services}`);
      });

      await ctx.reply(lines.join("\n\n"), { parse_mode: "Markdown" });
    } catch (error) {
      console.error("Error in /disruptions command:", error);
      await ctx.reply("❌ Unable to load transit advisories. Please try again later.");
    }
  });

  // /class <moduleCode> command
  bot.command("class", async (ctx) => {
    const moduleCode = (ctx.match || "").trim().toUpperCase();

    if (!moduleCode) {
      await ctx.reply(
        `ℹ️ *Please provide a module code.*\n\n` +
          `Example: \`/class CS2030S\` or \`/class MA1521\``,
        { parse_mode: "Markdown" }
      );
      return;
    }

    try {
      const info = await getFirstLessonCommute(moduleCode);

      if (!info) {
        await ctx.reply(
          `❌ *Module not found:* Could not retrieve schedule for \`${moduleCode}\`.\n` +
            `Please verify the course code and try again.`,
          { parse_mode: "Markdown" }
        );
        return;
      }

      const commuteMsg =
        `📚 *Class Commute: ${escapeMarkdown(info.moduleCode)}*\n` +
        `*${escapeMarkdown(info.moduleTitle)}*\n\n` +
        `🗓 *1st Lesson:* ${info.day}, ${info.startTime} - ${info.endTime}\n` +
        `🏷 *Type:* ${info.lessonType} (${info.classNo})\n` +
        `📍 *Venue:* \`${escapeMarkdown(info.venue)}\`\n` +
        `🚏 *Nearest Bus Stop:* *${escapeMarkdown(info.busStopCaption)}* (\`${info.busStopCode}\`)\n\n` +
        `🚌 *Live Shuttle Arrivals at Nearest Stop:*`;

      const shuttleLines: string[] = [];
      if (info.arrivals.length === 0) {
        shuttleLines.push(`_No active shuttles currently running._`);
      } else {
        info.arrivals.forEach((s) => {
          shuttleLines.push(`• *${s.serviceName}*: ${s.urgencyBadge} ${s.arrivalTime}`);
        });
      }

      await ctx.reply(`${commuteMsg}\n${shuttleLines.join("\n")}`, {
        parse_mode: "Markdown",
      });
    } catch (error) {
      console.error("Error in /class command:", error);
      await ctx.reply("❌ Unable to process smart commute search. Please try again later.");
    }
  });

  // Handle quick stop button presses from inline keyboards
  bot.on("callback_query:data", async (ctx) => {
    const data = ctx.callbackQuery.data;

    if (data.startsWith("stop:")) {
      const stopCode = data.replace("stop:", "");
      try {
        await ctx.answerCallbackQuery({ text: `Fetching ${stopCode}...` });
        const result = await getNextBusShuttleService(stopCode);
        const message = formatShuttleMessage(result.caption, result.name, result.shuttles);

        await ctx.reply(message, {
          parse_mode: "Markdown",
          reply_markup: quickStopsKeyboard,
        });
      } catch (err) {
        console.error("Error handling callback query:", err);
        await ctx.answerCallbackQuery({ text: "Failed to fetch timings." });
      }
    } else {
      await ctx.answerCallbackQuery();
    }
  });

  // Natural language & direct text handler (no slash needed)
  bot.on("message:text", async (ctx) => {
    const raw = (ctx.message.text || "").trim();
    if (raw.startsWith("/")) return; // Ignore unhandled slash commands

    const upper = raw.toUpperCase().replace(/\s+/g, "");

    // 1. Check if user typed a module code (e.g., CS2030S, MA1521)
    const modulePattern = /^[A-Z]{2,3}\d{4}[A-Z]{0,2}$/;
    if (modulePattern.test(upper)) {
      try {
        const info = await getFirstLessonCommute(upper);
        if (info) {
          const commuteMsg =
            `📚 *Class Commute: ${escapeMarkdown(info.moduleCode)}*\n` +
            `*${escapeMarkdown(info.moduleTitle)}*\n\n` +
            `🗓 *1st Lesson:* ${info.day}, ${info.startTime} - ${info.endTime}\n` +
            `🏷 *Type:* ${info.lessonType} (${info.classNo})\n` +
            `📍 *Venue:* \`${escapeMarkdown(info.venue)}\`\n` +
            `🚏 *Nearest Bus Stop:* *${escapeMarkdown(info.busStopCaption)}* (\`${info.busStopCode}\`)\n\n` +
            `🚌 *Live Shuttle Arrivals at Nearest Stop:*`;

          const shuttleLines: string[] = [];
          if (info.arrivals.length === 0) {
            shuttleLines.push(`_No active shuttles currently running._`);
          } else {
            info.arrivals.forEach((s) => {
              shuttleLines.push(`• *${s.serviceName}*: ${s.urgencyBadge} ${s.arrivalTime}`);
            });
          }

          await ctx.reply(`${commuteMsg}\n${shuttleLines.join("\n")}`, {
            parse_mode: "Markdown",
          });
          return;
        }
      } catch (e) {
        console.error("Direct module lookup error:", e);
      }
    }

    // 2. Check if user typed a known stop code or name
    const knownStops = ["UTOWN", "COM3", "KR-MRT", "CLB", "LT27", "BIZ2", "PGP", "EA", "IT"];
    if (knownStops.includes(upper)) {
      try {
        const data = await getNextBusShuttleService(upper);
        const message = formatShuttleMessage(data.caption, data.name, data.shuttles);
        await ctx.reply(message, {
          parse_mode: "Markdown",
          reply_markup: quickStopsKeyboard,
        });
        return;
      } catch (e) {
        console.error("Direct stop lookup error:", e);
      }
    }

    // 3. Fallback helper
    await ctx.reply(
      `👋 Send a bus stop code (e.g. \`UTOWN\`, \`COM3\`) or a module code (e.g. \`CS2030S\`) to get instant timings, or select a stop below:`,
      {
        parse_mode: "Markdown",
        reply_markup: quickStopsKeyboard,
      }
    );
  });

  // Error catcher
  bot.catch((err) => {
    console.error("Unhandled error in bot handler:", err);
  });

  return bot;
}

/**
 * Escapes characters for Telegram Markdown (V1)
 */
function escapeMarkdown(text: string): string {
  if (!text) return "";
  return text.replace(/([_*`\\])/g, "\\$1");
}

// Default instance for application imports
export const bot = createBot();

