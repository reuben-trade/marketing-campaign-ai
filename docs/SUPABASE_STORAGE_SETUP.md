# Supabase Storage Setup

This document explains how to set up the required Supabase storage buckets for the Marketing Campaign AI application.

## Required Buckets

The application requires the following storage buckets:

1. **ad-creatives** - Stores ad creative files (images and videos) from Meta Ad Library
2. **strategy-documents** - Stores strategy PDF documents
3. **screenshots** - Stores landing page screenshots
4. **critique-files** - Stores user-uploaded critique files (images and videos)

## Creating Buckets

### Step 1: Access Supabase Dashboard

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Select your project
3. Navigate to **Storage** in the left sidebar

### Step 2: Create Each Bucket

For each bucket listed above:

1. Click the **"New bucket"** button
2. Enter the bucket name (e.g., `ad-creatives`)
3. **Important:** Set the bucket to **Public** for file access
   - Toggle "Public bucket" to ON
4. Click **"Create bucket"**

### Step 3: Configure Bucket Policies (Optional)

For production deployments, you may want to configure bucket policies to:

- Limit file sizes
- Restrict file types
- Set up automatic deletion rules

Example policy for the `critique-files` bucket:

```sql
-- Allow public read access
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'critique-files' );

-- Allow authenticated uploads
CREATE POLICY "Authenticated uploads"
ON storage.objects FOR INSERT
WITH CHECK ( bucket_id = 'critique-files' AND auth.role() = 'authenticated' );
```

## Bucket Structure

### ad-creatives
```
ad-creatives/
└── competitors/
    └── {competitor_id}/
        ├── images/
        │   └── {ad_id}.jpg
        └── videos/
            └── {ad_id}.mp4
```

### strategy-documents
```
strategy-documents/
└── {strategy_id}.pdf
```

### screenshots
```
screenshots/
└── {landing_page_id}.png
```

### critique-files
```
critique-files/
├── images/
│   └── {critique_id}.jpg
└── videos/
    └── {critique_id}.mp4
```

## Verification

After creating the buckets, you can verify they're set up correctly by:

1. Uploading a test file through the Supabase dashboard
2. Checking that the file is publicly accessible
3. Running the application and testing file uploads

## Environment Variables

Make sure your `.env` file includes the Supabase configuration:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

The bucket names are configured in `app/config.py` with the following defaults:
- `ad_creatives_bucket`: "ad-creatives"
- `strategy_documents_bucket`: "strategy-documents"
- `supabase_screenshots_bucket`: "screenshots"
- `critique_files_bucket`: "critique-files"

## Troubleshooting

### Files not accessible
- Ensure buckets are set to **Public**
- Check CORS settings in Supabase if accessing from web frontend
- Verify the service role key has proper permissions

### Upload failures
- Check file size limits
- Verify content-type headers are correct
- Check Supabase logs for detailed error messages

### Storage quota
- Monitor your storage usage in the Supabase dashboard
- Consider implementing cleanup policies for old files
- Upgrade your Supabase plan if needed
