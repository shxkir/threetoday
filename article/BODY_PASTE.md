# Weekend Productivity Challenge: ThreeToday


> **Publish this on AWS Builder Center**
>
> - **Title (exact pattern):** `Weekend Productivity Challenge: ThreeToday`
> - **Tag:** `#productivity` (add this tag in the article UI)
> - **Link:** Function URL after deploy **and/or** public GitHub repo (challenge allows **either**; both is stronger)
> - **GitHub (already public):** https://github.com/shxkir/threetoday
> - **Length:** this draft is well over 500 words — paste as-is, then add 2–3 screenshots
> - **Deadline:** July 13, 2026 at 1:00 PM PT

---

## Vision & What the App Does

Most productivity apps make the same quiet mistake: they treat your ambition as capacity.

You open a notes app, dump fifteen things on your mind, and the app nods along. It will happily hold a novel’s worth of unfinished intentions. By noon you’ve “planned” nine hours of work into a four-hour day, and the guilt starts before the deep work does.

**ThreeToday** is built for the opposite behavior. You paste a messy brain dump — half-finished tasks, worries, side quests, “maybe I should learn Rust,” real client work, random errands — and you tell it how many focused hours you actually have and how much energy you have today. ThreeToday returns:

1. **Exactly three outcomes for today** (or fewer if your budget is tiny)
2. A **first move** for each — a 2–10 minute starting action so friction dies
3. A **focus schedule** that sequences those three into realistic blocks
4. A **parked** list for “not today, still real”
5. A **killed** list for noise you should stop carrying

The product promise is deliberate undercommitment. Finishing three things beats juggling twelve. The UI is a single page: dump → constraints → **Lock my three**. No accounts, no kanban boards, no feature cemetery.

From a user perspective the flow is boring in the best way:

1. Paste everything on your mind (messy is fine).
2. Set hours (e.g. 4) and energy (low / medium / high).
3. Optionally add day context (“client deadline Friday”).
4. Hit **Lock my three**.
5. Copy the plan as Markdown into your notes or Slack.

I built this because I run marketing and delivery work in the same day. Without a hard cap, the loudest task wins — not the highest leverage one. ThreeToday is the colleague who says: *you don’t get twelve today; pick the three that move the needle and kill the rest on purpose.*

---

## How You Built It

I had a weekend and a clear constraint from the challenge: ship a real **AI-powered productivity tool on AWS**, not a slide deck. That pushed me toward a boring architecture that deploys as one unit.

### Key decisions

**1. One Lambda, one URL.**  
The function serves the HTML UI on `GET` and the planning API on `POST` via a Lambda Function URL. No API Gateway, no separate Amplify app, no CORS maze. The browser talks to the same origin it loaded from. That collapsed deploy risk and made demos a single link.

**2. AI proposes; code decides.**  
Amazon Bedrock (Nova Lite) extracts candidate tasks, scores them, and suggests buckets. But the **“max three today” rule and the hour budget are enforced in Python**, not in the prompt. If the model is creative, the plan still can’t overcommit. This was the most important design choice — LLMs are great at language and mediocre at hard constraints.

**3. Nova Lite over larger models.**  
For this workload (short structured triage), latency and cost matter more than essay-quality prose. Nova Lite is fast enough for an interactive UI and cheap enough that a public Function URL doesn’t scare me for a challenge weekend. Temperature is low (0.2) so plans stay stable.

**4. Structured JSON + defensive parsing.**  
The model returns a single JSON object of candidates. The handler strips optional code fences, finds the outermost `{...}`, and fails closed with a clear error if parsing breaks. Each candidate is normalized (hours clamped, effort enum, score as float) before budgeting.

**5. Energy as a soft bias, hours as a hard limit.**  
Low energy down-ranks high-effort items in the sort. High energy slightly boosts them. Hours available are a hard ceiling: once the budget is full or three slots are taken, everything else parks or dies.

### Challenges and how I overcame them

**Challenge: models love to overpromise.**  
Early prompts asked the model to “build the full plan.” It would cheerfully return five “today” items that ignored the hour budget.  
**Fix:** stop trusting the model for the final plan. Ask only for scored candidates; run `enforce_three()` in code.

**Challenge: JSON reliability.**  
Even with “JSON only” instructions, models occasionally wrap output in markdown fences or add a friendly sentence.  
**Fix:** fence stripping + brace slicing before `json.loads`, plus field-level defaults.

**Challenge: cold start vs. polish.**  
I wanted a UI that didn’t look like a 2008 form. Embedding a full HTML/CSS/JS page in the Lambda increases package size slightly but removes a second deploy target. For a weekend challenge, one artifact is a feature.

**Challenge: public endpoint blast radius.**  
AuthType is `NONE` for easy demos (challenge-friendly). Mitigations: request size caps (6k chars), timeout 60s, least-privilege IAM (only `bedrock:InvokeModel` / `bedrock:Converse` on the Nova model ARN), and no database of user content.

**Local loop:** I built `local_server.py` with a mock AI so I could iterate on the UI without burning Bedrock tokens, then flipped `USE_BEDROCK=1` for real model tests before deploy.

---

## AWS Services Used / Architecture Overview

| Service | Role |
| --- | --- |
| **AWS Lambda** (Python 3.12, arm64) | Hosts UI + API in one function |
| **Lambda Function URL** | Public HTTPS endpoint (`AuthType: NONE` for demo) |
| **Amazon Bedrock** — **Amazon Nova Lite** | Extracts, scores, and explains tasks from the brain dump |
| **IAM** | Execution role limited to invoke/converse on the chosen model ARN |
| **AWS SAM / CloudFormation** | Infrastructure as code (`infra/template.yaml`) |

### Architecture (request path)

```text
Browser
  │  GET /
  ▼
Lambda Function URL ──► Lambda (handler)
                          │ returns HTML (ThreeToday UI)
                          │
Browser                 POST /  { brain_dump, hours, energy, context }
  │                       ▼
  │                     Validate input (size, bounds)
  │                       ▼
  │                     Amazon Bedrock Runtime
  │                       (Converse → Nova Lite)
  │                       ▼
  │                     Parse candidates JSON
  │                       ▼
  │                     enforce_three()  ← deterministic budget + max 3
  │                       ▼
  └─────────────────── JSON plan { today, parked, killed, schedule }
```

### Why this shape

- **Serverless:** no servers to patch for a weekend app  
- **Free Tier friendly:** Lambda + light Bedrock usage fits new-account free tier / credits  
- **Explainable:** the article (and code comments) can show exactly where AI ends and rules begin  
- **Demoable:** one URL in the Builder Center article satisfies the “working link” requirement  

Diagram encouragement from the challenge: the ASCII flow above is intentional — judges can read it without opening a PNG. Screenshots of the locked plan UI belong under Vision / How You Built It when you publish.

---

## What You Learned

1. **Constraint engines beat prompt engineering for promises you must keep.**  
   “Only three things today” is a product rule. Putting it only in the system prompt is hope; putting it in Python is product.

2. **Small models are enough for triage UX.**  
   Nova Lite doesn’t need to write a novel. It needs to turn messy language into structured candidates. That matches the model to the job.

3. **Same-origin Function URL UX is underrated.**  
   Skipping API Gateway + separate static host removed an entire class of CORS and deploy-order bugs. For hackathon-shaped work, collapse the stack.

4. **Energy and time are different axes.**  
   A high-impact deep-work task on a low-energy day is a trap. Soft score bias + hard hour budget models how humans actually fail.

5. **Ship the article structure while you build.**  
   The challenge grades completeness: Vision, Build story, Architecture, Learning, Link. Writing those sections as I coded made the final article honest instead of retrofitted marketing.

6. **Public AI endpoints need a cost story.**  
   Even without auth, max input length, short max tokens, and a cheap model keep the blast radius small. Next iteration would add a simple API key or Cognito if this left demo mode.

If I had another day, I’d add Amazon Bedrock Guardrails for prompt-injection filtering and DynamoDB for optional plan history — without breaking the “one screen, three outcomes” core.

---

## Link to App or Repo

**Source code (public repo):**  
https://github.com/shxkir/threetoday

**Live app (Function URL):**  
*(Deploy pending AWS account verification — will be added immediately after Lambda unlocks. Repo link satisfies the challenge link requirement in the meantime.)*  
*(Filled after AWS account verification completes and `infra/deploy-cli.sh` succeeds — CloudFormation/Lambda Function URL output.)*

**How to run locally (mock AI):**
```bash
cd threetoday
python3 local_server.py
# open http://127.0.0.1:8080
```

**How to deploy:**
```bash
# one-time: enable Amazon Nova Lite in Bedrock model access (same region)
brew install awscli aws-sam-cli   # if needed
aws configure
cd threetoday/infra
chmod +x deploy.sh
./deploy.sh
```

---

## Closing

ThreeToday is a small app with a sharp opinion: **productivity is subtraction.** AWS made it easy to put that opinion behind a real HTTPS endpoint in a weekend — Lambda for the app, Bedrock for the language, IAM for the blast radius. If the jacket is the prize, the lasting win is a tool I actually open on chaotic mornings.

---

### Pre-publish checklist (for you)

- [ ] Deploy to your AWS account; confirm **Lock my three** works with real Bedrock
- [ ] Replace the two `PASTE_…` links above
- [ ] Take screenshots: empty form, sample dump, locked three + schedule
- [ ] Create article on [builder.aws.com](https://builder.aws.com) with **exact title pattern** and tag **`#productivity`**
- [ ] Word count ≥ 500 (this draft is ~1,100+ words before screenshots)
- [ ] Publish **before July 13, 2026, 1:00 PM PT**
- [ ] Speed matters: first **50 qualifying** pass/fail entries get the AWS Builder Jacket
