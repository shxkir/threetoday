# ThreeToday Architecture

## Goal

Turn a messy brain dump into a **finishable day**: at most three outcomes, within a real hour budget, with a first move for each.

## High-level flow

```text
┌─────────────┐   GET /    ┌──────────────────────────┐
│   Browser   │ ─────────► │ AWS Lambda (Python 3.12) │
│  ThreeToday │ ◄───────── │  serves HTML UI          │
│     UI      │            └──────────────────────────┘
│             │   POST /   ┌──────────────────────────┐
│             │ ─────────► │ same Lambda              │
│             │            │  1. validate input       │
│             │            │  2. Bedrock Nova Lite    │
│             │            │  3. enforce_three()      │
│             │ ◄───────── │  4. JSON plan            │
└─────────────┘            └────────────┬─────────────┘
                                        │
                                        ▼
                           ┌──────────────────────────┐
                           │ Amazon Bedrock           │
                           │ amazon.nova-lite-v1:0    │
                           └──────────────────────────┘
```

Public entrypoint: **Lambda Function URL** (`AuthType: NONE` for challenge demos).

## Separation of concerns

| Layer | Responsibility |
| --- | --- |
| **UI** | Capture brain dump, hours, energy, context; render plan |
| **Nova Lite** | Extract candidates, score, suggest bucket, write first moves |
| **`enforce_three()`** | Hard cap of 3 today items; hour budget; energy bias; schedule |

The model **suggests**. The code **decides**. That keeps the product promise honest even when the model is optimistic.

## AWS resources

| Resource | Purpose |
| --- | --- |
| `AWS::Serverless::Function` / Lambda | App + API |
| Function URL | HTTPS endpoint |
| IAM role | `bedrock:InvokeModel`, `bedrock:Converse` on Nova model ARNs only |
| CloudWatch Logs | Via basic Lambda execution role |

No database in v1 — nothing stored server-side.

## Security (demo posture)

- Input capped at 6,000 characters  
- Timeout 60s, memory 256 MB, arm64  
- Least-privilege Bedrock permissions  
- No secrets in the client  

Production follow-ups: Cognito or API key, Bedrock Guardrails, WAF + custom domain.

## Deploy

```bash
# After AWS account verification completes:
cd infra && ./deploy-cli.sh
# or
cd infra && ./deploy.sh   # requires SAM CLI
```

Region used for this submission: **ap-southeast-2** (Sydney).

## Local development

```bash
python3 local_server.py          # mock AI
USE_BEDROCK=1 python3 local_server.py  # real Nova (needs model access)
make test
```
