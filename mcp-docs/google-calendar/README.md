# Google Calendar MCP Server

## Overview

Google Calendar integration for event management

**Category:** Productivity
**Package:** `@takumi0706/google-calendar-mcp`

## Configuration

### Local Server Configuration

```json
{
  "google-calendar": {
    "command": "npx"
,
    "args": [
      "-y",
      "@takumi0706/google-calendar-mcp"
    ]
,
    "env": {
      "GOOGLE_CLIENT_ID": "$YOUR_GOOGLE_CLIENT_ID_HERE",
      "GOOGLE_CLIENT_SECRET": "$YOUR_GOOGLE_CLIENT_SECRET_HERE",
      "GOOGLE_REDIRECT_URI": "$YOUR_GOOGLE_REDIRECT_URI_HERE"
    }
  }
}
```

## Required Environment Variables

- `GOOGLE_CLIENT_ID`: OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Secret key for authentication
- `GOOGLE_REDIRECT_URI`: Configuration value

## Installation

Install via npm:

```bash
npm install -g @takumi0706/google-calendar-mcp
```

Or use npx directly (recommended):

```bash
npx @takumi0706/google-calendar-mcp
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

