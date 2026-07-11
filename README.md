# ThreeToday

**AWS Weekend Productivity Challenge** entry — an AI-powered daily focus planner.

Paste a messy brain dump. Set real hours + energy. Get **exactly three** finishable outcomes, a first move for each, a focus schedule, plus parked and killed lists.

**Stack:** AWS Lambda · Lambda Function URL · Amazon Bedrock (Nova Lite) · IAM  
**Repo:** https://github.com/shxkir/threetoday  
**Region:** `ap-southeast-2`

## Challenge fit

| Requirement | How ThreeToday meets it |
| --- | --- |
| AI-powered productivity tool | Bedrock Nova Lite triages your dump |
| At least one AWS service | Lambda, Function URL, Bedrock, IAM |
| Working link or public repo | This repo + Function URL after deploy |
| Article title | `Weekend Productivity Challenge: ThreeToday` |
| Tag | `#productivity` |

Deadline: **July 13, 2026, 1:00 PM PT** · First **50 qualifying** → AWS Builder Jacket.

## Quick start (local)

```bash
python3 local_server.py
# → http://127.0.0.1:8080  (mock AI, full UI)
make test
```

Real Bedrock (after account verification + model access):

```bash
USE_BEDROCK=1 AWS_REGION=ap-southeast-2 python3 local_server.py
```

## Deploy to AWS

> New accounts may show *“account is currently being verified”* for up to ~2 hours.
> Until then Lambda/S3/Bedrock invoke stay blocked.

```bash
# one-time tools
brew install awscli
aws login --region ap-southeast-2   # or configure access keys

# auto-deploy when verification clears
./infra/watch-and-deploy.sh

# or deploy immediately once Lambda works
./infra/deploy-cli.sh
```

Enable **Amazon Nova Lite** in Bedrock → Model access (`ap-southeast-2`) if prompted.

## Publish the article

1. Open [AWS Builder Center](https://builder.aws.com) → new article  
2. Title: **`Weekend Productivity Challenge: ThreeToday`**  
3. Tag: **`#productivity`**  
4. Paste `article/ARTICLE.md`  
5. Add Function URL (from deploy) + this GitHub link  
6. Attach screenshots from a local or live run  
7. Publish before **July 13, 2026 1:00 PM PT**

## Project layout

```
threetoday/
├── src/lambda_function.py     # UI + API + Bedrock + enforce_three()
├── local_server.py            # local mock / real Bedrock
├── tests/test_enforce.py      # deterministic planner tests
├── infra/
│   ├── template.yaml          # SAM
│   ├── deploy.sh / deploy-cli.sh
│   └── watch-and-deploy.sh    # poll verification → deploy
├── article/ARTICLE.md
├── docs/ARCHITECTURE.md
└── README.md
```

## Architecture

```
GET  Function URL → HTML UI
POST Function URL → validate → Bedrock Nova Lite → enforce_three() → JSON plan
```

The model **suggests**; Python **enforces** max-three + hour budget. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

MIT — AWS Builder Center Weekend Productivity Challenge (July 2026).
