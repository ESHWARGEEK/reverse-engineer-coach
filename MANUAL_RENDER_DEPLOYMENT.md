# 🚀 Manual Backend Deployment to Render

## ✅ Frontend Already Deployed!
Your frontend is live at: **https://reveng.netlify.app**

## 🎯 Now Deploy Backend to Render (FREE)

### Step 1: Push Code to GitHub (if not already done)

1. **Initialize Git** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit for deployment"
   ```

2. **Create GitHub Repository**:
   - Go to [github.com](https://github.com)
   - Click "New repository"
   - Name it "reverse-engineer-coach"
   - Don't initialize with README (since you have code)

3. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/reverse-engineer-coach.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy Backend to Render

1. **Go to [render.com](https://render.com)**

2. **Sign up/Login** with your GitHub account

3. **Create a Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select "reverse-engineer-coach"

4. **Configure the Service**:
   ```
   Name: reverse-coach-backend
   Environment: Python 3
   Build Command: cd backend && pip install -r requirements.txt
   Start Command: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

5. **Add Environment Variables**:
   Click "Environment" and add:
   ```
   DATABASE_URL=postgresql://user:pass@hostname:5432/dbname
   CORS_ORIGINS=https://reveng.netlify.app
   JWT_SECRET_KEY=your-secure-jwt-secret-32-chars-minimum
   JWT_REFRESH_SECRET_KEY=your-secure-refresh-secret-32-chars
   ENCRYPTION_KEY=your-encryption-key-32-bytes-base64
   MASTER_ENCRYPTION_KEY=your-master-key-32-bytes-base64
   ```

6. **Create PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - Name it "reverse-coach-db"
   - Copy the connection string
   - Update `DATABASE_URL` in your web service

7. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

### Step 3: Connect Frontend to Backend

1. **Get Backend URL**:
   - Your backend will be at: `https://reverse-coach-backend.onrender.com`

2. **Update Frontend Environment**:
   - Go to [Netlify Dashboard](https://app.netlify.com)
   - Click on your "RevEng" site
   - Go to Site settings → Environment variables
   - Add: `REACT_APP_API_URL=https://reverse-coach-backend.onrender.com`

3. **Redeploy Frontend**:
   ```bash
   cd frontend
   netlify deploy --prod
   ```

### Step 4: Generate Secure Keys

Use these commands to generate secure keys:

```bash
# Generate secure random keys
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('MASTER_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

### Step 5: Test Your Deployment

1. **Frontend**: https://reveng.netlify.app
2. **Backend API**: https://reverse-coach-backend.onrender.com/docs
3. **Health Check**: https://reverse-coach-backend.onrender.com/health

## 🎉 Success!

Once completed, you'll have:
- ✅ Frontend on Netlify (FREE)
- ✅ Backend on Render (FREE)
- ✅ PostgreSQL Database (FREE)
- ✅ SSL Certificates (FREE)
- ✅ Custom domains supported

**Total Cost**: $0/month

## 🔧 Troubleshooting

### Common Issues:

1. **Build Fails**: Check that `requirements.txt` is in the backend folder
2. **Database Connection**: Verify `DATABASE_URL` is correct
3. **CORS Errors**: Ensure `CORS_ORIGINS` includes your Netlify URL
4. **Environment Variables**: Make sure all required variables are set

### Getting Help:

- Check Render build logs for errors
- Test backend locally first: `cd backend && uvicorn app.main:app --reload`
- Verify frontend builds: `cd frontend && npm run build`

## 📞 Next Steps

After successful deployment:
1. Test the application end-to-end
2. Add your API keys (GitHub, OpenAI, etc.)
3. Customize branding and content
4. Share your live application!

---

**Your Live Application URLs:**
- Frontend: https://reveng.netlify.app
- Backend: https://reverse-coach-backend.onrender.com (after Render deployment)