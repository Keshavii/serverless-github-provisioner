#!/bin/bash

echo "=================================================="
echo "  Lambda Deployment Verification Script"
echo "=================================================="
echo ""

FUNCTION_NAME="github-repo-automation-test-repo-creator"
REGION="us-east-1"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Checking Lambda Function Info...${NC}"
echo "---------------------------------------------------"
aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Configuration.{LastModified:LastModified,Runtime:Runtime,CodeSize:CodeSize,Handler:Handler}' \
  --output table

echo ""
echo -e "${BLUE}2. Checking Lambda Code SHA256...${NC}"
echo "---------------------------------------------------"
aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Configuration.CodeSha256' \
  --output text

echo ""
echo -e "${BLUE}3. Checking Environment Variables...${NC}"
echo "---------------------------------------------------"
aws lambda get-function-configuration \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Environment.Variables' \
  --output json

echo ""
echo -e "${BLUE}4. Testing if new modules are in deployment package...${NC}"
echo "---------------------------------------------------"
echo "Downloading Lambda deployment package..."

# Download the Lambda function code
aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --region $REGION \
  --query 'Code.Location' \
  --output text | xargs curl -s -o /tmp/lambda-deployment.zip

echo "Checking for new modules in package..."
unzip -l /tmp/lambda-deployment.zip | grep -E "(github_handler|workflow_processor|message_parser|error_handlers|secrets_manager)\.py"

echo ""
echo -e "${YELLOW}✓ Files in deployment package:${NC}"
unzip -l /tmp/lambda-deployment.zip | grep "\.py$" | awk '{print "  - " $4}'

echo ""
echo -e "${BLUE}5. Checking Recent Lambda Invocations...${NC}"
echo "---------------------------------------------------"
echo "Last 5 invocations from CloudWatch Logs:"

# Get the most recent log stream
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"
LATEST_STREAM=$(aws logs describe-log-streams \
  --log-group-name $LOG_GROUP \
  --region $REGION \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null)

if [ "$LATEST_STREAM" != "None" ] && [ -n "$LATEST_STREAM" ]; then
  echo "Latest log stream: $LATEST_STREAM"
  echo ""
  aws logs get-log-events \
    --log-group-name $LOG_GROUP \
    --log-stream-name "$LATEST_STREAM" \
    --region $REGION \
    --limit 20 \
    --query 'events[*].message' \
    --output text | tail -20
else
  echo -e "${YELLOW}No recent invocations found${NC}"
fi

echo ""
echo -e "${GREEN}=================================================="
echo "  Verification Complete!"
echo -e "==================================================${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "  1. Check 'LastModified' timestamp - should be recent"
echo "  2. Verify all 5 new modules are in the deployment package"
echo "  3. Look for recent log entries showing your changes"
echo ""
echo -e "${YELLOW}🔄 To redeploy:${NC}"
echo "  cd infra/environments/test"
echo "  terraform apply -auto-approve"
echo ""
