# MCP-Client
An async MCP Client built with Gemini and Python, supporting Streamable HTTP and STDIO transports for tool discovery and execution through an MCP server.


# MCP Client

A Python-based **MCP Client** that connects a **Gemini model** to an **MCP Server**.  
It discovers tools exposed by the server, converts them into Gemini-compatible function declarations, and enables interactive terminal chat where Gemini can invoke server tools automatically.

This client supports two transport modes:

- **Streamable HTTP**
- **STDIO**

---

## Features

- Connects to an MCP server over **HTTP** or **STDIO**
- Loads configuration from a `.env` file
- Uses **Gemini** as the LLM backend
- Dynamically reads MCP tools from the server
- Maps MCP tool schemas into Gemini function declarations
- Lets Gemini call tools during chat
- Runs fully asynchronously with `asyncio`

---

## How It Works

1. The client connects to an MCP server.
2. It fetches the list of available tools using `list_tools()`.
3. It converts those tools into Gemini function declarations.
4. The user types a prompt in the terminal.
5. Gemini decides whether to answer directly or call a tool.
6. If a tool call is requested:
   - the client executes it through the MCP session
   - sends the result back to Gemini
   - prints the final assistant response

---

## Requirements

Install dependencies:

```bash
pip install google-genai python-dotenv mcp
