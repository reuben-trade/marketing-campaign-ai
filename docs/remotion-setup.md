# Remotion Lambda Setup Guide

This guide walks you through setting up Remotion Lambda for cloud-based video rendering in the Marketing Campaign AI platform.

## Overview

Remotion Lambda enables serverless video rendering on AWS, allowing you to:
- Render videos without managing servers
- Scale to handle multiple concurrent renders
- Pay only for actual rendering time

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js 18+** installed
4. **Python 3.11+** installed

## Quick Setup (5 minutes)

### 1. Install AWS CLI

```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure with your credentials
aws configure
```

### 2. Set Up IAM Permissions

Create an IAM policy with the permissions in `infrastructure/remotion/iam-policy.json`:

```bash
aws iam create-policy \
  --policy-name RemotionLambdaPolicy \
  --policy-document file://infrastructure/remotion/iam-policy.json
```

Attach the policy to your IAM user or role.

### 3. Deploy Remotion Lambda

```bash
# Install dependencies
cd remotion
npm install @remotion/lambda --save

# Deploy (uses us-east-1 by default)
cd ..
python infrastructure/remotion/deploy.py
```

### 4. Configure Environment

Add the output values to your `.env`:

```env
# Remotion Lambda Configuration
REMOTION_AWS_REGION=us-east-1
REMOTION_FUNCTION_NAME=remotion-render-3-3-123
REMOTION_SITE_NAME=marketing-campaign-ai-us-east-1

# Optional: Explicit AWS credentials (uses default chain if not set)
# AWS_ACCESS_KEY_ID=your-key-id
# AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 5. Test the Setup

```bash
# Check deployment status
python infrastructure/remotion/deploy.py --check

# Run the test suite
poetry run pytest tests/test_services/test_remotion_renderer.py -v
```

## Configuration Options

### Memory Settings

Remotion recommends 3009 MB for most videos. Increase for larger/complex videos:

```bash
python infrastructure/remotion/deploy.py --memory 4096
```

| Video Type | Recommended Memory |
|------------|-------------------|
| Standard 1080p, < 60s | 3009 MB |
| Complex 1080p, > 60s | 4096 MB |
| 4K content | 6144 MB |

### Regional Deployment

Deploy to a region closer to your users for faster uploads:

```bash
python infrastructure/remotion/deploy.py --region eu-west-1
```

Supported regions: us-east-1, us-west-2, eu-west-1, ap-southeast-1, etc.

### Disk Size

For videos with many assets or longer durations:

```bash
python infrastructure/remotion/deploy.py --disk 4096
```

## How It Works

### Render Flow

```
1. User triggers render via API
   POST /api/render { project_id, payload }

2. Backend creates render job in database
   status: "pending"

3. Backend invokes Remotion Lambda
   - Sends composition ID and props
   - Lambda distributes work across chunks

4. Lambda renders video
   - Chunks rendered in parallel
   - Chunks concatenated
   - Output uploaded to S3

5. Backend downloads from S3
   - Transfers to Supabase storage
   - Updates render status to "completed"

6. User receives video URL
```

### Automatic Mode Selection

The backend automatically chooses the render mode:

```python
# If REMOTION_AWS_REGION is set: uses Lambda
# Otherwise: uses local CLI rendering

# You can also force a specific mode:
POST /api/render?mode=lambda
POST /api/render?mode=local
```

## Monitoring & Debugging

### View Lambda Logs

```bash
# List recent renders
aws logs filter-log-events \
  --log-group-name /aws/lambda/remotion-render-xxx \
  --limit 50
```

### Check Render Status

```bash
# Via API
curl http://localhost:8000/api/render/{render_id}

# Via database
poetry run python -c "
from app.models.rendered_video import RenderedVideo
# ... query database
"
```

### Common Issues

#### "Function not found"

Ensure the function name in `.env` matches exactly:
```bash
python infrastructure/remotion/deploy.py --check
```

#### Timeout Errors

Increase timeout (max 900 seconds):
```bash
python infrastructure/remotion/deploy.py --timeout 900
```

#### Memory Errors

Increase Lambda memory:
```bash
python infrastructure/remotion/deploy.py --memory 4096
```

#### Permission Denied

Check IAM policy is correctly attached:
```bash
aws sts get-caller-identity
aws iam list-attached-user-policies --user-name YOUR_USER
```

## Cost Management

### Estimated Costs

| Operation | Cost (us-east-1) |
|-----------|------------------|
| 30s video @ 1080p | ~$0.15 |
| 60s video @ 1080p | ~$0.25 |
| 30s video @ 4K | ~$0.40 |

### Cost Optimization

1. **Use appropriate memory**: Don't over-provision
2. **Clean up old renders**: Delete unused S3 objects
3. **Use Supabase for storage**: Transfer rendered videos out of Lambda S3

### Set Up Billing Alerts

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name remotion-lambda-cost-alert \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT:billing-alerts
```

## Cleanup

To remove all Remotion Lambda resources:

```bash
python infrastructure/remotion/deploy.py --cleanup
```

This removes:
- Lambda functions
- S3 buckets (Remotion-managed)
- Lambda layers

**Note**: Remove IAM policies manually if no longer needed.

## Advanced Configuration

### Custom Compositions

Register new compositions in `remotion/src/Root.tsx`:

```tsx
<Composition
  id="custom_ad_v1"
  component={CustomAd}
  durationInFrames={300}
  fps={30}
  width={1080}
  height={1920}
/>
```

Then redeploy the site:

```bash
npx remotion lambda sites create --region us-east-1 --site-name marketing-campaign-ai-us-east-1
```

### Webhook Callbacks

Configure webhook for render completion:

```env
RENDER_CALLBACK_URL=https://your-domain.com/api/render/callback
RENDER_CALLBACK_SECRET=your-secret-key
```

### Provisioned Concurrency

For consistent cold-start performance:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name remotion-render-xxx \
  --qualifier $LATEST \
  --provisioned-concurrent-executions 2
```

Note: This incurs continuous charges.

## Resources

- [Remotion Lambda Documentation](https://www.remotion.dev/docs/lambda)
- [Remotion Pricing Calculator](https://www.remotion.dev/lambda/pricing)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Project Architecture](../README.md)
