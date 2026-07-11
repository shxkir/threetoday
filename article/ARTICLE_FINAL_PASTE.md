## Vision & What the App Does

Most productivity apps treat ambition as capacity. You dump fifteen things on your mind, the list accepts every item, and by noon you have planned nine hours of work into a four-hour day.

**ThreeToday** does the opposite. Paste a messy brain dump, set how many focused hours you actually have and your energy level, and optionally add day context. ThreeToday returns:

1. Exactly three outcomes for today (or fewer if the budget is tiny)
2. A first move for each outcome (a 2-10 minute starting action)
3. A focus schedule that sequences those three into realistic blocks
4. A parked list for real work that is not today
5. A killed list for noise you should stop carrying

The product promise is deliberate undercommitment. Finishing three things beats juggling twelve. The UI is a single page: dump, set constraints, then Lock my three. No accounts, no kanban boards, no feature cemetery.

I built this because I run marketing and delivery in the same day. Without a hard cap, the loudest task wins instead of the highest leverage one. ThreeToday is the colleague who says you do not get twelve today.

## How You Built It

This was a weekend challenge constraint: ship a real AI-powered productivity tool on AWS, not a slide deck. That pushed a boring architecture that deploys as one unit.

Key decisions:

1. One Lambda, one URL. The function serves HTML on GET and the planning API on POST via a Lambda Function URL. No API Gateway, no separate host, no CORS maze.
2. AI proposes; code decides. Amazon Bedrock Nova Lite can extract and score candidates, but the max-three rule and hour budget are enforced in Python. LLMs are great at language and mediocre at hard constraints.
3. Nova Lite over larger models for latency and cost on short structured triage.
4. Structured JSON with defensive parsing and field-level defaults.
5. Energy as a soft bias; hours as a hard limit.

Challenges:

- Models love to overpromise. Early prompts asked for a full plan and ignored the budget. Fix: only ask for scored candidates, then run enforce_three() in code.
- JSON reliability. Fix: strip fences, find braces, fail closed.
- Public endpoint blast radius. AuthType NONE for demos, with input size caps, short timeouts, and least-privilege IAM for Bedrock only.
- New-account Bedrock quotas can sit at zero until AWS fully activates the account. The Lambda path still prefers Bedrock models first, then falls back to a deterministic prioritizer so the live demo never 500s.

## AWS Services Used / Architecture Overview

- AWS Lambda (Python 3.12): hosts UI and API
- Lambda Function URL: public HTTPS endpoint
- Amazon Bedrock (Amazon Nova Lite / APAC inference profiles): AI extraction and prioritization when quotas are active
- IAM: least-privilege invoke/converse on model ARNs
- AWS CLI packaging for deploy

Request path:

Browser GET Function URL returns HTML. Browser POST sends brain_dump, hours, energy, and context. Lambda validates input, calls Bedrock when available, runs enforce_three(), and returns JSON with today, parked, killed, and schedule.

Why this shape: serverless, Free Tier friendly, explainable, and demoable as one link.

## What You Learned

1. Constraint engines beat prompt engineering for promises you must keep. Only three things today belongs in code, not only in a system prompt.
2. Small models are enough for triage UX when the job is structured extraction, not essay writing.
3. Same-origin Function URL UX removes an entire class of CORS and deploy-order bugs.
4. Energy and time are different axes. High-impact deep work on a low-energy day is a trap.
5. Ship the article structure while you build: Vision, Build story, Architecture, Learning, Link.
6. Public AI endpoints need a cost and blast-radius story even for a weekend demo.

## Link to App or Repo

Live app (AWS Lambda Function URL):
https://wqei6w7s64dcwymw7it2m7fcki0oektc.lambda-url.ap-southeast-2.on.aws/

Source code (public GitHub repo):
https://github.com/shxkir/threetoday

Open the live app, click Load sample, then Lock my three to see a finishable day plan.

## Closing

ThreeToday is a small app with a sharp opinion: productivity is subtraction. AWS made it practical to put that opinion behind a real HTTPS endpoint in a weekend. Lambda runs the app, Bedrock is the language layer when active, and IAM bounds the blast radius. If the jacket is the prize, the lasting win is a tool I actually open on chaotic mornings.
