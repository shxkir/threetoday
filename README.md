# ThreeToday

**Weekend Productivity Challenge** entry — an AI-powered daily focus planner on AWS.

Paste a messy brain dump. Set your real hours and energy. Get **exactly three** finishable outcomes, a first move for each, a focus schedule, plus parked and killed lists.

Built with **AWS Lambda** + **Lambda Function URL** + **Amazon Bedrock (Nova Lite)**.

## Challenge fit

| Requirement | How ThreeToday meets it |
| --- | --- |
| AI-powered productivity tool | Bedrock Nova Lite triages your dump |
| At least one AWS service | Lambda, Function URL, Bedrock, IAM |
| Working link or public repo | Function URL after deploy / this repo |
| Article title pattern | `Weekend Productivity Challenge: ThreeToday` |
| Tag | `#productivity` |

Deadline: **July 13, 2026, 1:00 PM PT** · Prize: first **50 qualifying** submissions → AWS Builder Jacket.

## Quick start (local, no AWS)

```bash
cd threetoday
python3 local_server.py
# open http://127.0.0.1:8080
# uses mock AI — full UI + deterministic max-3 logic
```

Real Bedrock locally:

```bash
export USE_BEDROCK=1
export AWS_REGION=us-east-1
# ensure AWS creds + Nova Lite model access in that region
python3 local_server.py
```

## Deploy to AWS

### 1. Prerequisites

- AWS account (you said yours is set up)
- Enable **Amazon Nova Lite** under Amazon Bedrock → Model access (same region you deploy to, e.g. `us-east-1`)
- Tools:

```bash
brew install awscli aws-sam-cli
aws configure
```

### 2. Deploy

```bash
cd threetoday/infra
chmod +x deploy.sh
./deploy.sh
```

Copy the **Function URL** from the output. Open it in a browser → **Lock my three**.

### 3. Publish the article

Use `article/ARTICLE.md` — paste into Builder Center, add screenshots, set tag `#productivity`, add your live URL + repo link.

## Project layout

```
threetoday/
├── src/lambda_function.py   # UI + API + Bedrock + enforce_three()
├── src/requirements.txt
├── infra/template.yaml      # SAM template
├── infra/deploy.sh
├── local_server.py          # local UI + mock/real AI
├── article/ARTICLE.md       # ready-to-publish Builder Center article
└── README.md
```

## Architecture

```
GET  Function URL → HTML UI
POST Function URL → validate → Bedrock Nova Lite → enforce_three() → JSON plan
```

The model **suggests** candidates; **Python enforces** the hour budget and the hard cap of three today items.

## Security notes (demo)

- Function URL `AuthType: NONE` for easy challenge demos
- Input size capped; Lambda timeout 60s; arm64 256 MB
- IAM allows only Bedrock invoke/converse on the Nova model ARN
- No datastore — nothing retained server-side

For production: add Cognito or an API key, Bedrock Guardrails, and WAF on a custom domain.

## License

MIT — built for the AWS Builder Center Weekend Productivity Challenge (July 2026).
