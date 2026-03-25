# Google Drive Setup

**Without this configured, invoices save locally to `generated_files/` — fine for the hackathon.**

## 1. Create Service Account (5 min)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (or use existing)
3. Enable **Google Drive API**: APIs & Services → Enable APIs → search "Drive"
4. IAM & Admin → Service Accounts → Create Service Account
5. Name it anything, click Done
6. Click the service account → Keys → Add Key → JSON → download
7. Save as `credentials/gdrive_service_account.json` (never commit this file)

## 2. Create Shared Folder (2 min)

1. In Google Drive, create a folder (e.g. "RE Invoices")
2. Right-click → Share → paste the **service account email** (from the JSON file, `client_email` field) → Editor
3. Copy the folder ID from the URL: `drive.google.com/drive/folders/**THIS_IS_THE_ID**`

## 3. Set env vars

```env
GDRIVE_CREDENTIALS_PATH=credentials/gdrive_service_account.json
GDRIVE_FOLDER_ID=your_folder_id_here
```

## Test it

```bash
python -c "
import asyncio
from gdrive.uploader import upload_to_drive
link = asyncio.run(upload_to_drive(b'%PDF test', 'test.pdf'))
print(link)
"
```
