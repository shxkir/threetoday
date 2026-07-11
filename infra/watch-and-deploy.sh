#!/usr/bin/env bash
# Poll until AWS account verification unlocks Lambda, then deploy ThreeToday.
set -u
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export AWS_PAGER=""
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ap-southeast-2}"
export AWS_REGION="${AWS_REGION:-ap-southeast-2}"
export MODEL_ID="${MODEL_ID:-amazon.nova-lite-v1:0}"
export FN_NAME="${FN_NAME:-threetoday}"
export ROLE_NAME="${ROLE_NAME:-threetoday-lambda-role}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${LOG:-/tmp/threetoday-autodeploy.log}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-180}"  # ~3 hours @ 60s
SLEEP_SECS="${SLEEP_SECS:-60}"

echo "watch-and-deploy start $(date)" | tee -a "$LOG"

lambda_ok() {
  if aws lambda list-functions --region "$AWS_REGION" >/dev/null 2>&1; then
    return 0
  fi
  if AWS_PROFILE=threetoday aws lambda list-functions --region "$AWS_REGION" >/dev/null 2>&1; then
    export AWS_PROFILE=threetoday
    return 0
  fi
  return 1
}

for i in $(seq 1 "$MAX_ATTEMPTS"); do
  if lambda_ok; then
    echo "LAMBDA READY attempt=$i $(date)" | tee -a "$LOG"
    cd "$SCRIPT_DIR"
    ./deploy-cli.sh 2>&1 | tee -a "$LOG"
    URL=$(aws lambda get-function-url-config \
      --function-name "$FN_NAME" \
      --region "$AWS_REGION" \
      --query FunctionUrl \
      --output text 2>/dev/null || true)
    echo "URL=$URL" | tee -a "$LOG"
    if [ -n "${URL:-}" ] && [ "$URL" != "None" ]; then
      curl -sS -X POST "$URL" \
        -H 'Content-Type: application/json' \
        -d '{"brain_dump":"- finish client proposal\n- reply to 3 leads\n- maybe learn Rust\n- gym\n- send invoice","hours":4,"energy":"medium","context":"Friday deadline"}' \
        | tee /tmp/threetoday-test.json | head -c 3000 | tee -a "$LOG"
      echo | tee -a "$LOG"
      # Persist URL for article
      echo "$URL" > "$SCRIPT_DIR/../.function-url"
    fi
    echo "DONE $(date)" | tee -a "$LOG"
    exit 0
  fi
  err=$(aws bedrock-runtime converse \
    --model-id amazon.nova-lite-v1:0 \
    --messages '[{"role":"user","content":[{"text":"x"}]}]' \
    --inference-config '{"maxTokens":5}' \
    --region "$AWS_REGION" 2>&1 | head -1)
  echo "[$i $(date +%H:%M:%S)] waiting: ${err:0:160}" | tee -a "$LOG"
  sleep "$SLEEP_SECS"
done

echo "TIMEOUT $(date)" | tee -a "$LOG"
exit 1
