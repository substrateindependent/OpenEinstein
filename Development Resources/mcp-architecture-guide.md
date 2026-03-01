# The Practical Guide to MCP Architecture

## Building AI Agents That Connect to Your Software

*A reference guide for founders, CTOs, and technical leaders evaluating or implementing Model Context Protocol*

---

## What MCP Is (and Why It Matters)

Model Context Protocol (MCP) is an open standard — originally created by Anthropic in November 2024 and now governed by the Linux Foundation — that standardizes how AI applications connect to external data sources and tools. Think of it as USB-C for AI: a universal interface that lets any compatible AI agent talk to any compatible data source.

Before MCP, connecting an AI agent to your proprietary software meant building custom API integrations for every AI platform you wanted to support. If you wanted your system to work with Claude, ChatGPT, Cursor, and your own internal agent, that was four separate integrations to build and maintain. MCP collapses this from an N×M problem to an N+M problem: you build one MCP server for your software, and it works with every MCP-compatible client.

As of early 2026, MCP has been adopted by Anthropic, OpenAI, Google DeepMind, Microsoft, and a rapidly growing ecosystem of developer tools and enterprise platforms. The protocol was donated to the Agentic AI Foundation (a directed fund under the Linux Foundation) in December 2025, co-founded by Anthropic, Block, and OpenAI — signaling broad industry commitment to the standard.

---

## Architecture Overview

MCP uses a three-layer client-server model:

### The Three Layers

**Host** — The AI application the end user interacts with. This could be Claude Desktop, ChatGPT, Cursor, VS Code with Copilot, or your own custom-built AI application. The host provides the runtime environment and manages communication between clients and servers.

**Client** — A protocol-aware bridge that lives inside the host application. It knows how to speak MCP — discovering available tools, making requests, and handling responses. In most cases, you don't build the client yourself; it's built into the host. (The exception is if you're building a completely custom AI application, in which case you'll implement both the client and the host.)

**Server** — This is what you build. The MCP server wraps your proprietary software, database, or API and exposes its capabilities through a standardized interface. It translates between the MCP protocol and your system's native interfaces.

### How They Communicate

```
┌─────────────────────────────────────────────┐
│  HOST (Claude Desktop, ChatGPT, Custom App) │
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │ Client  │  │ Client  │  │ Client  │     │
│  └────┬────┘  └────┬────┘  └────┬────┘     │
└───────┼────────────┼────────────┼───────────┘
        │            │            │
   MCP Protocol  MCP Protocol  MCP Protocol
        │            │            │
   ┌────┴────┐  ┌────┴────┐  ┌────┴────┐
   │ Your    │  │ Google  │  │ Slack   │
   │ Server  │  │ Drive   │  │ Server  │
   │         │  │ Server  │  │         │
   └────┬────┘  └─────────┘  └─────────┘
        │
   Your Proprietary
   Software / API / DB
```

A single host can connect to multiple MCP servers simultaneously. This means a user could ask a question and the AI agent could pull context from your proprietary system, Google Drive, and Slack all in the same response — each through its own MCP server.

---

## The Three Primitives

MCP servers expose capabilities through three core primitives:

### Tools

Tools are functions that the LLM can call. They're the most commonly used primitive and the one you'll likely start with. Each tool has a name, a description (which the LLM reads to decide when to use it), an input schema, and a handler function.

**When to use:** Any operation where the AI needs to *do something* — query a database, trigger a workflow, fetch real-time data, create a record, run a calculation.

**Key detail:** The LLM decides when to call tools based on the user's query and the tool descriptions you provide. Good descriptions are critical — they're essentially prompts that tell the model what each tool does and when it's appropriate to use it.

### Resources

Resources are read-only data that clients can pull into context. Think of them as files or documents the AI can reference — API responses, configuration data, database records, documentation.

**When to use:** When you want to provide background context or reference material rather than interactive functionality. Resources are great for things like customer profiles, product catalogs, or documentation that the AI should be aware of.

### Prompts

Prompts are pre-written templates that help users accomplish specific tasks with your system. They're reusable instruction sets that can include dynamic parameters.

**When to use:** When you want to provide structured workflows or "recipes" for common tasks — like generating a quarterly report, running a standard analysis, or following a multi-step procedure.

---

## Building an MCP Server: Step by Step

### Step 1: Choose Your SDK

Anthropic provides official SDKs in the two most common languages:

**Python SDK** — Uses FastMCP for rapid development. Best for teams already working in Python or for wrapping Python-based APIs and data pipelines.

```bash
pip install mcp httpx
```

**TypeScript SDK** — Ideal when your stack is Node.js/React or when you want tight type safety. Published as `@modelcontextprotocol/sdk`.

```bash
npm install @modelcontextprotocol/sdk zod
```

There's also an official **C# SDK** maintained in collaboration with Microsoft for .NET environments.

### Step 2: Define Your Tools

Here's a minimal Python example wrapping a hypothetical proprietary API:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App Server")

@mcp.tool()
def get_customer(customer_id: str) -> dict:
    """Look up a customer by ID. Returns their profile,
    account status, and recent activity."""
    return my_api.fetch_customer(customer_id)

@mcp.tool()
def search_orders(
    query: str,
    status: str = "all",
    limit: int = 10
) -> list:
    """Search orders by keyword with optional status filter.
    Valid statuses: all, pending, shipped, delivered, cancelled."""
    return my_api.search_orders(query, status=status, limit=limit)

@mcp.tool()
def create_support_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "normal"
) -> dict:
    """Create a new support ticket for a customer.
    Priority can be: low, normal, high, urgent."""
    return my_api.create_ticket(
        customer_id, subject, description, priority
    )
```

And the equivalent in TypeScript:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-app-server",
  version: "1.0.0"
});

server.registerTool(
  "get_customer",
  {
    title: "Get Customer",
    description: "Look up a customer by ID. Returns profile, account status, and recent activity.",
    inputSchema: {
      customer_id: z.string().describe("The unique customer identifier")
    },
    annotations: { readOnlyHint: true }
  },
  async ({ customer_id }) => ({
    content: [{
      type: "text",
      text: JSON.stringify(await myApi.fetchCustomer(customer_id))
    }]
  })
);
```

**Writing good tool descriptions matters.** The LLM reads these descriptions to decide which tool to call and when. Be specific about what the tool does, what inputs it expects, and what it returns. Include valid values for enum-like parameters. Think of descriptions as mini-prompts.

### Step 3: Optionally Add Resources

```python
@mcp.resource("customer://{customer_id}/profile")
def get_customer_profile(customer_id: str) -> str:
    """Full customer profile including history and preferences"""
    profile = my_api.fetch_full_profile(customer_id)
    return json.dumps(profile, indent=2)

@mcp.resource("docs://api-reference")
def get_api_docs() -> str:
    """API documentation and schema reference"""
    return load_file("api_reference.md")
```

### Step 4: Choose Your Transport

This is one of the most important architectural decisions. MCP supports two primary transport mechanisms:

#### Stdio (Local Process)

The server runs as a local process on the user's machine, communicating over stdin/stdout.

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Pros:** Dead simple. No auth needed (inherits process security). Zero network latency. Great for development and single-user desktop scenarios.

**Cons:** Only works locally. Each user needs the server installed on their machine. Not suitable for multi-user or web-based deployments.

**Use when:** Building integrations for Claude Desktop, Cursor, VS Code, or other desktop AI tools. Good for internal tools where you control the machines.

#### Streamable HTTP (Remote Service)

The server runs as a web service, accessible over HTTPS.

```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

**Pros:** Works for multi-user deployments. Can be hosted centrally. Supports web-based and mobile clients. Scalable.

**Cons:** Requires proper authentication (OAuth 2.0/2.1 with PKCE). More infrastructure to manage. Need to handle session management.

**Use when:** Building production services, multi-user deployments, or any scenario where the server needs to be accessible over a network.

**Note:** There's also a legacy HTTP+SSE transport from the original 2024 spec. The newer Streamable HTTP transport (2025-03-26 spec) is preferred as it works better with serverless platforms and modern infrastructure.

### Step 5: Test with the MCP Inspector

Before connecting to a real AI host, test your server using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector build/index.js    # TypeScript
npx @modelcontextprotocol/inspector python server.py   # Python
```

This gives you a browser-based UI at `http://127.0.0.1:6274` where you can see all your registered tools, call them with test inputs, and inspect the responses. This is invaluable for debugging before you introduce the complexity of an LLM deciding which tools to call.

### Step 6: Connect to a Host

#### For Local (Stdio) Servers

Add your server to the host's configuration. For Claude Desktop, edit the config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-app": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/your/server",
        "run", "server"
      ],
      "env": {
        "API_KEY": "your-api-key-here"
      }
    }
  }
}
```

For TypeScript servers:

```json
{
  "mcpServers": {
    "my-app": {
      "command": "node",
      "args": ["/absolute/path/to/build/index.js"]
    }
  }
}
```

#### For Remote (HTTP) Servers

Deploy your server to any HTTPS-capable host (Cloudflare Workers, AWS, Fly.io, Vercel, etc.) and configure the client to point at the endpoint URL. Authentication configuration will vary by host application.

---

## Security Considerations

### Authentication and Authorization

For **stdio** servers, security relies on the process execution context. Credentials are typically passed via environment variables. This is acceptable because the server runs locally on a trusted machine.

For **HTTP** servers, the MCP spec mandates OAuth 2.0/2.1 authentication with PKCE (Proof Key for Code Exchange). Key requirements include:

- Implementing OAuth discovery endpoints (`/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`)
- Supporting dynamic client registration where applicable
- Enforcing scope-based access controls
- Integration with identity providers (Auth0, Okta, etc.) is the recommended pattern

### Data Protection

MCP servers often sit between AI models and sensitive internal systems. Critical practices include:

- **Principle of least privilege:** Only expose the minimum data and operations necessary. Don't give a customer-facing agent access to internal financial data.
- **Input validation:** Validate and sanitize all inputs from the LLM. Treat tool calls as untrusted input.
- **Audit logging:** Log all tool calls, especially write operations. You need visibility into what the AI is doing with your systems.
- **Rate limiting:** Protect your backend systems from excessive requests, whether from bugs or adversarial prompts.
- **Secrets management:** Never expose API keys, tokens, or credentials in tool responses. Keep sensitive logic server-side.

### Trust Boundaries

Tool descriptions and annotations should be considered untrusted unless they come from a verified server. The LLM's decision about which tools to call is influenced by these descriptions, making them a potential vector for prompt injection if the server source isn't trusted.

---

## Architecture Patterns

### Pattern 1: Internal Agent (Single Org)

Your team builds an MCP server wrapping internal systems. Employees use it through Claude Desktop or a custom internal chat interface.

```
Employee → Claude Desktop → MCP Client → Your MCP Server → Internal API/DB
```

**Best for:** Internal productivity tools, knowledge base access, operational dashboards.
**Transport:** Stdio for desktop, HTTP for web-based internal tools.

### Pattern 2: Customer-Facing Agent

You build an AI agent as a product feature. Your MCP server provides the real-time data backbone.

```
Customer → Your AI Chat UI → Your MCP Client → Your MCP Server → Your Backend
```

**Best for:** AI-powered customer support, intelligent product interfaces, guided workflows.
**Transport:** HTTP (you control both client and server).
**Note:** In this pattern you're building both the client and server, giving you full control over the interaction model.

### Pattern 3: Platform Integration

You want third-party AI tools to integrate with your platform (similar to how GitHub, Slack, and Google Drive have built MCP servers).

```
Any User → Any MCP Host → Any MCP Client → Your Published MCP Server → Your Platform API
```

**Best for:** SaaS products wanting AI ecosystem presence. Developer platforms. Any product that benefits from AI-powered access.
**Transport:** HTTP with full OAuth implementation.

### Pattern 4: Multi-Source Agent

An AI agent that pulls from multiple systems simultaneously to answer complex queries.

```
                          ┌→ CRM Server → Salesforce
User → AI Host → Client ─┼→ Analytics Server → Your Data Warehouse
                          └→ Docs Server → Internal Wiki
```

**Best for:** Executive dashboards, cross-functional analysis, complex decision support.
**Key consideration:** Each server is independent and reusable. The AI host orchestrates calls across all of them based on the user's query.

---

## MCP vs. Alternatives

### MCP vs. Custom API Integrations (Function Calling)

Traditional function calling (like OpenAI's function calling API) requires you to define tools inline with each API call and wire up the execution yourself. MCP externalizes this into a standalone, reusable server.

**Choose MCP when:** You want the integration to work across multiple AI platforms, or when the tool/data layer is complex enough to warrant its own service.

**Choose direct function calling when:** You're building a tightly coupled, single-platform application and want maximum control over the interaction.

### MCP vs. RAG (Retrieval-Augmented Generation)

RAG pre-indexes your data into a vector store and retrieves relevant chunks at query time. MCP provides live, structured access to systems and data.

**RAG is better for:** Large document corpora, historical knowledge bases, unstructured text search.

**MCP is better for:** Real-time data, structured operations (CRUD), live system interactions, workflows that require current state.

**Combined approach:** Use RAG for deep background knowledge and MCP for real-time operations. They're complementary, not competing.

---

## Common Pitfalls

**Overly broad tool descriptions.** If a tool description is vague ("does stuff with data"), the LLM won't know when to use it. Be specific and include examples of when the tool is appropriate.

**Too many tools.** LLMs perform worse with large tool sets. Group related operations logically and keep the total number manageable (under ~20 for most use cases). Consider splitting into multiple focused servers if needed.

**Exposing raw database access.** Don't give the AI a generic "run SQL" tool. Build purpose-specific tools that encapsulate business logic and enforce access controls.

**Ignoring error handling.** Return clear, descriptive error messages. The LLM will use error messages to decide what to do next — cryptic errors lead to poor recovery behavior.

**Skipping the Inspector.** Always test tools in isolation with the MCP Inspector before connecting to an LLM. It's much easier to debug tool behavior without the added complexity of LLM decision-making.

**Neglecting transport evolution.** The MCP transport spec is still maturing. If you're building for production, implement the latest Streamable HTTP transport and be prepared for the ecosystem to shift as standards solidify.

---

## Getting Started: Recommended Path

1. **Start with a Python stdio server.** It's the fastest path to a working prototype. Use FastMCP, define 2-3 tools, and test with the MCP Inspector.

2. **Connect to Claude Desktop.** Add your server to the config and see it work end-to-end with an actual LLM making tool calls.

3. **Iterate on tool design.** The descriptions, input schemas, and response formats matter more than you'd expect. Refine based on how the LLM actually uses your tools.

4. **Move to HTTP when ready.** Once the tool design is solid, add the Streamable HTTP transport for multi-user or production deployment.

5. **Add auth and security.** Implement OAuth, rate limiting, and audit logging before any production deployment.

6. **Consider the client side.** If you need a fully custom experience beyond what existing hosts provide, the official SDKs also support building custom MCP clients.

---

## Key Resources

- **Official Specification:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Python SDK:** [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- **TypeScript SDK:** [github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
- **C# SDK:** [github.com/modelcontextprotocol/csharp-sdk](https://github.com/modelcontextprotocol/csharp-sdk)
- **Reference Server Implementations:** [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- **MCP Inspector:** `npx @modelcontextprotocol/inspector`
- **Agentic AI Foundation (AAIF):** Governance body under the Linux Foundation

---

*Last updated: February 2026. MCP is a rapidly evolving standard — always check the official specification for the latest protocol details.*
