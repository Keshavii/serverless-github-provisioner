#!/bin/bash

LOG_GROUP="/aws/lambda/github-repo-automation-test-repo-creator"
REGION="us-east-1"

show_help() {
    cat << EOF
📊 Repository Creator Lambda Log Viewer

Usage: ./scripts/check-lambda-logs.sh [OPTIONS]

OPTIONS:
    -t, --tail          Live tail logs (real-time)
    -r, --recent        Show recent logs (last 30 minutes)
    -e, --errors        Show only errors
    -c, --correlation   Filter by correlation ID (requires ID argument)
    -j, --jira          Filter by JIRA ticket ID (requires ticket argument)
    -h, --help          Show this help message

EXAMPLES:
    # Live tail all logs
    ./scripts/check-lambda-logs.sh --tail

    # Show recent logs
    ./scripts/check-lambda-logs.sh --recent

    # Show only errors in last hour
    ./scripts/check-lambda-logs.sh --errors

    # Track specific correlation ID
    ./scripts/check-lambda-logs.sh --correlation abc-123-def-456

    # Track specific JIRA ticket
    ./scripts/check-lambda-logs.sh --jira PROJ-123

CLOUDWATCH CONSOLE:
    https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/\$252Faws\$252Flambda\$252Fgithub-repo-automation-test-repo-creator

EOF
}

if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

case "$1" in
    -t|--tail)
        echo "📡 Live tailing logs for Repository Creator Lambda..."
        aws logs tail "$LOG_GROUP" --follow --region "$REGION"
        ;;
    
    -r|--recent)
        echo "📋 Recent logs (last 30 minutes)..."
        aws logs tail "$LOG_GROUP" --since 30m --region "$REGION"
        ;;
    
    -e|--errors)
        echo "❌ Filtering for ERROR level logs..."
        aws logs tail "$LOG_GROUP" --filter-pattern "ERROR" --since 1h --region "$REGION"
        ;;
    
    -c|--correlation)
        if [ -z "$2" ]; then
            echo "❌ Error: Correlation ID required"
            echo "Usage: $0 --correlation <correlation-id>"
            exit 1
        fi
        echo "🔍 Filtering for correlation ID: $2"
        aws logs tail "$LOG_GROUP" --filter-pattern "$2" --since 2h --region "$REGION"
        ;;
    
    -j|--jira)
        if [ -z "$2" ]; then
            echo "❌ Error: JIRA ticket ID required"
            echo "Usage: $0 --jira <ticket-id>"
            exit 1
        fi
        echo "🎫 Filtering for JIRA ticket: $2"
        aws logs tail "$LOG_GROUP" --filter-pattern "$2" --since 2h --region "$REGION"
        ;;
    
    -h|--help)
        show_help
        ;;
    
    *)
        echo "❌ Unknown option: $1"
        show_help
        exit 1
        ;;
esac
