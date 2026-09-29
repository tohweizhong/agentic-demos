export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

import { webhookCallback } from "grammy";
import { bot } from "@/lib/bot";

// Export POST handler using grammY's standard HTTP adapter for Next.js App Router
export const POST = webhookCallback(bot, "std/http");

// Optional GET handler for webhook health checking
export async function GET() {
  return new Response("NUS Transit Hub Telegram Bot Webhook Active", {
    status: 200,
  });
}
