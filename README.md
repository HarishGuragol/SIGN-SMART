# Sign Smart

A WhatsApp/Telegram/web-chat bot that reads a shopkeeper's rental (or supplier/loan)
agreement, scores the risk in plain language, drafts a negotiation message to the
owner, and tracks the back-and-forth through to a final decision — with a visual
risk dashboard and an optional voice explainer.

Built for a hackathon. Agent logic (extraction, risk scoring, negotiation,
evaluation, translation) runs on [AgenticOrg](https://agenticorg.hackathon.pinelabs.com);
payments are a Pine Labs integration point (stubbed for local testing).

## Quick start (local, no API keys needed)

The app ships with `MOCK_LLM=1`, so you can run the whole flow — extraction,
risk scoring, negotiation, evaluation — with sample answers and **zero API keys**.

```bash
# 1. Clone and enter the project
git clone https://github.com/jeffyrosemary-rgb/Sign-Smart.git
cd Sign-Smart

# 2. Python 3.10+ required (3.9 is too old for some deps). Create a venv:
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example env file
cp .env.example .env
#    .env.example already has MOCK_LLM=1 and CHANNEL=sim — no edits needed
#    to try it locally.

# 5. Run the server
uvicorn app.main:app --reload

# 6. Open the chat UI
open http://localhost:8000/chat
```

Talk to the bot like a real user: pick a language, upload any photo or PDF
(content is ignored in mock mode — you'll always get the sample agreement back),
answer the profile questions, and walk through risk report → negotiate → pay
(stubbed) → simulate an owner reply → accept/counter/walk away.

Useful routes while testing:
- `/chat` — the web chat UI (what you just used)
- `/stats` — demo counters (users, agreements checked, money at risk found)
- `/d/<token>` — the visual risk dashboard for a session (the bot sends you this link)
- `/pay/<token>` — the **test-mode** Pine Labs payment page (no real money moves
  while `PINELABS_MODE=stub`)

## Running with real agents (optional)

To use real AgenticOrg agents instead of mock answers:

1. Get an AgenticOrg API key and a `company_id` for the hackathon tenant.
2. In `.env`, set `MOCK_LLM=0` and `AGENTICORG_API_KEY=<your key>`.
3. **Note:** as shipped, `app/agents.py` doesn't pass a `company_id` when
   calling `agents.run(...)` — AgenticOrg's API requires one. You'll need to
   add it (see `_agenticorg()` / `run_on_agenticorg()` in `app/agents.py`)
   before real agent calls will succeed. `test_agenticorg.py` is a quick
   standalone script to check connectivity without starting the whole app:
   ```bash
   python test_agenticorg.py
   ```

To use Anthropic directly instead of AgenticOrg, set `AGENT_BACKEND=llm` and
`ANTHROPIC_API_KEY=<your key>`.

## Running on Telegram instead of web chat

1. Create a bot with [@BotFather](https://t.me/BotFather), get its token.
2. You need a **public HTTPS URL** pointing at your local server — Telegram
   webhooks won't accept `localhost`. For local testing, use a tunnel:
   ```bash
   # Cloudflare's free quick tunnel, no account needed:
   cloudflared tunnel --url http://localhost:8000
   # copy the https://*.trycloudflare.com URL it prints
   ```
3. In `.env`: set `CHANNEL=telegram`, `TELEGRAM_TOKEN=<your token>`,
   `TELEGRAM_BOT_USERNAME=<bot username, no @>`, and
   `PUBLIC_BASE_URL=<your https tunnel URL>`.
4. Restart the server — it registers the Telegram webhook automatically on
   startup (see `register_telegram_webhook()` in `app/main.py`).
5. Message your bot on Telegram.

Note: `trycloudflare.com` tunnel URLs are ephemeral — if you restart the
tunnel, update `PUBLIC_BASE_URL` and restart the server so the webhook
re-registers at the new URL.

## Running on WhatsApp (Twilio) instead

Set `CHANNEL=twilio` plus `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and point
your Twilio WhatsApp sandbox's inbound webhook at
`https://<your-public-url>/whatsapp/inbound` (and status callback at
`/whatsapp/status`). Needs the same public-HTTPS-URL requirement as Telegram.

## Voice (optional)

Set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to have the bot generate a
short spoken risk summary after the report (see `app/voice.py`). Skipped
silently if unset — the rest of the flow doesn't depend on it.

## Project structure

```
app/
  main.py        FastAPI routes: WhatsApp/Telegram webhooks, web chat API,
                  payments webhook, risk dashboard, stats
  states.py       The conversation state machine — one handler per state
  agents.py       Prompts + calls to AgenticOrg/Anthropic, plus MOCK_LLM sample data
  calc.py         All numbers and verdict rules (deterministic, never the LLM)
  channel.py      Sends/receives messages across Telegram/web-chat/WhatsApp
  payments.py     Pine Labs payment links (stub mode works out of the box;
                  live mode has 3 TODOs for the real API calls)
  db.py           SQLite-backed session store (one row per user, JSON blob)
  voice.py        ElevenLabs text-to-speech for the voice explainer
  templates/      chat.html (web chat UI) and dashboard.html (risk dashboard)
test_agenticorg.py   Standalone script to sanity-check the AgenticOrg connection
```

## Known gaps / TODOs

- **Pine Labs live payments aren't wired up.** `PINELABS_MODE=stub` (the
  default) uses a local fake payment page — no real Pine Labs API calls
  happen. Going live requires real Pine Labs merchant credentials and their
  payment-link API docs; see the 3 `TODO (live)` comments in `app/payments.py`.
- **AgenticOrg calls need a `company_id`** that isn't currently passed (see
  above) — real (non-mock) agent calls will fail until that's added.
- Data is session-only: uploaded files are deleted when a chat finishes or
  restarts (`states.delete_files`), and sessions live in a local SQLite file
  (`data/signsmart.db`) — fine for a demo, not meant for production storage.
