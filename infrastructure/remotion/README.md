# Remotion Lambda Infrastructure

This directory contains deployment scripts and configuration for Remotion Lambda, which enables cloud-based video rendering on AWS.

## Overview

Remotion Lambda allows rendering videos in AWS Lambda functions, providing:
- **Scalability**: Render multiple videos in parallel
- **No server management**: Fully serverless architecture
- **Pay-per-use**: Only pay for actual render time
- **Fast rendering**: Distributed rendering across chunks

## Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** installed and configured with appropriate credentials
2. **Node.js 18+** installed
3. **AWS IAM permissions** (see `iam-policy.json` for required permissions)

## Quick Start

### 1. Install Dependencies

```bash
cd remotion
npm install @remotion/lambda --save
```

### 2. Deploy Lambda Function

```bash
# Deploy to us-east-1 with default settings
python infrastructure/remotion/deploy.py --region us-east-1

# Deploy with custom memory (for larger videos)
python infrastructure/remotion/deploy.py --region us-east-1 --memory 4096
```

### 3. Configure Environment

Add the following to your `.env` file:

```env
REMOTION_AWS_REGION=us-east-1
REMOTION_FUNCTION_NAME=remotion-render-xxxxx
REMOTION_SITE_NAME=marketing-campaign-ai-us-east-1
```

## Deployment Script Options

```bash
python infrastructure/remotion/deploy.py [OPTIONS]

Options:
  --region      AWS region (default: us-east-1)
  --memory      Lambda memory in MB (default: 3009, recommended by Remotion)
  --timeout     Lambda timeout in seconds (default: 900)
  --disk        Lambda disk size in MB (default: 2048)
  --check       Check deployment status only
  --cleanup     Remove all Remotion Lambda resources
```

## IAM Permissions

The `iam-policy.json` file contains the minimum IAM permissions required to deploy Remotion Lambda. Attach this policy to the IAM user or role that will run the deployment.

```bash
aws iam create-policy \
  --policy-name RemotionLambdaDeployPolicy \
  --policy-document file://infrastructure/remotion/iam-policy.json
```

## Architecture

```
                                    ┌──────────────────┐
                                    │   AWS Lambda     │
                                    │ (remotion-render)│
                                    └────────┬─────────┘
                                             │
┌─────────────┐     ┌────────────┐          │
│   Backend   │────▶│ Lambda API │──────────┤
│ (FastAPI)   │     └────────────┘          │
└─────────────┘                              │
                                    ┌────────▼─────────┐
                                    │   S3 Buckets     │
                                    │ - Input videos   │
                                    │ - Remotion bundle│
                                    │ - Output renders │
                                    └──────────────────┘
```

## Costs

Remotion Lambda costs depend on:

1. **Lambda execution time**: Based on memory and duration
2. **S3 storage**: For input/output videos and bundles
3. **Data transfer**: Downloading input and uploading output

### Estimated Costs (US East 1)

| Video Length | Memory | Approx. Cost |
|--------------|--------|--------------|
| 30s @ 1080p  | 3009MB | ~$0.15       |
| 60s @ 1080p  | 3009MB | ~$0.25       |
| 30s @ 4K     | 4096MB | ~$0.40       |

## Troubleshooting

### "Function not found" error

1. Check that deployment completed successfully:
   ```bash
   python infrastructure/remotion/deploy.py --check
   ```

2. Verify environment variables are set correctly in `.env`

### Timeout errors

Increase Lambda timeout (max 900 seconds):
```bash
python infrastructure/remotion/deploy.py --timeout 900
```

### Memory errors

Increase Lambda memory for larger videos:
```bash
python infrastructure/remotion/deploy.py --memory 4096
```

### Permission errors

Ensure IAM policy is correctly attached:
```bash
aws iam list-attached-user-policies --user-name YOUR_USER
```

## Cleanup

To remove all Remotion Lambda resources:

```bash
python infrastructure/remotion/deploy.py --cleanup
```

This removes:
- Lambda functions
- S3 buckets (Remotion-created)
- Lambda layers

**Note**: This does not remove IAM roles/policies - remove those manually if needed.

## More Information

- [Remotion Lambda Documentation](https://www.remotion.dev/docs/lambda)
- [Remotion Pricing Calculator](https://www.remotion.dev/lambda/pricing)
- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
