#!/usr/bin/env bash
# Deploy ThreeToday with AWS CLI only (no SAM required).
set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
FN_NAME="${FN_NAME:-threetoday}"
ROLE_NAME="${ROLE_NAME:-threetoday-lambda-role}"
MODEL_ID="${MODEL_ID:-amazon.nova-lite-v1:0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/../src" && pwd)"
ZIP_PATH="/tmp/threetoday-lambda.zip"

echo "==> CLI deploy → $FN_NAME ($REGION)"

if ! command -v aws >/dev/null 2>&1; then
  echo "Install AWS CLI first: brew install awscli"
  exit 1
fi
aws sts get-caller-identity >/dev/null

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Create role if missing
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "==> Creating IAM role $ROLE_NAME"
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{
        "Effect":"Allow",
        "Principal":{"Service":"lambda.amazonaws.com"},
        "Action":"sts:AssumeRole"
      }]
    }' >/dev/null

  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  cat > /tmp/threetoday-bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:Converse"],
    "Resource": [
      "arn:aws:bedrock:${REGION}::foundation-model/${MODEL_ID}",
      "arn:aws:bedrock:${REGION}::foundation-model/amazon.nova-lite-v1:0",
      "arn:aws:bedrock:${REGION}::foundation-model/amazon.nova-micro-v1:0"
    ]
  }]
}
EOF
  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name threetoday-bedrock \
    --policy-document file:///tmp/threetoday-bedrock-policy.json

  echo "    Waiting for IAM role propagation…"
  sleep 10
fi

echo "==> Packaging Lambda"
rm -f "$ZIP_PATH"
(
  cd "$SRC_DIR"
  zip -q "$ZIP_PATH" lambda_function.py
)

if aws lambda get-function --function-name "$FN_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "==> Updating function code"
  aws lambda update-function-code \
    --function-name "$FN_NAME" \
    --zip-file "fileb://$ZIP_PATH" \
    --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FN_NAME" --region "$REGION"
  aws lambda update-function-configuration \
    --function-name "$FN_NAME" \
    --runtime python3.12 \
    --handler lambda_function.handler \
    --timeout 60 \
    --memory-size 256 \
    --architectures arm64 \
    --environment "Variables={MODEL_ID=$MODEL_ID}" \
    --region "$REGION" >/dev/null
else
  echo "==> Creating function"
  aws lambda create-function \
    --function-name "$FN_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --handler lambda_function.handler \
    --zip-file "fileb://$ZIP_PATH" \
    --timeout 60 \
    --memory-size 256 \
    --architectures arm64 \
    --environment "Variables={MODEL_ID=$MODEL_ID}" \
    --region "$REGION" >/dev/null
  aws lambda wait function-active --function-name "$FN_NAME" --region "$REGION"
fi

# Function URL
if ! aws lambda get-function-url-config --function-name "$FN_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "==> Creating Function URL"
  aws lambda create-function-url-config \
    --function-name "$FN_NAME" \
    --auth-type NONE \
    --cors 'AllowOrigins=*,AllowMethods=GET,POST,AllowHeaders=content-type' \
    --region "$REGION" >/dev/null

  aws lambda add-permission \
    --function-name "$FN_NAME" \
    --statement-id FunctionURLAllowPublicAccess \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE \
    --region "$REGION" >/dev/null 2>&1 || true
fi

URL=$(aws lambda get-function-url-config \
  --function-name "$FN_NAME" \
  --region "$REGION" \
  --query FunctionUrl \
  --output text)

echo ""
echo "============================================"
echo "  ThreeToday is live"
echo "  $URL"
echo "============================================"
echo "Enable Amazon Nova Lite in Bedrock model access ($REGION) if not already."
