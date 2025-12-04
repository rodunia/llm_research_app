# Automatic GitHub → Hugging Face Deployment Setup

## Step 1: Update Your GitHub Personal Access Token

Your current PAT doesn't have the `workflow` scope needed to push workflow files.

**Option A: Update existing token**
1. Go to https://github.com/settings/tokens
2. Find your existing Personal Access Token
3. Click **"Edit"**
4. Check the **`workflow`** scope checkbox
5. Click **"Update token"** at the bottom
6. Copy the token and update it in your git credential manager

**Option B: Create workflow via GitHub web interface (easier)**
Follow Step 2 below instead.

## Step 2: Create Workflow File on GitHub

Since we can't push the workflow file, create it directly on GitHub:

1. **Go to this URL** (creates the file automatically):
   ```
   https://github.com/rodunia/llm_research_app/new/main?filename=.github%2Fworkflows%2Fdeploy-to-hf.yml
   ```

2. **Paste this content**:
   ```yaml
   name: Deploy to Hugging Face Spaces

   on:
     push:
       branches:
         - main
     workflow_dispatch:

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - name: Checkout code
           uses: actions/checkout@v3
           with:
             fetch-depth: 0
             lfs: true

         - name: Push to Hugging Face Space
           env:
             HF_TOKEN: ${{ secrets.HF_TOKEN }}
           run: |
             git config --global user.email "github-actions[bot]@users.noreply.github.com"
             git config --global user.name "github-actions[bot]"
             git remote add hf https://oauth:$HF_TOKEN@huggingface.co/spaces/rodunia/llm-research-app
             git push hf main --force
   ```

3. **Commit directly to main branch**

## Step 3: Verify GitHub Secrets

Your secrets should already be configured, but verify:

1. Go to https://github.com/rodunia/llm_research_app/settings/secrets/actions
2. Confirm this secret exists:
   - `HF_TOKEN` - Your Hugging Face write token

## Step 4: Configure Hugging Face Secrets

The app needs API keys to run on HF:

1. Go to https://huggingface.co/spaces/rodunia/llm-research-app/settings
2. Scroll to **"Repository secrets"**
3. Add these secrets:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `GOOGLE_API_KEY` - Your Google AI Studio API key
   - `ANTHROPIC_API_KEY` - Your Anthropic API key
   - `MISTRAL_API_KEY` - Your Mistral API key

## Step 5: Trigger First Deployment

Once the workflow file is created on GitHub:

**Option A: Automatic** - Just push any commit to main:
```bash
git push origin main
```

**Option B: Manual** - Trigger the workflow manually:
1. Go to https://github.com/rodunia/llm_research_app/actions
2. Click "Deploy to Hugging Face Spaces"
3. Click "Run workflow" → "Run workflow"

## Step 6: Verify Deployment

1. Wait 1-2 minutes for the workflow to complete
2. Check workflow status: https://github.com/rodunia/llm_research_app/actions
3. Your app should be live at: https://huggingface.co/spaces/rodunia/llm-research-app

## How It Works

Once set up, every time you push to the `main` branch on GitHub:
1. GitHub Actions workflow triggers automatically
2. Workflow clones your repo
3. Pushes code to Hugging Face Space
4. HF Space rebuilds and redeploys your app

## Troubleshooting

**Workflow fails with "invalid credentials"**
- Regenerate HF_TOKEN at https://huggingface.co/settings/tokens (must be Write token)
- Update the GitHub secret

**App shows "Missing API key" errors**
- Configure the API key secrets in HF Space settings (Step 4)

**Workflow doesn't trigger**
- Make sure the workflow file was created in `.github/workflows/deploy-to-hf.yml`
- Check Actions are enabled: https://github.com/rodunia/llm_research_app/settings/actions
