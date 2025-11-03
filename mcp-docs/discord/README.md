# Discord MCP Server

## Overview

Discord bot integration and server management

**Category:** Communication
**Package:** `@modelcontextprotocol/server-discord`

## Configuration

### Local Server Configuration

```json
{
  "discord": {
    "command": "npx"
,
    "args": [
      "-y",
      "@modelcontextprotocol/server-discord"
    ]
,
    "env": {
      "DISCORD_BOT_TOKEN": "$YOUR_DISCORD_BOT_TOKEN_HERE"
    }
  }
}
```

## Required Environment Variables

- `DISCORD_BOT_TOKEN`: Authentication token or API key

## Installation

Install via npm:

```bash
npm install -g @modelcontextprotocol/server-discord
```

Or use npx directly (recommended):

```bash
npx @modelcontextprotocol/server-discord
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Package Repository](https://github.com/modelcontextprotocol/server-discord)

