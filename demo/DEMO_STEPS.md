# Sign Smart: demo script

**Files to upload** (in `/Users/harishguragol/Downloads/signsmart/demo/`):
- `original_agreement.pdf`: bad shop lease (₹35,000 rent, ₹3,00,000 deposit, 36-month lock-in, no refund date, uncapped late fee)
- `revised_agreement.pdf`: owner's counter (deposit ₹1,50,000 + 30-day refund, 12-month lock-in, but a **new 15% yearly rent increase** and the late fee is still uncapped)

**Where:** Telegram bot `@SignSmart_Help_bot`, or web chat `http://localhost:8000/chat`.
(Server: `.venv_local/bin/uvicorn app.main:app --port 8000`. Tunnel: `/opt/homebrew/bin/cloudflared tunnel --url http://localhost:8000`, then put the new URL in `PUBLIC_BASE_URL` in `.env` and restart the server.)

## Steps and answers

| # | Bot says | You send |
|---|---|---|
| 1 | Welcome, choose language | `hi`, then `1` (English) |
| 2 | Send photo or PDF | Upload `original_agreement.pdf` |
| 3 | Got 1 page | `1` (Start reading) |
| 4 | "I read: 3-year shop rent, ₹35,000/month, ₹3,00,000 deposit. Right?" | `1` (Yes) |
| 5 | Max you can pay upfront? | `2` (₹1,80,000 lower deposit) |
| 6 | How long do you plan to stay? | `2` (1 to 2 years) |
| 7 | Must-haves to check | `1` (Keep these) |
| 8 | **Report**: verdict, risk score, money at risk, dashboard link | Open the **dashboard link**, then send `1` (Help me negotiate) |
| 9 | Nearby deposit? | `150000` |
| 10 | Free message for owner + upsell | `1` (Unlock for ₹49) |
| 11 | **Payment link** | Open the link, tap **Pay / Confirm Google Pay Payment**. The chat then continues by itself. (Or send `1`, "I've paid".) |
| 12 | Pick tone | `2` (Firm) |
| 13 | Negotiation plan + message | `2` (I'll forward it myself) |
| 14 | Did you send it? | `1` (Yes, sent) |
| 15 | When the owner replies | `2` (Send the revised agreement) |
| 16 | Send revised agreement | Upload `revised_agreement.pdf`, then `1` (Check it) |
| 17 | **Comparison**: ✅ deposit, ✅ refund, ✅ lock-in, ❌ late fee, ⚠️ new 15% increase, verdict COUNTER | `1` (Draft round 2) |
| 18 | Round 2 message | `2`, then `1`, then pick `I ACCEPT` / walk away to finish |

## Extra things to show
- **Second agreement**: upload any new agreement later. Your income and stay answers are reused, with no questions again.
- **Restart**: type `menu`.
- **Payment guard**: at step 11, type `hi` or `continue`. You get a "payment not received" reminder and no unlock.
- **Language**: pick `2` or `3` at step 1 for Hindi or Kannada.

## Known gaps
- "Ask a question" (menu option 2) and the voice summary need a `chat_agent` ID. They fail until one is configured.
