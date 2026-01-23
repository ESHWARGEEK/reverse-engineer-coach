# 🚀 Deploy to Internet - Step by Step Guide

This guide will help you deploy the Reverse Engineer Coach application to the internet **for free** using the best available platforms.

## 🎯 Quick Summary

**Best Free Options:**
1. **Frontend**: Netlify (Free forever)
2. **Backend**: Railway (Free tier) or Render (Free tier)
3. **Database**: Included with backend platforms

**Total Cost**: $0/month with free tiers

## 📋 Prerequisites

Before starting, make sure you have:
- ✅ GitHub account
- ✅ Application running locally (see [LOCAL_SETUP_GUIDE.md](LOCAL_SETUP_GUIDE.md))
- ✅ Code pushed to GitHub repository

## 🌟 Method 1: Netlify + Railway (Recommended FREE option)

### Step 1: Deploy Frontend to Netlify (FREE)

1. **Install Netlify CLI**
   ```powershell
   npm install -g netlify-cli
   ```

2. **Navigate to frontend directory**
   ```powershell
   cd frontend
   ```

3. **Login to Netlify**
   ```powershell
   netlify login
   ```
   This will open your browser to authenticate.

4. **Initialize Netlify site**
   ```powershell
   netlify init
   ```
   Follow the prompts:
   - Choose "Create & configure a new site"
   - Select your team
   - Enter a site name (or leave blank for auto-generated)

5. **Deploy to production**
   ```powershell
   netlify deploy --prod
   ```

6. **Your frontend is now live!** 🎉
   - You'll get a URL like: `https://your-site-name.netlify.app`

### Step 2: Deploy Backend to Railway (FREE tier)

1. **Install Railway CLI**
   ```powershell
   npm install -g @railway/cli
   ```

2. **Navigate to project root**
   ```powershell
   cd ..
   ```

3. **Login to Railway**
   ```powershell
   railway login
   ```

4. **Initialize Railway project**
   ```powershell
   railway init
   ```

5. **Deploy backend**
   ```powershell
   railway up
   ```

6. **Add environment variables in Railway dashboard**
   - Go to [railway.app](https://railway.app)
   - Click on your project
   - Go to Variables tab
   - Add these variables:
     ```
     DATABASE_URL=postgresql://postgres:password@postgres:5432/reverse_coach
     CORS_ORIGINS=https://your-netlify-site.netlify.app
     JWT_SECRET_KEY=your-secret-key-here
     ```

7. **Your backend is now live!** 🎉
   - You'll get a URL like: `https://your-app.railway.app`

### Step 3: Connect Frontend to Backend

1. **Update Netlify environment variables**
   - Go to Netlify dashboard
   - Click on your site
   - Go to Site settings → Environment variables
   - Add:
     ```
     REACT_APP_API_URL=https://your-railway-app.railway.app
     ```

2. **Redeploy frontend**
   ```powershell
   cd frontend
   netlify deploy --prod
   ```

### 🎉 You're Done!

Your application is now live on the internet:
- **Frontend**: `https://your-site.netlify.app`
- **Backend**: `https://your-app.railway.app`
- **Total Cost**: $0/month

---

## 🌟 Method 2: Netlify + Render (Alternative FREE option)

### Step 1: Deploy Frontend to Netlify
Follow the same steps as Method 1, Step 1.

### Step 2: Deploy Backend to Render

1. **Push code to GitHub** (if not already done)
   ```powershell
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Go to [render.com](https://render.com)**

3. **Create a Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: `reverse-coach-backend`
     - **Environment**: `Python 3`
     - **Build Command**: `cd backend && pip install -r requirements.txt`
     - **Start Command**: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables**
   - In Render dashboard, go to Environment
   - Add:
     ```
     DATABASE_URL=postgresql://user:pass@hostname:5432/dbname
     CORS_ORIGINS=https://your-netlify-site.netlify.app
     JWT_SECRET_KEY=your-secret-key-here
     ```

5. **Create PostgreSQL Database**
   - Click "New +" → "PostgreSQL"
   - Note the connection details
   - Update `DATABASE_URL` in your web service

### Step 3: Connect Frontend to Backend
Same as Method 1, Step 3, but use your Render URL.

---

## 🔧 Advanced: Custom Domain (Optional)

### For Netlify (Frontend)
1. Go to Netlify dashboard → Domain settings
2. Add your custom domain
3. Follow DNS configuration instructions

### For Railway/Render (Backend)
1. Go to platform dashboard
2. Add custom domain in settings
3. Update CORS_ORIGINS to include your custom domain

---

## 🛠️ Troubleshooting

### Common Issues

**1. Build Failures**
```powershell
# Check build logs in platform dashboard
# Common fix: ensure all dependencies are in package.json
cd frontend
npm install
npm run build
```

**2. CORS Errors**
- Make sure `CORS_ORIGINS` includes your frontend URL
- Check that URLs don't have trailing slashes

**3. Database Connection Issues**
- Verify `DATABASE_URL` is correctly set
- Check that database service is running

**4. Environment Variables Not Loading**
- Redeploy after adding environment variables
- Check variable names match exactly

### Testing Your Deployment

1. **Frontend Test**
   ```
   Visit: https://your-site.netlify.app
   Should load the homepage
   ```

2. **Backend Test**
   ```
   Visit: https://your-backend-url/docs
   Should show API documentation
   ```

3. **Full Integration Test**
   - Try creating an account
   - Test repository discovery
   - Check that data persists

---

## 💰 Cost Breakdown

### Free Tier Limits

**Netlify (Frontend)**
- ✅ 100GB bandwidth/month
- ✅ 300 build minutes/month
- ✅ Custom domains
- ✅ SSL certificates
- ✅ Form handling

**Railway (Backend)**
- ✅ $5 credit/month (usually enough for small apps)
- ✅ PostgreSQL database included
- ✅ 500 hours/month execution time
- ✅ Custom domains

**Render (Backend Alternative)**
- ✅ 750 hours/month (enough for 24/7)
- ✅ PostgreSQL database included
- ✅ SSL certificates
- ⚠️ Spins down after 15 minutes of inactivity

### When You Might Need to Pay

**Railway**: After $5 credit is used (~month 2-3)
- Upgrade to $5/month plan

**Render**: For always-on service
- Upgrade to $7/month plan

**Netlify**: For advanced features
- Pro plan $19/month (usually not needed)

---

## 🔐 Security Considerations

### Environment Variables
Never commit these to GitHub:
```env
# Generate secure keys
JWT_SECRET_KEY=your-secure-jwt-secret-32-chars-min
JWT_REFRESH_SECRET_KEY=your-secure-refresh-secret
ENCRYPTION_KEY=your-encryption-key-32-bytes
MASTER_ENCRYPTION_KEY=your-master-key-32-bytes
```

### Generate Secure Keys
```powershell
# Use this to generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### API Keys (User-Specific)
Users should add their own API keys after deployment:
- GitHub Token (for repository analysis)
- OpenAI API Key (for AI features)
- Anthropic API Key (for AI features)

---

## 📊 Monitoring Your Deployment

### Built-in Monitoring

**Netlify**
- Analytics dashboard
- Build logs
- Performance metrics

**Railway**
- Resource usage
- Deployment logs
- Database metrics

**Render**
- Service metrics
- Build logs
- Database monitoring

### Custom Monitoring

Your app includes built-in health checks:
- `/health` - Overall system health
- `/api/health` - API health
- `/docs` - API documentation

---

## 🚀 Next Steps After Deployment

1. **Test Everything**
   - Create a test account
   - Try the repository discovery feature
   - Test the learning workflow

2. **Add Your API Keys**
   - GitHub token for repository access
   - AI API keys for enhanced features

3. **Customize**
   - Update branding
   - Modify content
   - Add your own repositories

4. **Share**
   - Share your deployment URL
   - Get feedback from users
   - Iterate and improve

---

## 🆘 Getting Help

### Platform Support
- **Netlify**: [docs.netlify.com](https://docs.netlify.com)
- **Railway**: [docs.railway.app](https://docs.railway.app)
- **Render**: [render.com/docs](https://render.com/docs)

### Application Issues
- Check the [LOCAL_SETUP_GUIDE.md](LOCAL_SETUP_GUIDE.md)
- Review application logs in platform dashboards
- Test locally first to isolate issues

### Community
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Platform-specific community forums

---

## 🎯 Summary

You now have a **free, production-ready** deployment of the Reverse Engineer Coach application on the internet! 

**Your URLs:**
- Frontend: `https://your-site.netlify.app`
- Backend: `https://your-backend.railway.app` or `https://your-backend.onrender.com`
- API Docs: `https://your-backend-url/docs`

**Monthly Cost**: $0 (with free tiers)

**Next Steps**: Test, customize, and share your deployment!

---

*This guide focuses on the most reliable free deployment options. For enterprise needs or custom requirements, see [INTERNET_DEPLOYMENT.md](INTERNET_DEPLOYMENT.md) for advanced options.*