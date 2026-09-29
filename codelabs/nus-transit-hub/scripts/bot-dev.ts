import dotenv from "dotenv";
import path from "path";

// Load .env.local first, then fallback to .env
dotenv.config({ path: path.resolve(process.cwd(), ".env.local") });
dotenv.config({ path: path.resolve(process.cwd(), ".env") });

import { createBot } from "../lib/bot";

const token = process.env.TELEGRAM_BOT_TOKEN;

if (!token || token === "YOUR_TELEGRAM_BOT_TOKEN_HERE") {
  console.error("=========================================================");
  console.error("⚠️  TELEGRAM_BOT_TOKEN is not configured in .env.local!");
  console.error("Please add your token from @BotFather in .env.local:");
  console.error('TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"');
  console.error("=========================================================");
  process.exit(1);
}

console.log("🤖 Initializing NUS Campus Transit Telegram Bot (Polling Mode)...");
const bot = createBot(token);

// Handle graceful shutdown
const shutdown = () => {
  console.log("\nStopping bot runner...");
  bot.stop();
  process.exit(0);
};

process.once("SIGINT", shutdown);
process.once("SIGTERM", shutdown);

bot
  .start({
    onStart: (botInfo) => {
      console.log(`✅ Bot @${botInfo.username} is running and listening for messages!`);
      console.log(`Try sending /start, /bus UTOWN, /disruptions, or /class CS2030S`);
    },
  })
  .catch((err) => {
    console.error("Failed to start bot:", err);
    process.exit(1);
  });

