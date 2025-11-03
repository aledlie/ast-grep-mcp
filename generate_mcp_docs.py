#!/usr/bin/env python3
"""Generate Schema.org and README documentation for all MCP servers."""

import json
import os
from pathlib import Path
from typing import Any, Dict

# MCP metadata - descriptions for each server
MCP_DESCRIPTIONS = {
    "linkedin": {
        "description": "LinkedIn integration MCP server running locally",
        "category": "Social Media",
        "package": "Custom LinkedIn MCP",
    },
    "supabase": {
        "description": "Supabase database and backend-as-a-service integration",
        "category": "Database",
        "package": "@supabase/mcp-server",
    },
    "browserbase": {
        "description": "Browser automation and web scraping capabilities",
        "category": "Web Automation",
        "package": "@browserbasehq/mcp-server-browserbase",
    },
    "cloudflare-workers-bindings": {
        "description": "Access Cloudflare Workers bindings and KV storage",
        "category": "Cloud Infrastructure",
        "package": "@cloudflare/mcp-workers-bindings",
    },
    "cloudflare-observability": {
        "description": "Monitor and analyze Cloudflare infrastructure metrics",
        "category": "Monitoring",
        "package": "@cloudflare/mcp-observability",
    },
    "cloudflare-radar": {
        "description": "Access Cloudflare Radar internet intelligence data",
        "category": "Analytics",
        "package": "@cloudflare/mcp-radar",
    },
    "cloudflare-ai-gateway": {
        "description": "Interface with Cloudflare AI Gateway for AI model access",
        "category": "AI/ML",
        "package": "@cloudflare/mcp-ai-gateway",
    },
    "cloudflare-browser-rendering": {
        "description": "Server-side browser rendering via Cloudflare",
        "category": "Web Automation",
        "package": "@cloudflare/mcp-browser-rendering",
    },
    "ast-grep": {
        "description": "Structural code search using Abstract Syntax Tree pattern matching",
        "category": "Development Tools",
        "package": "sg-mcp",
    },
    "schema-org": {
        "description": "Generate and validate Schema.org structured data markup",
        "category": "SEO/Semantic Web",
        "package": "@custom/schema-org-mcp",
    },
    "github": {
        "description": "GitHub repository management and API integration",
        "category": "Development Tools",
        "package": "@github/github-mcp-server",
    },
    "eventbrite": {
        "description": "Event management and ticketing via Eventbrite API",
        "category": "Events",
        "package": "@modelcontextprotocol/server-eventbrite",
    },
    "postgres": {
        "description": "PostgreSQL database query and management interface",
        "category": "Database",
        "package": "@modelcontextprotocol/server-postgres",
    },
    "memory": {
        "description": "Persistent memory and context storage for AI conversations",
        "category": "AI/ML",
        "package": "@modelcontextprotocol/server-memory",
    },
    "fetch": {
        "description": "HTTP request capabilities for fetching web content",
        "category": "Web",
        "package": "@modelcontextprotocol/server-fetch",
    },
    "filesystem": {
        "description": "File system access for reading and managing files",
        "category": "System",
        "package": "@modelcontextprotocol/server-filesystem",
    },
    "porkbun": {
        "description": "DNS management and domain registration via Porkbun API",
        "category": "Infrastructure",
        "package": "@modelcontextprotocol/server-porkbun",
    },
    "auth0": {
        "description": "Identity and access management via Auth0",
        "category": "Authentication",
        "package": "@auth0/auth0-mcp-server",
    },
    "discord": {
        "description": "Discord bot integration and server management",
        "category": "Communication",
        "package": "@modelcontextprotocol/server-discord",
    },
    "redis": {
        "description": "Redis in-memory data store for caching and queuing",
        "category": "Database",
        "package": "@redis/redis-mcp-server",
    },
    "bullmq": {
        "description": "Job queue management using BullMQ and Redis",
        "category": "Queue",
        "package": "@modelcontextprotocol/server-bullmq",
    },
    "openapi": {
        "description": "OpenAPI/Swagger specification parsing and API exploration",
        "category": "Development Tools",
        "package": "@openapi/openapi-mcp-server",
    },
    "git-visualization": {
        "description": "Git repository visualization and analysis tools",
        "category": "Development Tools",
        "package": "custom-git-viz",
    },
    "scheduler-mcp": {
        "description": "Task scheduling and cron job management",
        "category": "Automation",
        "package": "scheduler-mcp",
    },
    "mcp-cron": {
        "description": "Cron-based task scheduling interface",
        "category": "Automation",
        "package": "mcp-cron",
    },
    "google-calendar": {
        "description": "Google Calendar integration for event management",
        "category": "Productivity",
        "package": "@takumi0706/google-calendar-mcp",
    },
    "tailscale": {
        "description": "Tailscale VPN management and network configuration",
        "category": "Networking",
        "package": "tailscale-mcp-server",
    },
    "doppler-custom": {
        "description": "Doppler secrets management and configuration",
        "category": "Security",
        "package": "custom-doppler-mcp",
    },
    "porkbun-custom": {
        "description": "Custom Porkbun DNS management implementation",
        "category": "Infrastructure",
        "package": "custom-porkbun-mcp",
    },
}


def generate_schema_org_json(name: str, config: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
    """Generate Schema.org JSON-LD for an MCP server."""
    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": f"{name.title()} MCP Server",
        "description": metadata["description"],
        "applicationCategory": "DeveloperApplication",
        "applicationSubCategory": metadata["category"],
        "operatingSystem": "Cross-platform",
        "softwareVersion": "latest",
        "programmingLanguage": [],
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        }
    }

    # Determine programming language from command
    command = config.get("command", "")
    if command == "npx" or command == "node":
        schema["programmingLanguage"].append("JavaScript")
    elif command == "python" or command.endswith("python"):
        schema["programmingLanguage"].append("Python")
    elif command == "uv":
        schema["programmingLanguage"].append("Python")
    elif "go" in command or command.endswith("-server"):
        schema["programmingLanguage"].append("Go")
    elif command == "docker":
        schema["programmingLanguage"].append("Container")

    # Add installation URL if package is known
    if "modelcontextprotocol" in metadata["package"]:
        schema["url"] = f"https://github.com/modelcontextprotocol/{metadata['package'].split('/')[-1]}"
    elif "@" in metadata["package"] and not metadata["package"].startswith("@custom"):
        schema["softwareHelp"] = {
            "@type": "WebPage",
            "url": f"https://www.npmjs.com/package/{metadata['package']}"
        }

    # Add requirements
    if config.get("env"):
        schema["softwareRequirements"] = {
            "@type": "SoftwareApplication",
            "name": "Environment Variables",
            "description": f"Required environment variables: {', '.join(config['env'].keys())}"
        }

    return schema


def generate_readme(name: str, config: Dict[str, Any], metadata: Dict[str, str]) -> str:
    """Generate README.md content for an MCP server."""
    readme = f"""# {name.replace('-', ' ').title()} MCP Server

## Overview

{metadata['description']}

**Category:** {metadata['category']}
**Package:** `{metadata['package']}`

## Configuration

"""

    # Add configuration based on type
    if "url" in config:
        readme += f"""### Remote Server Configuration

This MCP connects to a remote server endpoint.

```json
{{
  "{name}": {{
    "url": "{config['url']}"
"""
        if "headers" in config:
            readme += """,
    "headers": {
      "Authorization": "Bearer YOUR_TOKEN_HERE"
    }
"""
        readme += """  }
}
```

"""
    else:
        readme += f"""### Local Server Configuration

```json
{{
  "{name}": {{
    "command": "{config['command']}"
"""
        if config.get("args"):
            args_str = ',\n      '.join([f'"{arg}"' for arg in config["args"]])
            readme += f""",
    "args": [
      {args_str}
    ]
"""
        if config.get("env"):
            readme += """,
    "env": {
"""
            for key in config["env"].keys():
                readme += f'      "{key}": "$YOUR_{key}_HERE",\n'
            readme = readme.rstrip(",\n") + "\n    }\n"
        readme += """  }
}
```

"""

    # Add environment variables section
    if config.get("env"):
        readme += """## Required Environment Variables

"""
        for env_var, env_value in config["env"].items():
            readme += f"- `{env_var}`: "
            if "TOKEN" in env_var or "KEY" in env_var:
                readme += "Authentication token or API key\n"
            elif "SECRET" in env_var:
                readme += "Secret key for authentication\n"
            elif "URL" in env_var:
                readme += "Connection URL\n"
            elif "DOMAIN" in env_var:
                readme += "Domain name\n"
            elif "CLIENT_ID" in env_var:
                readme += "OAuth client ID\n"
            elif "CLIENT_SECRET" in env_var:
                readme += "OAuth client secret\n"
            else:
                readme += "Configuration value\n"
        readme += "\n"

    # Add installation section
    readme += """## Installation

"""

    if config.get("command") == "npx":
        package = None
        for arg in config.get("args", []):
            if arg.startswith("@") or (arg.startswith("-") == False and "/" not in arg and "mcp" in arg.lower()):
                package = arg
                break
        if package:
            readme += f"""Install via npm:

```bash
npm install -g {package}
```

Or use npx directly (recommended):

```bash
npx {package}
```

"""
    elif config.get("command") == "python" or config.get("command", "").endswith("python"):
        readme += """Ensure Python 3.8+ is installed, then install dependencies:

```bash
pip install -r requirements.txt
```

"""
    elif config.get("command") == "uv":
        readme += """Install using uv:

```bash
uv sync
```

"""
    elif config.get("command") == "docker":
        readme += """Pull the Docker image:

```bash
docker pull ghcr.io/github/github-mcp-server
```

"""

    readme += """## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

"""

    if "modelcontextprotocol" in metadata["package"]:
        readme += f"""- [MCP Documentation](https://modelcontextprotocol.io/)
- [Package Repository](https://github.com/modelcontextprotocol/{metadata['package'].split('/')[-1]})

"""
    else:
        readme += """- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

"""

    return readme


def main():
    """Generate documentation for all MCP servers."""
    # Read config files
    config_paths = [
        Path.home() / ".config/claude/claude_desktop_config.json",
        Path.home() / ".claude/claude_desktop_config.json"
    ]

    all_servers = {}
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                all_servers.update(config.get("mcpServers", {}))

    # Generate documentation for each server
    docs_dir = Path("mcp-docs")
    docs_dir.mkdir(exist_ok=True)

    for name, config in all_servers.items():
        print(f"Generating documentation for {name}...")

        # Get or create metadata
        metadata = MCP_DESCRIPTIONS.get(name, {
            "description": f"MCP server for {name}",
            "category": "Utility",
            "package": f"custom-{name}"
        })

        # Create directory
        server_dir = docs_dir / name
        server_dir.mkdir(exist_ok=True)

        # Generate Schema.org JSON
        schema = generate_schema_org_json(name, config, metadata)
        with open(server_dir / "schema.json", "w") as f:
            json.dump(schema, f, indent=2)

        # Generate README
        readme = generate_readme(name, config, metadata)
        with open(server_dir / "README.md", "w") as f:
            f.write(readme)

    print(f"\nGenerated documentation for {len(all_servers)} MCP servers in {docs_dir}")

    # Generate index
    generate_index(all_servers, docs_dir)


def generate_index(servers: Dict[str, Any], docs_dir: Path):
    """Generate master index README."""
    index = """# MCP Servers Documentation

This directory contains comprehensive documentation for all configured Model Context Protocol (MCP) servers.

## Overview

MCP servers extend AI assistants with specialized capabilities through a standardized protocol. Each server provides tools, resources, and prompts that AI can use to perform specific tasks.

## Configured Servers

"""

    # Group by category
    by_category = {}
    for name in sorted(servers.keys()):
        metadata = MCP_DESCRIPTIONS.get(name, {"category": "Utility", "description": f"MCP server for {name}"})
        category = metadata["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append((name, metadata["description"]))

    # Write by category
    for category in sorted(by_category.keys()):
        index += f"\n### {category}\n\n"
        for name, description in by_category[category]:
            index += f"- **[{name}](./{name}/README.md)** - {description}\n"

    index += f"""

## Directory Structure

Each MCP server has its own subdirectory containing:

- `README.md` - Comprehensive documentation including configuration, installation, and usage
- `schema.json` - Schema.org structured data describing the server

## Total Servers

**{len(servers)}** MCP servers are currently documented.

## Adding a New Server

To document a new MCP server:

1. Add server configuration to your MCP client config file
2. Add metadata to `MCP_DESCRIPTIONS` in `generate_mcp_docs.py`
3. Run `python generate_mcp_docs.py` to regenerate documentation

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Server Registry](https://github.com/modelcontextprotocol/servers)
- [Claude Code Documentation](https://docs.claude.com/claude-code)

---

*Documentation generated automatically from MCP configuration files.*
"""

    with open(docs_dir / "README.md", "w") as f:
        f.write(index)

    print(f"Generated master index at {docs_dir / 'README.md'}")


if __name__ == "__main__":
    main()
