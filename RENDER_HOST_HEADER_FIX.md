# 🔧 Fix: Invalid Host Header Error

## ❌ Problem
When visiting `https://reverse-coach-backend.onrender.com`, you see:
```
Invalid Host Header
```

## ✅ Solution
The FastAPI `TrustedHostMiddleware` is blocking the Render domain. You need to add the `ALLOWED_HOSTS` environment variable.

## 🚀 Quick Fix Steps

### Step 1: Add ALLOWED_HOSTS Environment Variable
1. **Go to your Render web service** → Environment tab
2. **Click "Add Environment Variable"**
3. **Key**: `ALLOWED_HOSTS`
4. **Value**: `reverse-coach-backend.onrender.com,localhost,127.0.0.1,0.0.0.0`
5. **Click "Save"**

### Step 2: Redeploy
1. **Click "Manual Deploy"** → "Deploy latest commit"
2. **Wait 2-3 minutes** for deployment

### Step 3: Test
- **Visit**: `https://reverse-coach-backend.onrender.com`
- **Should show**: `{"message": "Reverse Engineer Coach API", "version": "1.0.0", "status": "running"}`
- **Health check**: `https://reverse-coach-backend.onrender.com/health`

## 📋 Complete Environment Variables List

**Make sure ALL these are set in your Render web service:**

```
JWT_SECRET_KEY=CcppaPCzljV3Bnnj0rClCWXV7l2rwgk+DlT/1JFkNqY=
JWT_REFRESH_SECRET_KEY=w2nL8028iY1mRtT9ngpRrS2oXCScKSY3QzHlFcDxUns=
ENCRYPTION_KEY=bCpWb7BNI8gOKCvhCMCvGJGLQjJN1KcBCZrPrXJeKY8=
MASTER_ENCRYPTION_KEY=zcxi5EPfB4kM5n7Hkd0Mn9kfKIcoZPph1vQEB2Cutwc=
CREDENTIAL_ENCRYPTION_KEY=vyFqRAZpB8pnBXdUc0kwFiCYnaJeY29ZxHfI9DEbYCo=
CORS_ORIGINS=https://reveng.netlify.app
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=reverse-coach-backend.onrender.com,localhost,127.0.0.1,0.0.0.0
DATABASE_URL=[Connected via datastore]
```

## 🎯 Why This Happens

FastAPI's `TrustedHostMiddleware` is a security feature that prevents **Host Header Injection** attacks. It only allows requests from trusted domains.

**In main.py:**
```python
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
```

**Without the environment variable**, it defaults to only local hosts, blocking Render's domain.

## ✅ Expected Result

**After the fix:**
- ✅ `https://reverse-coach-backend.onrender.com` → Shows API info
- ✅ `https://reverse-coach-backend.onrender.com/health` → Shows health status
- ✅ Frontend at `https://reveng.netlify.app` can connect to backend
- ✅ No CORS errors in browser console

---

**This is the final step to get your backend working! 🎉**