# API Credentials Setup Guide

This guide explains how to obtain and configure the API credentials needed for the Reverse Engineer Coach platform.

## Overview

The platform requires two types of API credentials:

1. **GitHub Personal Access Token** - For accessing and analyzing repositories
2. **AI Service API Key** - For AI-powered coaching and explanations (OpenAI, Anthropic, etc.)

Both credentials are encrypted and stored securely in your account.

## GitHub Personal Access Token

### Why Do You Need This?

Your GitHub token allows the platform to:
- Access public repositories for analysis
- Fetch repository metadata and structure
- Download code files for AI analysis
- Respect GitHub's rate limits under your account

### Creating a GitHub Token

1. **Sign in to GitHub**
   - Go to [github.com](https://github.com) and sign in to your account

2. **Access Developer Settings**
   - Click your profile picture (top right)
   - Select "Settings"
   - Scroll down and click "Developer settings" (left sidebar)
   - Click "Personal access tokens" → "Tokens (classic)"

3. **Generate New Token**
   - Click "Generate new token" → "Generate new token (classic)"
   - Add a descriptive note: "Reverse Engineer Coach Platform"
   - Set expiration (recommended: 90 days for security)

4. **Select Required Scopes**
   
   **Minimum Required Permissions:**
   - ✅ `public_repo` - Access public repositories
   - ✅ `read:user` - Read user profile information
   
   **Optional but Recommended:**
   - ✅ `repo:status` - Access commit status
   - ✅ `read:org` - Read organization membership (for org repos)

5. **Generate and Copy Token**
   - Click "Generate token"
   - **Important**: Copy the token immediately - you won't see it again!
   - Store it securely (password manager recommended)

### Token Format
GitHub tokens look like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Security Best Practices

- **Never share your token** with anyone
- **Use expiration dates** - tokens should expire regularly
- **Regenerate periodically** - create new tokens every 90 days
- **Revoke unused tokens** - clean up old tokens in GitHub settings
- **Use minimal permissions** - only grant necessary scopes

## AI Service API Key

### Supported AI Services

The platform supports several AI providers:

1. **OpenAI** (GPT-3.5, GPT-4)
2. **Anthropic** (Claude)
3. **Google AI** (Gemini)
4. **Azure OpenAI**

### OpenAI API Key (Most Common)

1. **Create OpenAI Account**
   - Visit [platform.openai.com](https://platform.openai.com)
   - Sign up or sign in to your account

2. **Access API Keys**
   - Click your profile (top right)
   - Select "View API keys"
   - Or go directly to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

3. **Create New Key**
   - Click "Create new secret key"
   - Add a name: "Reverse Engineer Coach"
   - Set permissions (if available): "All" or "Read/Write"
   - Click "Create secret key"

4. **Copy and Store Key**
   - Copy the key immediately (starts with `sk-`)
   - Store securely - you won't see it again

### API Key Format
OpenAI keys look like: `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Usage and Billing

- **Free Tier**: OpenAI provides free credits for new accounts
- **Pay-per-use**: You're charged based on API usage
- **Set Limits**: Configure usage limits in your OpenAI dashboard
- **Monitor Usage**: Check your usage regularly to avoid unexpected charges

## Adding Credentials to Your Account

### During Registration

1. **Registration Form**
   - Enter your GitHub token in the "GitHub Token" field
   - Enter your AI API key in the "AI API Key" field
   - The system will validate both credentials before creating your account

2. **Validation Process**
   - GitHub token: Tests access to public repositories
   - AI API key: Makes a test API call
   - Both must pass validation to complete registration

### After Registration

1. **Access Profile Settings**
   - Go to your dashboard
   - Click your profile menu (top right)
   - Select "Profile Settings" or "Account Settings"

2. **Update Credentials**
   - Navigate to "API Credentials" section
   - Current credentials are shown masked (e.g., `ghp_****...****1234`)
   - Click "Update" next to the credential you want to change

3. **Enter New Credentials**
   - Paste your new token/key
   - Click "Validate and Save"
   - The system will test the new credential before saving

## Credential Security

### How We Protect Your Credentials

- **AES-256 Encryption**: All credentials are encrypted using industry-standard encryption
- **User-Specific Keys**: Each user has unique encryption keys
- **No Plain Text Storage**: Credentials are never stored in readable form
- **Secure Transmission**: All data is transmitted over HTTPS/TLS

### What We Don't Do

- **Never log credentials**: API keys are never written to log files
- **No credential sharing**: Your keys are never used for other users
- **No external transmission**: Credentials only leave our servers to call the respective APIs
- **No backup in plain text**: Even backups maintain encryption

## Troubleshooting Credentials

### GitHub Token Issues

**Error: "Invalid GitHub token"**
- Verify the token is copied correctly (no extra spaces)
- Check token hasn't expired
- Ensure required scopes are selected
- Try regenerating the token

**Error: "GitHub API rate limit exceeded"**
- Your token has hit GitHub's rate limits
- Wait for the limit to reset (usually 1 hour)
- Consider upgrading to GitHub Pro for higher limits

**Error: "Token lacks required permissions"**
- Regenerate token with `public_repo` scope
- Ensure `read:user` permission is granted

### AI API Key Issues

**Error: "Invalid AI API key"**
- Verify the key is copied correctly
- Check if the key has been revoked or expired
- Ensure you have available credits/quota
- Try creating a new API key

**Error: "AI API quota exceeded"**
- You've reached your usage limits
- Check your billing dashboard
- Add payment method or increase limits
- Wait for quota to reset (if on free tier)

**Error: "AI service unavailable"**
- The AI service may be experiencing downtime
- Try again in a few minutes
- Check the service status page

### General Validation Issues

**Error: "Network connection failed"**
- Check your internet connection
- Verify firewall isn't blocking API calls
- Try again in a few moments

**Error: "Credential validation timeout"**
- API services may be slow to respond
- Try validation again
- Check service status pages

## Updating Expired Credentials

### When Credentials Expire

You'll be notified when credentials need updating:
- Email notifications before expiration
- Dashboard warnings for expired credentials
- Error messages when API calls fail

### Quick Update Process

1. **Generate New Credentials**
   - Create new GitHub token (same process as above)
   - Generate new AI API key if needed

2. **Update in Platform**
   - Go to Profile Settings → API Credentials
   - Click "Update" for expired credential
   - Enter new credential and validate

3. **Verify Functionality**
   - Test by starting a new learning project
   - Ensure repository discovery works
   - Confirm AI coach responses

## Best Practices Summary

### Security
- ✅ Use strong, unique passwords for all accounts
- ✅ Enable 2FA on GitHub and AI service accounts
- ✅ Set expiration dates on tokens
- ✅ Regularly rotate credentials
- ✅ Monitor usage and billing

### Management
- ✅ Keep credentials in a password manager
- ✅ Set calendar reminders for renewal
- ✅ Monitor API usage and costs
- ✅ Revoke unused or old tokens
- ✅ Use descriptive names for tokens

### Troubleshooting
- ✅ Test credentials after creation
- ✅ Keep backup tokens ready
- ✅ Monitor service status pages
- ✅ Check billing and quota limits
- ✅ Contact support with specific error messages

## Need Help?

If you're still having trouble with API credentials:

1. **Check Error Messages**: Look for specific error details
2. **Verify Credentials**: Test tokens directly with the APIs
3. **Review Permissions**: Ensure all required scopes are granted
4. **Check Service Status**: Verify APIs are operational
5. **Contact Support**: Include error messages and steps you've tried

Remember: Your API credentials are the key to your personalized learning experience. Keep them secure and up to date! 🔐