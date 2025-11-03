# Bullmq MCP Server

## Overview

Job queue management using BullMQ and Redis

**Category:** Queue
**Package:** `@modelcontextprotocol/server-bullmq`

## Configuration

### Local Server Configuration

```json
{
  "bullmq": {
    "command": "npx"
,
    "args": [
      "-y",
      "@modelcontextprotocol/server-bullmq"
    ]
,
    "env": {
      "REDIS_URL": "$YOUR_REDIS_URL_HERE"
    }
  }
}
```

## Required Environment Variables

- `REDIS_URL`: Connection URL

## Installation

Install via npm:

```bash
npm install -g @modelcontextprotocol/server-bullmq
```

Or use npx directly (recommended):

```bash
npx @modelcontextprotocol/server-bullmq
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Package Repository](https://github.com/modelcontextprotocol/server-bullmq)

