#!/bin/bash

echo "🚀 Testing Complete Flow - RELB-7993"
echo "======================================"

# Create simple test payload with Repo-Creation-Automation org
cat > test-payload.json << 'EOF'
{
  "body": "{\"timestamp\":1744359061322,\"webhookEvent\":\"jira:issue_created\",\"issue\":{\"id\":\"2609440\",\"key\":\"RELB-9254 \",\"fields\":{\"issuetype\":{\"name\":\"Repo Creation\"},\"summary\":\"Test Flow Manual\",\"status\":{\"name\":\"To Do\"},\"labels\":[\"repo-automation\"],\"customfield_27191\":\"repo-test-auto-web-001\",\"customfield_27192\":{\"value\":\"Repo-Creation-Automation\"},\"customfield_27193\":{\"value\":\"Private\"},\"customfield_27194\":{\"value\":\"Python\"},\"customfield_27195\":{\"displayName\":\"Hiya Modi\"},\"customfield_27196\":{\"displayName\":\"Hiya Modi\"},\"customfield_27197\":{\"displayName\":\"Hiya Modi\"},\"customfield_27198\":{\"value\":\"Platform\"}}}}"
}
EOF

echo "✅ Payload created with org: Repo-Creation-Automation"
echo ""

# Send to Lambda
echo "📤 Sending to webhook handler Lambda..."
aws lambda invoke \
  --function-name github-repo-automation-test-webhook-handler \
  --region us-east-1 \
  --payload file://test-payload.json \
  response.json

echo "Lambda invoke exit code: $?"

echo ""
echo "📄 Lambda Response:"
cat response.json
echo ""

# Wait for processing
echo "⏳ Waiting 20 seconds for complete flow..."
sleep 20

# Check JIRA for last update
echo ""
echo "📊 Checking JIRA RELB-7924 for latest update..."
echo "======================================"

curl -s -u "hiya.modi.here@gmail.com:DUMMY_TOKEN" \
  "https://hiyamodi.atlassian.net/rest/api/3/issue/RELB-9254?fields=comment,updated" | \
jq -r '
"JIRA Ticket: RELB-7924",
"Last Updated: " + .fields.updated,
"Total Comments: " + (.fields.comment.total | tostring),
"",
"Latest Comment:",
"  Time: " + .fields.comment.comments[-1].created,
"  Author: " + .fields.comment.comments[-1].author.displayName,
"  Message: " + (.fields.comment.comments[-1].body.content[0].content[0].text // "No text")[0:200]
'

echo ""
echo "======================================"
echo "✅ Test Complete!"

# Cleanup
rm -f test-payload.json response.json
