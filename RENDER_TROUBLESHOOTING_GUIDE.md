# 🔧 Render Deployment Troubleshooting Guide

## ❌ Deploy Failed: "Exited with status 1"

**Error Message**: `Deploy failed for 50f7eb0: Add deployment helper scripts for Render and frontend connection. Exited with status 1 while running your code.`

This error means the application started but crashed immediately. Let's fix it step by step.

## 🔍 Step 1: Check Deploy Logs

**In your Render dashboard:**

1. **Click on your web service** (`reverse-coach-backend`)
2. **Go to "Logs" tab** (left sidebar)
3. **Look for the error details** in the deploy logs

**Common error patterns to look for:**

### A) Missing Environment Variables
```
KeyError: 'DATABASE_URL'
Environment variable DATABASE_URL not found
```
**Fix**: Add missing environment variables

### B) Database Connection Issues
```
could not connect to server: Connection refused
FATAL: database "reverse_coach" does not exist
```
**Fix**: Create PostgreSQL database and add DATABASE_URL

### C) Import/Module Errors
```
ModuleNotFoundError: No module named 'xyz'
ImportError: cannot import name 'xyz'
```
**Fix**: Check requirements.txt and Python dependencies

### D) Port Binding Issues
```
OSError: [Errno 98] Address already in use
```
**Fix**: Ensure start command uses $PORT variable

## 🛠️ Step 2: Most Common Fixes

### Fix 1: Missing DATABASE_URL (Most Likely)

**Problem**: Backend expects a database but DATABASE_URL is not set.

**Solution**:
1. **Create PostgreSQL database** (if not done):
   - Click "New +" → "PostgreSQL"
   - Name: `reverse-coach-db`
   - Database: `reverse_coach`

2. **Add DATABASE_URL to web service**:
   - Go to your web service → "Environment" tab
   - Add: `DATABASE_URL=postgresql://user:pass@host:5432/reverse_coach`
   - Use the connection string from your PostgreSQL database

### Fix 2: Missing Required Environment Variables

**Check these are all set in Environment tab:**

```
JWT_SECRET_KEY=CcppaPCzljV3Bnnj0rClCWXV7l2rwgk+DlT/1JFkNqY=
JWT_REFRESH_SECRET_KEY=w2nL8028iY1mRtT9ngpRrS2oXCScKSY3QzHlFcDxUns=
ENCRYPTION_KEY=bCpWb7BNI8gOKCvhCMCvGJGLQjJN1KcBCZrPrXJeKY8=
MASTER_ENCRYPTION_KEY=zcxi5EPfB4kM5n7Hkd0Mn9kfKIcoZPph1vQEB2Cutwc=
CORS_ORIGINS=https://reveng.netlify.app
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=[your database connection string]
```

### Fix 3: Incorrect Build/Start Commands

**Check your service settings:**

```
Build Command: cd backend && pip install -r requirements.txt
Start Command: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Important**: Both commands MUST include `cd backend &&`

## 🔧 Step 3: Quick Diagnostic Commands

### Test 1: Check if requirements.txt exists
**In Render logs, look for:**
```
✅ GOOD: "Successfully installed fastapi uvicorn..."
❌ BAD: "Could not open requirements file"
```

### Test 2: Check if app starts locally
**Run locally to test:**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test 3: Check environment variables
**In Render service → Environment tab:**
- Should show 8 environment variables
- DATABASE_URL should be present (value hidden)

## 🚀 Step 4: Force Redeploy

**After making fixes:**

1. **Go to your web service**
2. **Click "Manual Deploy"** (top right)
3. **Select "Deploy latest commit"**
4. **Wait for new deployment**

## 📋 Step 5: Deployment Checklist

**Before deploying, verify:**

- [ ] PostgreSQL database created (`reverse-coach-db`)
- [ ] DATABASE_URL added to web service environment variables
- [ ] All 8 environment variables are set
- [ ] Build command includes `cd backend &&`
- [ ] Start command includes `cd backend &&` and `$PORT`
- [ ] Repository is public (required for free tier)
- [ ] `backend/requirements.txt` exists in your repository

## 🔍 Step 6: Read the Exact Error

**To get the specific error:**

1. **Go to Logs tab** in your web service
2. **Scroll to the bottom** of the deploy logs
3. **Look for the last error message** before "Exited with status 1"
4. **Copy the exact error** and we can fix it specifically

## 🆘 Common Error Solutions

### Error: "No module named 'app'"
**Fix**: Ensure start command is:
```
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Error: "Database connection failed"
**Fix**: 
1. Create PostgreSQL database in Render
2. Add DATABASE_URL environment variable
3. Ensure database and web service are in same region

### Error: "Port already in use"
**Fix**: Ensure start command uses `$PORT` variable:
```
--port $PORT
```

### Error: "CORS origin not allowed"
**Fix**: Set CORS_ORIGINS environment variable:
```
CORS_ORIGINS=https://reveng.netlify.app
```

## 📞 Next Steps

1. **Check your deploy logs** for the specific error
2. **Apply the appropriate fix** from above
3. **Redeploy** using "Manual Deploy"
4. **Monitor the logs** during deployment

**If you share the specific error from the logs, I can provide an exact fix!**

## 🎯 Expected Success

**When deployment works, you'll see:**
```
=== Deploy Logs ===
✅ Build completed successfully
✅ Starting application...
✅ Server running on port $PORT
✅ Health check passed
✅ Deploy live at: https://reverse-coach-backend.onrender.com
```

**Test URL**: Visit `https://reverse-coach-backend.onrender.com/health`
**Should return**: `{"status": "healthy", ...}`

---

**Most likely fix**: Create PostgreSQL database and add DATABASE_URL environment variable! 🎯