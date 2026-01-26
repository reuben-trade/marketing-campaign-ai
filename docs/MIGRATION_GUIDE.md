# Migration Guide: Adding Video Storage to Critique Feature

This guide walks you through upgrading your existing Marketing Campaign AI deployment to support video storage for the critique feature.

## Prerequisites

- Access to your Supabase dashboard
- Database credentials with migration permissions
- Python environment with alembic installed

## Step 1: Create Supabase Storage Bucket

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Select your project
3. Navigate to **Storage** → **Buckets**
4. Click **"New bucket"**
5. Create a bucket named: `critique-files`
6. **Important**: Toggle "Public bucket" to **ON**
7. Click "Create bucket"

### Verify Bucket Creation

You should now see `critique-files` in your buckets list alongside:
- `ad-creatives`
- `strategy-documents`
- `screenshots`

## Step 2: Run Database Migration

The migration adds two new columns to the `critiques` table:
- `file_storage_path` (VARCHAR 1000) - Path to file in S3
- `file_url` (VARCHAR 2000) - Public URL to access the file

### Apply Migration

```bash
# From project root directory
alembic upgrade head
```

### Verify Migration

Connect to your database and check the critiques table:

```sql
-- Check that new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'critiques'
AND column_name IN ('file_storage_path', 'file_url');
```

Expected output:
```
   column_name     |     data_type
-------------------+--------------------
 file_storage_path | character varying
 file_url          | character varying
```

## Step 3: Update Environment Variables

No new environment variables are required! The bucket name uses the default `critique-files`.

If you want to customize the bucket name, add to `.env`:

```env
# Optional: Override default bucket name
CRITIQUE_FILES_BUCKET=your-custom-bucket-name
```

## Step 4: Deploy Backend Changes

Deploy the updated backend code:

```bash
# Pull latest changes
git pull origin main

# Install any new dependencies (if needed)
pip install -r requirements.txt

# Restart your backend service
# (Command depends on your deployment method)
# Examples:
systemctl restart marketing-campaign-ai
# or
docker-compose restart backend
# or
pm2 restart marketing-campaign-ai
```

## Step 5: Deploy Frontend Changes

Deploy the updated frontend code:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Deploy (method depends on your hosting)
# Examples:
# - Vercel: vercel --prod
# - Netlify: netlify deploy --prod
# - Custom: Copy build/ to your web server
```

## Step 6: Test the Feature

1. **Upload a new video critique**:
   - Go to `/critique` page
   - Upload a video file
   - Complete the analysis
   - Verify the video plays back correctly

2. **Check storage**:
   - Go to Supabase dashboard → Storage → `critique-files`
   - You should see a new file in `videos/{critique-id}.{ext}`

3. **Test retrieval**:
   - Reload the page
   - Click on the saved critique in the sidebar
   - Verify the video loads and plays

4. **Test deletion**:
   - Delete a critique
   - Check Supabase storage - file should be removed

## Backfill Existing Data (Optional)

If you have existing critiques in your database that don't have videos stored, you have two options:

### Option 1: Leave as-is (Recommended)

Existing critiques will continue to work without video playback. Only new critiques will have videos stored.

### Option 2: Manual Backfill

If you have the original video files and want to backfill them:

```python
# Example backfill script (run with caution!)
from app.utils.supabase_storage import SupabaseStorage
from app.models.critique import Critique
from app.database import get_db

async def backfill_videos():
    storage = SupabaseStorage()
    async for db in get_db():
        critiques = await db.execute(
            select(Critique).where(Critique.file_storage_path.is_(None))
        )

        for critique in critiques.scalars():
            # Load video file from your backup/archive
            video_path = f"./backups/{critique.id}.mp4"
            if not os.path.exists(video_path):
                continue

            with open(video_path, 'rb') as f:
                content = f.read()

            # Upload to storage
            storage_path = await storage.upload_critique_file(
                critique_id=critique.id,
                content=content,
                filename=critique.file_name,
                media_type=critique.media_type,
            )

            # Update database
            critique.file_storage_path = storage_path
            critique.file_url = storage.get_public_url(
                storage_path,
                bucket=storage.critique_files_bucket
            )

        await db.commit()

# Run it
asyncio.run(backfill_videos())
```

**Warning**: Only run backfill scripts on a database backup first!

## Rollback Instructions

If you need to rollback the changes:

### 1. Rollback Database

```bash
alembic downgrade -1
```

This removes the `file_storage_path` and `file_url` columns.

### 2. Revert Code

```bash
git checkout <previous-commit-hash>
# Redeploy backend and frontend
```

### 3. Clean Up Storage (Optional)

The Supabase bucket can remain - it won't cause issues. To remove it:

1. Go to Supabase dashboard → Storage
2. Select `critique-files` bucket
3. Click "Delete bucket"

## Monitoring

After deployment, monitor:

### Backend Logs

Check for storage-related errors:

```bash
# Look for SupabaseStorageError messages
tail -f /var/log/marketing-campaign-ai/backend.log | grep -i storage
```

### Storage Usage

Monitor in Supabase dashboard:
- Dashboard → Settings → Usage
- Check storage size and bandwidth
- Set up usage alerts if needed

### Performance

Watch for:
- Slow upload times (videos > 50MB)
- High bandwidth usage
- Storage quota warnings

## Troubleshooting

### "Bucket not found" Error

**Cause**: The `critique-files` bucket doesn't exist

**Fix**:
```bash
# Verify bucket exists in Supabase dashboard
# If not, create it following Step 1
```

### Videos Not Appearing

**Cause**: Bucket is not public

**Fix**:
1. Go to Storage → `critique-files`
2. Click bucket settings
3. Ensure "Public bucket" is toggled ON

### Upload Failures

**Cause**: Insufficient storage quota or permissions

**Fix**:
1. Check Supabase storage quota
2. Verify service role key has storage.objects.create permission
3. Check file size is under 100MB

### CORS Errors

**Cause**: Frontend can't access Supabase storage

**Fix**:
1. Supabase dashboard → Settings → API
2. Add your frontend domain to allowed origins
3. Ensure bucket is public

## Getting Help

If you encounter issues:

1. Check backend logs for detailed error messages
2. Verify Supabase dashboard for bucket/file status
3. Test with curl to isolate frontend vs backend issues:

```bash
# Test file upload
curl -X POST http://your-api/api/critique/upload \
  -F "file=@test-video.mp4" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check response includes file_url
```

4. Review the documentation:
   - `docs/SUPABASE_STORAGE_SETUP.md`
   - `docs/VIDEO_PLAYBACK_FEATURE.md`

5. Open an issue with:
   - Error messages from logs
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)

## Success Checklist

✅ Supabase `critique-files` bucket created and set to public
✅ Database migration applied successfully
✅ Backend deployed with new code
✅ Frontend deployed with new code
✅ Test video upload works
✅ Video playback works
✅ Saved critiques load videos correctly
✅ File deletion removes from storage
✅ No errors in backend logs
✅ Storage monitoring configured

Once all items are checked, the migration is complete! 🎉
