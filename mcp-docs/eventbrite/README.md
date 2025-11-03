# Eventbrite MCP Server

## Overview

Event management and ticketing via Eventbrite API

**Category:** Events
**Package:** `@modelcontextprotocol/server-eventbrite`

## Configuration

### Local Server Configuration

```json
{
  "eventbrite": {
    "command": "npx"
,
    "args": [
      "-y",
      "@modelcontextprotocol/server-eventbrite"
    ]
,
    "env": {
      "EVENTBRITE_API_KEY": "$YOUR_EVENTBRITE_API_KEY_HERE"
    }
  }
}
```

## Required Environment Variables

- `EVENTBRITE_API_KEY`: Authentication token or API key

## Installation

Install via npm:

```bash
npm install -g @modelcontextprotocol/server-eventbrite
```

Or use npx directly (recommended):

```bash
npx @modelcontextprotocol/server-eventbrite
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Package Repository](https://github.com/modelcontextprotocol/server-eventbrite)

