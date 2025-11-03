# Git Visualization MCP Server

## Overview

Git repository visualization and analysis tools

**Category:** Development Tools
**Package:** `custom-git-viz`

## Configuration

### Local Server Configuration

```json
{
  "git-visualization": {
    "command": "python"
,
    "args": [
      "/Users/alyshialedlie/code/RepoViz/enhanced_mcp_server.py"
    ]
  }
}
```

## Installation

Ensure Python 3.8+ is installed, then install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Add this server to your MCP client configuration file (e.g., Claude Desktop config, Cursor MCP settings) using the configuration above.

## Schema.org Metadata

This directory includes a `schema.json` file with Schema.org structured data describing this MCP server.

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

