#!/usr/bin/env bash
# Deploy ThreeToday to AWS (SAM).
# Prerequisites: AWS CLI, SAM CLI, Bedrock model access for Nova Lite in the target region.
set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
STACK_NAME="${STACK_NAME:-threetoday}"
MODEL_ID="${MODEL_ID:-amazon.nova-lite-v1:0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> ThreeToday deploy"
echo "    Region:     $REGION"
echo "    Stack:      $STACK_NAME"
echo "    Model:      $MODEL_ID"
echo "    Project:    $ROOT_DIR"

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: AWS CLI not found. Install: brew install awscli"
  exit 1
fi

if ! command -v sam >/dev/null 2>&1; then
  echo "ERROR: SAM CLI not found. Install: brew install aws-sam-cli"
  exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "ERROR: AWS credentials not configured. Run: aws configure"
  exit 1
fi

echo "==> Building…"
cd "$SCRIPT_DIR"
sam build --template-file template.yaml

echo "==> Deploying…"
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides "ModelId=$MODEL_ID" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" \
  --output text)

echo ""
echo "============================================"
echo "  ThreeToday is live"
echo "  $URL"
echo "============================================"
echo ""
echo "If the app errors on plan generation, open Amazon Bedrock console →"
echo "Model access → enable Amazon Nova Lite in region: $REGION"
echo ""
