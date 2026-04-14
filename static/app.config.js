/**
 * ╔══════════════════════════════════════════════╗
 * ║          CultureQuest — App Config           ║
 * ║  Change the name/branding here and it        ║
 * ║  updates EVERYWHERE automatically.           ║
 * ╚══════════════════════════════════════════════╝
 *
 * HOW TO USE:
 *   1. Edit APP_NAME below (e.g. "WanderAI")
 *   2. Edit APP_TAGLINE for the nav sub-line
 *   3. Save — the page reads this on load, done!
 */

const APP_CONFIG = {

  // ── Main name (shown in navbar, page title, chat header) ──
  APP_NAME: "CultureQuest",          // e.g. "WanderAI", "RoamBot", "TravelMate"

  // ── The italic/colored second part of the name in navbar ──
  APP_NAME_SUFFIX: "Quest",       // "Trip" + "Quests" → Trip is plain, Quests is styled

  // ── Browser tab title ──
  PAGE_TITLE: "CultureQuest — Your AI Travel Companion",

  // ── Chat header sub-line ──
  CHAT_SUBTITLE: "Multilingual · Weather · Distances · Personalised",

  // ── Admin panel label (shown next to brand) ──
  ADMIN_LABEL: "ADMIN",

  // ── Welcome message (supports <strong> and <br>) ──
  WELCOME_MESSAGE: `Namaste! I'm <strong>CultureQuest AI</strong> powered by Groq's Llama 3.3.<br><br>I plan trips, show <strong>live weather</strong>, calculate <strong>distances</strong>, and give <strong>personalised recommendations</strong>.<br><br>🌐 <strong>Switch the language</strong> in the sidebar to chat in Hindi, Punjabi, Tamil, French or any language!<br><br>👥 <strong>Group Plan</strong> — invite friends to plan together. 💰 <strong>Split Expenses</strong> — split trip costs fairly.`,

  // ── Typewriter effect speed (milliseconds per character) ──
  TYPEWRITER_SPEED_MS: 12,         // lower = faster. Try 10–30.

};

// ── Do not edit below this line ──────────────────────────
if (typeof module !== "undefined") module.exports = APP_CONFIG;
