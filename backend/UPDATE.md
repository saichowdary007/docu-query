# DocuQuery-AI Backend Update Instructions

## Overview of Changes

This update includes the following improvements:

1. **User File Isolation**: Files are now stored in user-specific directories and associated with the uploading user in the database.
2. **User Registration Fix**: Fixed issues with user account creation and storage.
3. **Database Schema Updates**: Added a new `files` table to track file ownership and metadata.
4. **Migration Scripts**: Added scripts to migrate existing files to the new structure.
5. **Improved Setup**: New setup and run scripts for easier deployment.

## Update Steps

### 1. Backup Your Data

Before updating, back up your database and uploaded files:

```bash
# Backup the SQLite database (if using SQLite)
cp backend/app.db backend/app.db.backup

# Backup the uploaded files
cp -r backend/temp_uploads backend/temp_uploads.backup

# Backup the vector store data
cp -r backend/vector_db_data backend/vector_db_data.backup
```

### 2. Update the Code

Pull the latest code or apply the patches:

```bash
git pull
# or apply patches manually
```

### 3. Install Dependencies

Make sure all dependencies are installed:

```bash
cd backend
pip install -r requirements.txt
```

### 4. Run Setup Script

The setup script will:
- Initialize the database with the new schema
- Create a default admin user if none exists
- Set up the file system directories
- Migrate existing files to the new structure

```bash
cd backend
python scripts/setup.py
```

### 5. Start the Updated Server

Start the server using the new run script:

```bash
cd backend
python run.py
```

## Important Notes

1. **First Login**: If this is a new installation, the default admin account is created with:
   - Email: admin@docuquery.ai (Override with ADMIN_EMAIL env var)
   - Password: admin123 (Override with ADMIN_PASSWORD env var)
   - **IMPORTANT**: Change this password immediately after first login.

2. **File Ownership**: Existing files will be assigned to the first admin user found in the system.

3. **Environment Variables**: Review the `.env` file for any new configuration options.

4. **Troubleshooting**: If you encounter issues after updating:
   - Check the logs for specific error messages
   - Try running setup.py again with the `--force` flag
   - Revert to backup if necessary

## API Changes

1. All file endpoints now require user authentication
2. File uploads are automatically associated with the current user
3. File listings only show files belonging to the current user

## For Developers

If you're modifying the code:

1. New model: `File` in `app/models/db_models.py`
2. New service: `file_service.py` for file operations
3. Modified routers: `files.py` now includes user authentication and file ownership checks
4. Modified storage: Files are now stored in user-specific directories 