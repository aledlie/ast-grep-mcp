# Auth0 MCP Server

## Overview

Identity and access management via Auth0

**Category:** Authentication
**Package:** `@auth0/auth0-mcp-server`

## Configuration

### Local Server Configuration

```json
{
  "auth0": {
    "command": "npx"
,
    "args": [
      "-y",
      "@auth0/auth0-mcp-server"
    ]
,
    "env": {
      "AUTH0_DOMAIN": "$YOUR_AUTH0_DOMAIN_HERE",
      "AUTH0_CLIENT_ID": "$YOUR_AUTH0_CLIENT_ID_HERE",
      "AUTH0_CLIENT_SECRET": "$YOUR_AUTH0_CLIENT_SECRET_HERE"
    }
  }
}
```

## Required Environment Variables

- `AUTH0_DOMAIN`: Domain name
- `AUTH0_CLIENT_ID`: OAuth client ID
- `AUTH0_CLIENT_SECRET`: Secret key for authentication

## Installation

Install via npm:

```bash
npm install -g @auth0/auth0-mcp-server
```

Or use npx directly (recommended):

```bash
npx @auth0/auth0-mcp-server
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

