# Doppler Migration Guide

This guide helps you migrate from manual environment variable configuration to Doppler-managed secrets for the ast-grep-mcp server.

## Table of Contents

- [Why Migrate to Doppler?](#why-migrate-to-doppler)
- [Prerequisites](#prerequisites)
- [Migration Steps](#migration-steps)
  - [Step 1: Install Doppler](#step-1-install-doppler)
  - [Step 2: Authenticate](#step-2-authenticate)
  - [Step 3: Access the Project](#step-3-access-the-project)
  - [Step 4: Verify Secrets](#step-4-verify-secrets)
  - [Step 5: Update MCP Client Configuration](#step-5-update-mcp-client-configuration)
  - [Step 6: Test the Migration](#step-6-test-the-migration)
  - [Step 7: Clean Up](#step-7-clean-up)
- [Rollback Plan](#rollback-plan)
- [Troubleshooting](#troubleshooting)
- [Multiple Environments](#multiple-environments)
- [Team Collaboration](#team-collaboration)
- [FAQ](#faq)

## Why Migrate to Doppler?

Doppler provides several advantages over manual environment variable management:

### Security Benefits

- **No hardcoded credentials** in configuration files or scripts
- **Automatic secret rotation** without updating configs
- **Encrypted storage** with SOC 2 Type II compliance
- **Access controls** with role-based permissions
- **Audit logging** for all secret access

### Developer Experience

- **Centralized management** of secrets across environments
- **Easy environment switching** (dev/staging/production)
- **Team collaboration** without sharing credentials
- **Version history** with rollback capability
- **CLI and API** for automation

### Operational Benefits

- **No .env files** to manage or accidentally commit
- **Consistent secrets** across local development and CI/CD
- **Integration with MCP clients** without manual env var management
- **Scalable** for teams and multiple projects

## Prerequisites

Before migrating, ensure you have:

1. **Current working setup** with manual environment variables
2. **Sentry DSN** (if using error tracking)
3. **macOS, Linux, or Windows** with terminal access
4. **Admin access** to install Doppler CLI

## Migration Steps

### Step 1: Install Doppler

**macOS:**
```bash
brew install dopplerhq/cli/doppler
```

**Linux:**
```bash
curl -Ls https://cli.doppler.com/install.sh | sh
```

**Windows (Scoop):**
```powershell
scoop bucket add doppler https://github.com/DopplerHQ/scoop-doppler.git
scoop install doppler
```

**Windows (Direct):**
Download from [Doppler Releases](https://github.com/DopplerHQ/cli/releases)

**Verify installation:**
```bash
doppler --version
```

Expected output: `doppler version X.Y.Z`

### Step 2: Authenticate

```bash
doppler login
```

This command:
1. Opens a browser for authentication
2. Asks you to grant CLI access
3. Saves authentication token locally

**Note**: If you don't have a Doppler account yet, sign up at [doppler.com](https://www.doppler.com/) first.

### Step 3: Access the Project

The ast-grep-mcp project is already configured in Doppler:

- **Project**: `bottleneck`
- **Config**: `dev` (default)

**Verify access:**
```bash
# List all projects you have access to
doppler projects

# You should see "bottleneck" in the list
```

If you don't see `bottleneck`, contact your team administrator for access.

### Step 4: Verify Secrets

Check what secrets are already configured:

```bash
# View all secrets in the dev config
doppler secrets --project bottleneck --config dev

# View specific secret (safe - shows value)
doppler secrets get SENTRY_DSN --project bottleneck --config dev --plain
```

**Expected secrets:**

| Secret | Description | Example Value |
|--------|-------------|---------------|
| `SENTRY_DSN` | Sentry project DSN | `https://key@sentry.io/123` |
| `SENTRY_ENVIRONMENT` | Environment name | `development` |

**If secrets are missing:**

```bash
# Set your Sentry DSN
doppler secrets set SENTRY_DSN="https://your-key@sentry.io/project-id" --project bottleneck --config dev

# Set environment
doppler secrets set SENTRY_ENVIRONMENT="development" --project bottleneck --config dev
```

**Copy from your current setup:**

If you have existing environment variables:

```bash
# On macOS/Linux
doppler secrets set SENTRY_DSN="$SENTRY_DSN" --project bottleneck --config dev

# On Windows (PowerShell)
doppler secrets set SENTRY_DSN="$env:SENTRY_DSN" --project bottleneck --config dev
```

### Step 5: Update MCP Client Configuration

Now update your MCP client to use Doppler instead of direct environment variables.

#### Cursor

**Before** (`.cursor-mcp/settings.json`):
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "https://your-key@sentry.io/project-id",
        "SENTRY_ENVIRONMENT": "production"
      }
    }
  }
}
```

**After**:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "dev",
        "--command",
        "uv --directory /absolute/path/to/ast-grep-mcp run main.py"
      ]
    }
  }
}
```

#### Claude Desktop

**macOS** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

**Before**:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "https://your-key@sentry.io/project-id",
        "SENTRY_ENVIRONMENT": "production"
      }
    }
  }
}
```

**After**:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "dev",
        "--command",
        "uv --directory /absolute/path/to/ast-grep-mcp run main.py"
      ]
    }
  }
}
```

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "dev",
        "--command",
        "uv --directory C:\\absolute\\path\\to\\ast-grep-mcp run main.py"
      ]
    }
  }
}
```

### Step 6: Test the Migration

**Test 1: Manual server startup**

```bash
cd /path/to/ast-grep-mcp
doppler run --project bottleneck --config dev -- uv run main.py
```

Expected output:
```
Sentry initialized with DSN: https://***@sentry.io/***
Starting ast-grep MCP server...
```

**Test 2: Verify secrets are injected**

```bash
doppler run --project bottleneck --config dev -- env | grep SENTRY
```

Expected output:
```
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENVIRONMENT=development
```

**Test 3: Restart MCP client**

1. Quit and restart Cursor or Claude Desktop
2. Wait for MCP server to initialize
3. Run `test_sentry_integration()` tool
4. Verify response shows `"sentry_enabled": true`

**Test 4: Verify error tracking**

1. Trigger a test error (use `test_sentry_integration()` tool)
2. Go to Sentry dashboard: https://sentry.io/organizations/[org]/issues/
3. Look for "Test error from ast-grep-mcp"
4. Verify error appears within 1-2 minutes

### Step 7: Clean Up

After successful migration:

1. **Remove hardcoded credentials** from MCP client config files
2. **Delete .env files** (if any) containing Sentry credentials
3. **Update team documentation** with new Doppler setup instructions
4. **Revoke old Sentry DSNs** (optional, if rotating credentials)

**Optional: Use .doppler.yaml for easier CLI usage**

The project already includes `.doppler.yaml`:

```yaml
# .doppler.yaml
setup:
  project: bottleneck
  config: dev
```

This allows shorter commands:

```bash
# Before
doppler run --project bottleneck --config dev -- uv run main.py

# After (with .doppler.yaml)
doppler run -- uv run main.py
```

## Rollback Plan

If you encounter issues with Doppler, you can quickly rollback:

### Quick Rollback

**Step 1**: Revert MCP client configuration to original (manual env vars)

**Cursor/Claude Desktop**:
```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "https://your-key@sentry.io/project-id",
        "SENTRY_ENVIRONMENT": "production"
      }
    }
  }
}
```

**Step 2**: Restart MCP client

**Step 3**: Verify server works with manual configuration

### Preserve Both Configurations

During migration, keep both configurations in your MCP settings:

```json
{
  "mcpServers": {
    "ast-grep": {
      "command": "doppler",
      "args": ["run", "--project", "bottleneck", "--config", "dev", "--command", "uv --directory /path run main.py"]
    },
    "ast-grep-fallback": {
      "command": "uv",
      "args": ["--directory", "/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {
        "SENTRY_DSN": "https://your-key@sentry.io/project-id",
        "SENTRY_ENVIRONMENT": "production"
      }
    }
  }
}
```

Switch between them by changing which one is active.

## Troubleshooting

### "doppler: command not found"

**Cause**: Doppler CLI not installed or not in PATH

**Solution**:
```bash
# Verify installation
which doppler

# If not found, reinstall
brew install dopplerhq/cli/doppler  # macOS

# Or add to PATH
export PATH="$PATH:$HOME/.doppler/bin"  # Linux
```

### "Authentication required"

**Cause**: Not logged into Doppler CLI

**Solution**:
```bash
doppler login

# Verify authentication
doppler me
```

### "Project not found"

**Cause**: Don't have access to `bottleneck` project

**Solution**:
1. Verify project name: `doppler projects`
2. Contact team admin for access
3. Or create your own project:
   ```bash
   doppler projects create my-ast-grep
   doppler configs create dev --project my-ast-grep
   ```

### "Secret SENTRY_DSN not found"

**Cause**: Secret not set in Doppler config

**Solution**:
```bash
# Set the secret
doppler secrets set SENTRY_DSN="your-dsn" --project bottleneck --config dev

# Verify
doppler secrets get SENTRY_DSN --project bottleneck --config dev
```

### MCP server not starting with Doppler

**Cause**: Various - see detailed debugging steps

**Solution**:
```bash
# Test 1: Verify Doppler can run commands
doppler run --project bottleneck --config dev -- echo "test"

# Test 2: Verify uv is in PATH
doppler run --project bottleneck --config dev -- which uv

# Test 3: Run server manually with verbose output
doppler run --project bottleneck --config dev -- uv run main.py --log-level DEBUG

# Test 4: Check MCP client logs
# Cursor: ~/.cursor-mcp/logs/
# Claude Desktop: ~/Library/Logs/Claude/
```

### Environment variables not injected

**Cause**: Doppler not wrapping the command correctly

**Solution**:
```bash
# Verify secrets are injected
doppler run --project bottleneck --config dev -- env | grep SENTRY

# If empty, check command format
# WRONG: "uv --directory /path run main.py" (no quotes)
# RIGHT: "uv --directory /path run main.py" (in args array)
```

## Multiple Environments

Doppler supports multiple environments for the same project.

### Create Production Config

```bash
# Create production config
doppler configs create prd --project bottleneck

# Set production secrets
doppler secrets set SENTRY_DSN="https://prod-key@sentry.io/prod-id" --project bottleneck --config prd
doppler secrets set SENTRY_ENVIRONMENT="production" --project bottleneck --config prd
```

### Use Production Config

Update MCP client configuration:

```json
{
  "mcpServers": {
    "ast-grep-prod": {
      "command": "doppler",
      "args": [
        "run",
        "--project", "bottleneck",
        "--config", "prd",  // Changed from "dev"
        "--command",
        "uv --directory /absolute/path/to/ast-grep-mcp run main.py"
      ]
    }
  }
}
```

### Environment-Specific Settings

| Environment | Config Name | SENTRY_ENVIRONMENT | Trace Sample Rate |
|-------------|-------------|-------------------|------------------|
| Development | `dev` | `development` | 1.0 (100%) |
| Staging | `stg` | `staging` | 0.5 (50%) |
| Production | `prd` | `production` | 0.1 (10%) |

Set trace sample rate:

```bash
doppler secrets set SENTRY_TRACES_SAMPLE_RATE="0.1" --project bottleneck --config prd
```

Then update `main.py` to read from environment variable:

```python
traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
```

## Team Collaboration

### Inviting Team Members

1. Go to [Doppler Dashboard](https://dashboard.doppler.com/)
2. Navigate to **Team** → **Members**
3. Click **Invite Member**
4. Set role (Admin, Developer, Read-only)
5. Send invitation

### Role-Based Access

| Role | Permissions |
|------|------------|
| **Owner** | Full access, can delete project |
| **Admin** | Manage secrets, configs, members |
| **Developer** | Read/write secrets, create configs |
| **Read-only** | View secrets only (useful for auditing) |

### Sharing Secrets Securely

**DO NOT:**
- Share Sentry DSN via Slack/email
- Commit .env files with credentials
- Use shared credentials in team chat

**DO:**
1. Add team members to Doppler project
2. Let them access secrets via Doppler CLI
3. Use role-based access for security
4. Enable audit logging

### Audit Logging

View who accessed secrets:

1. Go to **Project Settings** → **Audit Logs**
2. Filter by secret name (`SENTRY_DSN`)
3. See access history (timestamp, user, action)

## FAQ

### Q: Do I need to migrate?

**A**: No, manual environment variables still work. Doppler is optional but recommended for teams and production deployments.

### Q: Will this affect my existing setup?

**A**: No, until you update your MCP client configuration. The server works with both manual env vars and Doppler.

### Q: Can I use Doppler for other secrets?

**A**: Yes! Add any secrets you need:

```bash
doppler secrets set DATABASE_URL="postgres://..." --project bottleneck --config dev
doppler secrets set API_KEY="your-api-key" --project bottleneck --config dev
```

Then access them in your code:

```python
import os
db_url = os.environ.get("DATABASE_URL")
api_key = os.environ.get("API_KEY")
```

### Q: What if I want to use a different Doppler project?

**A**: Create your own project:

```bash
# Create project
doppler projects create my-ast-grep-mcp

# Create config
doppler configs create dev --project my-ast-grep-mcp

# Set secrets
doppler secrets set SENTRY_DSN="your-dsn" --project my-ast-grep-mcp --config dev

# Update MCP client config
# Change: --project bottleneck
# To: --project my-ast-grep-mcp
```

### Q: How do I rotate Sentry DSN?

**A**: With Doppler, rotation is easy:

```bash
# Get new DSN from Sentry dashboard
# Update secret in Doppler
doppler secrets set SENTRY_DSN="new-dsn" --project bottleneck --config dev

# Restart MCP server (automatic with Doppler)
# No need to update configuration files!
```

### Q: Can I use Doppler in CI/CD?

**A**: Yes! Use service tokens:

```bash
# Create service token
doppler configs tokens create ci-token --project bottleneck --config dev

# Use in CI/CD (e.g., GitHub Actions)
env:
  DOPPLER_TOKEN: ${{ secrets.DOPPLER_TOKEN }}

# Run commands
doppler run -- uv run pytest
```

### Q: What happens if Doppler is down?

**A**: Doppler CLI caches secrets locally. If Doppler API is unreachable:

1. CLI uses cached secrets (valid for 4 hours)
2. Warning is shown but server continues
3. No impact on running MCP server instances

For critical production:
- Use fallback configuration (manual env vars)
- Set up monitoring for Doppler availability
- Keep emergency credentials in secure vault

### Q: How much does Doppler cost?

**A**: Doppler has a generous free tier:

- **Free**: Up to 5 users, unlimited projects/configs
- **Team**: $12/user/month (advanced features)
- **Enterprise**: Custom pricing (SSO, audit logs, SLA)

For personal/small team use of ast-grep-mcp, the free tier is sufficient.

## Next Steps

After successful migration:

1. **Explore Doppler features**:
   - Set up additional environments (staging, production)
   - Add team members
   - Configure audit logging
   - Set up service tokens for CI/CD

2. **Optimize Sentry configuration**:
   - Adjust sampling rates per environment
   - Set up alerts in Sentry dashboard
   - Configure data scrubbing rules
   - Review privacy compliance

3. **Document your setup**:
   - Update team wiki with Doppler instructions
   - Share this guide with team members
   - Document environment-specific configurations
   - Create runbooks for common operations

4. **Read related documentation**:
   - [SENTRY-INTEGRATION.md](SENTRY-INTEGRATION.md) - Detailed Sentry setup
   - [CLAUDE.md](CLAUDE.md) - Project overview and development guide
   - [README.md](README.md) - Main project documentation

## Support

For help with migration:

1. **Doppler Issues**: [Doppler Support](https://support.doppler.com/)
2. **Sentry Issues**: [Sentry Support](https://sentry.io/support/)
3. **ast-grep-mcp Issues**: [GitHub Issues](https://github.com/ast-grep/ast-grep-mcp/issues)

For team-specific setup questions, contact your team administrator.
