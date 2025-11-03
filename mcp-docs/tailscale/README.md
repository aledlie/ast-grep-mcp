# Tailscale MCP Server

## Overview

Tailscale VPN management and network configuration

**Category:** Networking
**Package:** `tailscale-mcp-server`

## Configuration

### Local Server Configuration

```json
{
  "tailscale": {
    "command": "/Users/alyshialedlie/code/go/bin/tailscale-mcp-server"
,
    "env": {
      "TAILSCALE_API_KEY": "$YOUR_TAILSCALE_API_KEY_HERE",
      "TAILSCALE_CLIENT_ID": "$YOUR_TAILSCALE_CLIENT_ID_HERE",
      "TAILSCALE_CLIENT_SECRET": "$YOUR_TAILSCALE_CLIENT_SECRET_HERE",
      "TAILSCALE_TAILNET": "$YOUR_TAILSCALE_TAILNET_HERE"
    }
  }
}
```

## Required Environment Variables

- `TAILSCALE_API_KEY`: Authentication token or API key
- `TAILSCALE_CLIENT_ID`: OAuth client ID
- `TAILSCALE_CLIENT_SECRET`: Secret key for authentication
- `TAILSCALE_TAILNET`: Configuration value

## Installation

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

