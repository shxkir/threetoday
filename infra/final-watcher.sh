#!/bin/bash
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin:$PATH"
export AWS_PAGER=""
export AWS_DEFAULT_REGION=ap-southeast-2
export AWS_REGION=ap-southeast-2
export MODEL_ID=amazon.nova-lite-v1:0
export FN_NAME=threetoday
export ROLE_NAME=threetoday-lambda-role
LOG=/tmp/threetoday-autodeploy.log
ROOT=/Users/ismaielshakir/threetoday
echo "FINAL watcher start $(date)" | tee -a "$LOG"
for i in $(seq 1 240); do
  if aws lambda list-functions --region ap-southeast-2 >/dev/null 2>&1; then
    :
  elif AWS_PROFILE=threetoday aws lambda list-functions --region ap-southeast-2 >/dev/null 2>&1; then
    export AWS_PROFILE=threetoday
  else
    echo "[$i $(date +%H:%M:%S)] still locked" | tee -a "$LOG"
    sleep 45
    continue
  fi
  echo "UNLOCKED $(date)" | tee -a "$LOG"
  cd "$ROOT/infra" && ./deploy-cli.sh 2>&1 | tee -a "$LOG"
  URL=$(aws lambda get-function-url-config --function-name threetoday --region ap-southeast-2 --query FunctionUrl --output text 2>/dev/null || true)
  echo "URL=$URL" | tee -a "$LOG"
  printf '%s\n' "$URL" > "$ROOT/.function-url"
  if [ -n "$URL" ] && [ "$URL" != "None" ]; then
    python3 -c "
from pathlib import Path
url=Path('$ROOT/.function-url').read_text().strip()
for rel in ['article/ARTICLE.md','article/BODY_PASTE.md']:
 p=Path('$ROOT')/rel
 t=p.read_text()
 t=t.replace('Pending AWS account verification (auto-deploy watcher running). Will be added as soon as Lambda unlocks.', url)
 t=t.replace('*(Deploy pending AWS account verification — will be added immediately after Lambda unlocks. Repo link satisfies the challenge link requirement in the meantime.)*', url)
 p.write_text(t)
print('patched', url)
"
    curl -sS -X POST "$URL" -H 'Content-Type: application/json' \
      -d '{"brain_dump":"- finish proposal\n- reply leads\n- maybe learn rust\n- send invoice","hours":4,"energy":"medium"}' \
      | head -c 1500 | tee -a "$LOG"
    echo | tee -a "$LOG"
    open -a "Google Chrome" "$URL" || true
  fi
  echo "DEPLOY COMPLETE $(date)" | tee -a "$LOG"
  exit 0
done
echo "TIMEOUT $(date)" | tee -a "$LOG"
exit 1
