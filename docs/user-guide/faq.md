# Frequently Asked Questions (FAQ)

## General Questions

### What is the Reverse Engineer Coach?

The Reverse Engineer Coach is an AI-powered learning platform that helps developers understand complex codebases by providing personalized learning experiences. Instead of manually searching for repositories to learn from, you simply describe what you want to learn, and the platform finds the best open-source repositories and creates a custom curriculum for you.

### How is this different from other learning platforms?

**Unique Features:**
- **AI-Powered Repository Discovery**: Automatically finds the best repositories for your learning goals
- **Personalized Curricula**: Creates custom learning paths based on real-world code
- **Interactive Code Analysis**: Get AI explanations for any code you're exploring
- **Real Repository Learning**: Learn from actual production codebases, not toy examples

### Is the platform free to use?

The platform itself is free, but you need to provide your own API credentials:
- **GitHub Personal Access Token**: Free from GitHub
- **AI Service API Key**: You pay for your own AI API usage (OpenAI, Anthropic, etc.)

This approach ensures you have full control over your API usage and costs.

### What programming languages are supported?

The platform supports any programming language available on GitHub, including:
- **Web Development**: JavaScript, TypeScript, React, Vue, Angular
- **Backend**: Python, Java, C#, Go, Rust, PHP
- **Mobile**: Swift, Kotlin, React Native, Flutter
- **Data Science**: Python, R, Julia
- **DevOps**: Docker, Kubernetes, Terraform
- **And many more!**

## Account and Setup

### Do I need a GitHub account?

Yes, you need a GitHub account to create a Personal Access Token. This token allows the platform to:
- Access public repositories for analysis
- Fetch code files and documentation
- Respect GitHub's rate limits under your account

### What API credentials do I need?

You need two types of credentials:

1. **GitHub Personal Access Token**
   - Required scopes: `public_repo`, `read:user`
   - Used for repository access and analysis
   - Free from GitHub

2. **AI Service API Key**
   - OpenAI (most common), Anthropic, or other supported providers
   - Used for AI-powered coaching and explanations
   - You pay for your own usage

### How much do API calls cost?

**GitHub API**: Free (with rate limits)
- 5,000 requests per hour with authentication
- Sufficient for normal platform usage

**AI API Costs** (example with OpenAI):
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- GPT-4: ~$0.03 per 1K tokens
- Typical learning session: $0.10-$0.50
- Monthly usage: $5-$20 for active learners

### Can I use the platform without AI features?

Currently, the AI coach is integral to the learning experience. However, you can:
- Use cheaper AI models (GPT-3.5 instead of GPT-4)
- Set usage limits in your AI provider dashboard
- Ask fewer questions to reduce costs

### How secure are my API credentials?

Your credentials are protected with enterprise-grade security:
- **AES-256 encryption** for all stored credentials
- **User-specific encryption keys** - each user has unique keys
- **No plain text storage** - credentials are never stored in readable form
- **Secure transmission** - all data sent over HTTPS/TLS
- **No credential sharing** - your keys are never used for other users

## Using the Platform

### How do I start learning something new?

1. **Log into your dashboard**
2. **Click "Start New Project"**
3. **Describe what you want to learn** (e.g., "React hooks and context")
4. **Review suggested repositories** with quality scores
5. **Select a repository** that matches your goals
6. **Begin your personalized learning journey**

### What makes a good learning concept?

**Good Examples:**
- "React hooks and state management"
- "Microservices architecture with Docker"
- "GraphQL API design patterns"
- "Machine learning model deployment"

**Less Effective:**
- "Programming" (too broad)
- "JavaScript" (too general)
- "Web development" (lacks focus)

**Tips:**
- Be specific about technologies
- Include architectural patterns or concepts
- Mention your experience level if relevant

### How does repository discovery work?

The platform uses a multi-step process:

1. **GitHub Search**: Searches thousands of repositories using your concept
2. **Quality Analysis**: Evaluates code quality, documentation, and structure
3. **Educational Assessment**: AI analyzes learning potential and complexity
4. **Ranking Algorithm**: Combines quality, relevance, and educational value
5. **Top Suggestions**: Presents 3-5 best repositories with scores

### What if I don't like the suggested repositories?

You have several options:
- **Refine your concept**: Try more specific or alternative terms
- **Manual entry**: Enter a specific repository URL you want to learn from
- **Try different search**: Use related concepts or technologies
- **Browse suggestions**: Sometimes the 4th or 5th suggestion is perfect

### How long does it take to complete a learning project?

This varies greatly depending on:
- **Repository complexity**: Simple projects (2-5 hours), complex systems (20+ hours)
- **Your experience level**: Beginners need more time than experts
- **Learning depth**: Surface understanding vs. deep mastery
- **Available time**: Daily learning vs. weekend sessions

**Typical Timeframes:**
- **Small libraries**: 2-4 hours
- **Medium applications**: 8-15 hours
- **Large systems**: 20-40 hours
- **Complex architectures**: 40+ hours

### Can I learn multiple things at once?

Yes! You can have multiple active projects:
- **Switch between projects** as your interests change
- **Compare approaches** across different repositories
- **Build on previous knowledge** from completed projects
- **Organize projects** by technology or domain

## AI Coach and Learning

### How smart is the AI coach?

The AI coach uses state-of-the-art language models (GPT-4, Claude, etc.) and is specifically trained to:
- **Understand code architecture** and design patterns
- **Explain complex concepts** in simple terms
- **Provide contextual help** based on the specific repository
- **Adapt explanations** to your experience level

### What kinds of questions can I ask the AI coach?

**Great Questions:**
- "How does this authentication system work?"
- "Why did they choose this architectural pattern?"
- "What would happen if I changed this approach?"
- "Can you explain this algorithm step by step?"
- "What are the trade-offs of this design decision?"

**Less Effective:**
- "What is programming?" (too general)
- "Fix my code" (coach analyzes, doesn't write code)
- "What's the best framework?" (subjective, context-dependent)

### Does the AI coach write code for me?

No, the AI coach is designed for learning, not coding:
- **Explains existing code** in the repository
- **Analyzes architectural decisions** and patterns
- **Provides learning guidance** and next steps
- **Answers questions** about implementation details

The goal is to help you understand code, not to write it for you.

### Can I save my conversations with the AI coach?

Currently, conversations are session-based, but you can:
- **Take notes** in the built-in notes feature
- **Export your learning data** including insights and discoveries
- **Bookmark important explanations** for future reference
- **Copy useful explanations** to your personal notes

## Technical Issues

### The platform is running slowly. What can I do?

**Common Solutions:**
- **Close other browser tabs** to free memory
- **Choose smaller repositories** for faster analysis
- **Check your internet connection** speed
- **Try during off-peak hours** for better performance
- **Clear browser cache** and refresh

### My GitHub token isn't working. What's wrong?

**Check These Items:**
- **Token format**: Should start with `ghp_`
- **Required scopes**: Must include `public_repo` and `read:user`
- **Expiration date**: Token might have expired
- **Copy/paste errors**: Ensure no extra spaces or characters

**Solution**: Generate a new token with proper scopes.

### I'm getting "API quota exceeded" errors. What now?

**For GitHub API:**
- **Wait for reset**: Limits reset every hour
- **Check usage**: You get 5,000 requests/hour with authentication
- **Upgrade GitHub plan**: For higher limits

**For AI API:**
- **Check your billing dashboard** in your AI provider account
- **Add payment method** or increase limits
- **Use cheaper models** (GPT-3.5 instead of GPT-4)
- **Ask fewer questions** to reduce usage

### Repository analysis failed. Why?

**Common Causes:**
- **Repository too large**: Try repositories under 50MB
- **Unusual structure**: Some repos don't follow standard patterns
- **Access issues**: Repository might be private or deleted
- **Network problems**: Temporary connectivity issues

**Solutions**: Try a different repository or check the specific error message.

## Learning and Progress

### How do I track my learning progress?

The platform provides several progress indicators:
- **Task completion**: Check off learning objectives as you complete them
- **Time tracking**: See how much time you've spent on each project
- **Skill development**: Track technologies and concepts you've learned
- **Project history**: Review all completed and active projects

### Can I export my learning data?

Yes, you can export:
- **Project summaries**: Overview of all your learning projects
- **Learning notes**: Your personal insights and discoveries
- **Progress data**: Completion rates and time invested
- **Achievement records**: Technologies mastered and milestones reached

### What happens to my data if I delete my account?

**Data Deletion:**
- **Personal information**: Completely removed from our systems
- **API credentials**: Securely deleted and unrecoverable
- **Learning projects**: Removed from your account

**Anonymized Analytics:**
- **Usage patterns**: May be retained for platform improvement (no personal identifiers)
- **Repository quality data**: Helps improve discovery for other users

### Can I share my learning projects with others?

Currently, projects are private to your account. However, you can:
- **Export project summaries** to share your learning journey
- **Recommend repositories** you found valuable
- **Share insights** from your learning notes
- **Discuss concepts** you've learned with others

## Billing and Costs

### Does the platform charge any fees?

No, the platform itself is completely free. You only pay for:
- **Your own AI API usage** (OpenAI, Anthropic, etc.)
- **GitHub API is free** (with generous rate limits)

### How can I control my AI API costs?

**Cost Control Strategies:**
- **Set usage limits** in your AI provider dashboard
- **Use cheaper models** when possible (GPT-3.5 vs GPT-4)
- **Ask focused questions** instead of broad ones
- **Monitor usage regularly** through your AI provider's dashboard
- **Set up billing alerts** to notify you of high usage

### What if I run out of AI API credits?

**Options:**
- **Add more credits** to your AI provider account
- **Wait for monthly quota reset** (free tier users)
- **Switch to a different AI provider** if supported
- **Continue learning** with limited AI assistance until credits are restored

## Privacy and Security

### What data do you collect?

**We collect:**
- **Account information**: Email, encrypted password
- **Learning data**: Projects, progress, notes (associated with your account)
- **Usage analytics**: How you use the platform (anonymized)
- **API credentials**: Encrypted and stored securely

**We don't collect:**
- **Personal conversations**: AI chat logs are not permanently stored
- **Browsing history**: Outside of the platform
- **Financial information**: You pay AI providers directly

### How do you protect my privacy?

**Privacy Measures:**
- **Data encryption**: All sensitive data encrypted at rest and in transit
- **Minimal data collection**: Only collect what's necessary for functionality
- **No data selling**: We never sell or share your personal data
- **User control**: You can export or delete your data at any time

### Can I use the platform anonymously?

You need an email address for account creation, but:
- **Use any email**: Personal, work, or dedicated learning email
- **No real name required**: Use any display name you prefer
- **No phone verification**: Email is sufficient for account creation
- **No social media linking**: No requirement to connect other accounts

## Future Features

### Will you add more AI providers?

Yes, we're working on supporting additional AI providers:
- **Anthropic Claude**: Already supported
- **Google Gemini**: In development
- **Azure OpenAI**: Planned
- **Local models**: Considering support for self-hosted models

### Are you planning mobile apps?

Currently, the platform is web-based and works on mobile browsers. Native mobile apps are being considered based on user demand.

### Will you add collaborative features?

We're exploring features like:
- **Shared learning projects**: Collaborate with teammates
- **Learning groups**: Join others learning similar concepts
- **Mentorship features**: Connect with experienced developers
- **Community discussions**: Share insights and ask questions

### Can I suggest new features?

Absolutely! We welcome feature suggestions:
- **Feedback form**: Available in the platform
- **User research**: Participate in user experience studies
- **Beta testing**: Try new features before general release
- **Community forums**: Discuss ideas with other users

## Getting Help

### I can't find the answer to my question. What now?

**Next Steps:**
1. **Check the troubleshooting guide** for technical issues
2. **Search the documentation** for detailed information
3. **Contact support** with your specific question
4. **Join community forums** to ask other users

### How do I contact support?

**Support Channels:**
- **Help form**: Available in the platform settings
- **Email support**: Include error messages and steps to reproduce issues
- **Documentation**: Comprehensive guides for most topics
- **Community forums**: Get help from other users

### What information should I include when asking for help?

**Helpful Information:**
- **Specific error messages**: Exact text or screenshots
- **Steps to reproduce**: What you were doing when the issue occurred
- **Browser and version**: Chrome 91, Firefox 89, etc.
- **Account email**: For account-specific issues (never share passwords)
- **Repository details**: If the issue is related to a specific repository

---

Still have questions? Check our [Troubleshooting Guide](troubleshooting.md) or [contact support](mailto:support@example.com) for personalized help! 🤝