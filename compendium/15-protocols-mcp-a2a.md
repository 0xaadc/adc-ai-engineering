# 15. Protocols: MCP and A2A

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Anthropic open-sourced the **Model Context Protocol (MCP)** on November 25, 2024. Through 2025 the major hosts adopted it. By December 2025, Anthropic counted more than 10,000 active public MCP servers, with ChatGPT, Cursor, Gemini, Microsoft Copilot and VS Code among the adopters (a vendor claim). On December 9, 2025, Anthropic donated MCP to the new **Agentic AI Foundation (AAIF)**, a directed fund under the Linux Foundation, and on July 28, 2026 the largest revision of the spec shipped. Google launched **Agent2Agent (A2A)** on April 9, 2025. It became a Linux Foundation project in June 2025 and an AAIF project in August 2026. [§14](14-graph-engineering.md) left a problem: a graph structures your control flow, but every node that touches a tool or another team's agent is still custom glue code.

## Why this exists

**The N×M problem (P11).** Say there are N AI applications (Claude Code, an IDE, your LangGraph service) and M systems they need (Jira, Snowflake, GitHub). Without a standard, every pair needs its own integration: N×M pieces of code, each with its own auth and bugs. With a shared protocol, each application implements the client once and each system implements the server once, so the cost becomes N+M. You know this from databases. Before ODBC and JDBC, every BI tool needed a driver per database. Afterwards, each database shipped one driver and every tool spoke one API. MCP names its own model as the Language Server Protocol, which did the same for editors and languages.

The MCP docs say: "Think of MCP like a USB-C port for AI applications." That captures plug-compatibility and misses three things:

- **A plug says nothing about quality.** MCP standardizes discovery and invocation, not tool design. A vague description stays vague, and the model picks tools from descriptions ([§10](10-tool-use.md)).
- **The device talks to the model.** Descriptions and results are text in the model's context, so a server can steer it (P9).
- **Every plugged-in device costs context.** Each tool definition consumes tokens on every request (P3).

P6 is unchanged: the model proposes a call, and code on the server executes it.

## How it works (under the hood)

### Architecture: host, client, server

```text
 ┌──────────────── Host (Claude Code, VS Code, your agent) ────────────────┐
 │  LLM + harness                                                          │
 │    ├── MCP client A ──stdio────────────> MCP server: local filesystem   │
 │    └── MCP client B ──Streamable HTTP──> MCP server: remote Jira (OAuth)│
 └─────────────────────────────────────────────────────────────────────────┘
```

- The **host** is the AI application. It owns the model, the conversation and user consent.
- An **MCP client** is a connector inside the host, one per server, each holding its own connection.
- An **MCP server** is a program that exposes capabilities. It is *local* if the host launches it as a subprocess, *remote* if it is reached over HTTP.

MCP deliberately doesn't specify how the host uses the LLM. It only covers context exchange.

### Primitives: who controls what

A server can offer three kinds of capability, and the split follows who decides when each is used:

| Primitive | What it is | Controlled by | Example |
|---|---|---|---|
| **Tools** | Functions with a JSON Schema input | The **model** ("model-controlled") | `row_count(table)` |
| **Resources** | Read-only context addressed by URI | The **application** ("application-driven") | `schema://orders` attached to the prompt |
| **Prompts** | Reusable message templates | The **user** ("user-controlled") | A `/investigate` slash command |

Clients can offer features *to* servers as well. **Sampling** lets a server borrow the host's model to generate text. **Roots** tell a server which directories or URIs are in scope. **Elicitation** lets a server ask the *user* for input mid-call, either as a form or as an external URL for sensitive flows such as sign-in. The 2026-07-28 revision deprecates Roots and Sampling, plus server Logging, and keeps Elicitation (details below).

### The wire: JSON-RPC 2.0

Every MCP message is **JSON-RPC 2.0**, a tiny RPC convention. A *request* has an `id`, a `method` and `params`. A *response* echoes the `id` with a `result` or an `error`. A *notification* has no `id` and gets no reply. Here is the minimal server used for this section, written against the official Python SDK **(GA, v2.3.0 as of Oct 2026)**:

```python
from mcp.server import MCPServer   # v1 name: from mcp.server.fastmcp import FastMCP

mcp = MCPServer("warehouse")       # the server name clients see

@mcp.tool()
def row_count(table: str) -> int:
    """Return the number of rows in a warehouse table."""
    counts = {"orders": 1_204_331, "customers": 88_412}   # stand-in for a real query
    return counts.get(table, 0)

@mcp.resource("schema://{table}")
def table_schema(table: str) -> str:
    """Column definitions for a table, as read-only context."""
    return f"{table}: id BIGINT, created_at TIMESTAMP, ..."

@mcp.prompt()
def investigate(table: str) -> str:
    """A reusable prompt template the user can pick from a menu."""
    return f"Check {table} for duplicate ids and summarize what you find."

if __name__ == "__main__":
    mcp.run()                      # stdio by default; mcp.run(transport="streamable-http") to deploy
```

The type hints *are* the schema: `table: str` becomes the `inputSchema`, and the docstring becomes the description the model reads. SDK v2 renamed `FastMCP` to `MCPServer`, and the old import path is gone. Below is the raw exchange with this server over stdio, captured by writing JSON-RPC lines to its stdin and lightly trimmed. Note what is missing: there is no handshake before the first call.

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list",
 "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {},
                      "io.modelcontextprotocol/clientInfo": {"name": "probe", "version": "0.1"}}}}

{"jsonrpc": "2.0", "id": 1, "result": {
  "resultType": "complete",
  "tools": [{"name": "row_count",
             "description": "Return the number of rows in a warehouse table.",
             "inputSchema": {"type": "object",
                             "properties": {"table": {"title": "Table", "type": "string"}},
                             "required": ["table"]},
             "outputSchema": {"type": "object",
                              "properties": {"result": {"title": "Result", "type": "integer"}},
                              "required": ["result"]}}],
  "ttlMs": 0, "cacheScope": "private",
  "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "warehouse", "version": ""}}}}

{"jsonrpc": "2.0", "id": 2, "method": "tools/call",
 "params": {"name": "row_count", "arguments": {"table": "orders"},
            "_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                      "io.modelcontextprotocol/clientCapabilities": {}}}}

{"jsonrpc": "2.0", "id": 2, "result": {
  "resultType": "complete",
  "content": [{"type": "text", "text": "1204331"}],
  "structuredContent": {"result": 1204331},
  "isError": false}}
```

### From MCP to the model: the host's job

MCP doesn't replace tool use from [§10](10-tool-use.md). It *feeds* it. The host converts each MCP tool into a Messages API tool definition, runs the ordinary agent loop, and turns each `tool_use` block into a `tools/call`. This version was tested end to end against the SDK server above:

```python
import os
import anyio
from anthropic import AsyncAnthropic
from mcp import Client, StdioServerParameters

async def main():
    claude = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    server = StdioServerParameters(command="python", args=["server.py"])  # the host launches the server
    async with Client(server) as mcp:                       # one MCP client per server
        listed = await mcp.list_tools()                     # sends tools/list
        tools = [{"name": t.name, "description": t.description or "",
                  "input_schema": t.input_schema} for t in listed.tools]  # MCP tool -> Claude tool
        messages = [{"role": "user", "content": "How many rows are in the orders table?"}]
        while True:                                         # the ordinary agent loop from section 11
            reply = await claude.messages.create(model="claude-sonnet-5-5", max_tokens=16000,
                                                 tools=tools, messages=messages)
            messages.append({"role": "assistant", "content": reply.content})
            if reply.stop_reason != "tool_use":             # end_turn, max_tokens or refusal
                return print("".join(b.text for b in reply.content if b.type == "text"))
            results = []
            for block in reply.content:
                if block.type == "tool_use":                # the model proposes...
                    out = await mcp.call_tool(block.name, block.input)  # ...the host executes via tools/call
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": out.content[0].text, "is_error": out.is_error})
            messages.append({"role": "user", "content": results})

anyio.run(main)
```

For *remote* servers you can skip this glue. Anthropic's **MCP connector (Preview)** takes `mcp_servers=[{"type": "url", "url": ..., "name": ...}]` plus a matching `{"type": "mcp_toolset", "mcp_server_name": ...}` entry in `tools` (beta `mcp-client-2025-11-20`), and makes the MCP calls server-side. OpenAI's Responses API has a `{"type": "mcp", "server_label": ..., "server_url": ...}` tool, and Google ADK has MCP tool support.

### Transports: stdio vs Streamable HTTP

A **transport** defines how the JSON-RPC bytes move. The 2026-07-28 spec defines two standard transports:

- **stdio.** The host launches the server as a subprocess and exchanges newline-delimited JSON-RPC over its stdin and stdout. Credentials come from the environment, not OAuth. One consequence surprises people: **stdout is the wire.** A stray `print()` in a stdio server corrupts the protocol stream, so log to stderr.
- **Streamable HTTP.** Each message is an HTTP `POST` to one endpoint, such as `/mcp`. The reply is a JSON body or a stream scoped to that request, delivered as Server-Sent Events (SSE). The older HTTP+SSE transport was superseded in 2025-03-26 and is now formally deprecated.

### The 2026-07-28 revision

This was the largest revision since launch, with breaking changes. Everything below is checked against the spec changelog and the release-candidate post. The RC was locked May 21, 2026, and the final spec was published July 28, 2026 **(GA)**.

**A stateless core.** In 2025-11-25, a client opened with an `initialize` handshake, and over HTTP the server issued an `Mcp-Session-Id` that pinned the client to one instance. Both are gone. Every request carries its version and capabilities in `_meta`, as in the capture above, and a new `server/discover` method returns server capabilities on demand. Any instance can serve any request, so a remote server can sit behind a plain round-robin load balancer, the familiar move from sticky sessions to stateless services. Applications can still keep state: a tool mints an explicit handle, such as a `basket_id`, that the model passes back as an argument, so the state is visible to the model instead of hidden in transport metadata.

**Servers no longer send requests to clients.** Sampling, roots and elicitation used to be server-initiated requests over a held-open stream. Under **Multi Round-Trip Requests (MRTR)**, a server that needs input returns `"resultType": "input_required"` with `inputRequests` and an opaque `requestState`. The client *retries the original call* with `inputResponses` and a new JSON-RPC `id`. Because everything is in the payload, any instance can handle the retry, like a continuation token in a paginated REST API.

**Routable, cacheable, traceable.** HTTP requests carry `Mcp-Method` and `Mcp-Name` headers so gateways can route without parsing bodies. List results carry `ttlMs` and `cacheScope`, modeled on HTTP `Cache-Control`. Servers SHOULD list tools in a deterministic order, explicitly to improve prompt-cache hit rates (P10). And W3C trace context in `_meta` lets one OpenTelemetry trace follow a call from host to server ([§27](27-observability.md)).

**An extensions framework.** Extensions have reverse-DNS IDs, are negotiated through an `extensions` map in capabilities, are always opt-in, and are versioned independently of the spec. The official ones are:
- **Tasks**, for long-running work. A server can answer `tools/call` with a task handle that the client drives with `tasks/get` (polling), `tasks/update` (mid-flight input) and `tasks/cancel`. Tasks were experimental core in 2025-11-25 and were redesigned as an extension.
- **MCP Apps.** A tool declares a UI resource (`_meta.ui.resourceUri`, a `ui://` URI) that the host renders as HTML in a sandboxed iframe. The UI talks back over the same JSON-RPC, so its actions pass the same consent path as tool calls ([§35](35-ai-ux.md)).
- **Skills over MCP**, which serves Agent Skills from servers ([§18](18-skills.md)). There are also authorization extensions, such as OAuth client credentials.

**Deprecations under a formal lifecycle.** Features move from Active to Deprecated to Removed, with at least twelve months before any removal. This release deprecates:
- **Roots.** Pass paths as tool parameters or config.
- **Sampling.** Call an LLM provider API directly.
- **Logging.** Use stderr or OpenTelemetry.
- The old HTTP+SSE transport.
- Dynamic Client Registration.

The Python SDK v2 (2.0.0, July 28, 2026) speaks 2026-07-28 and still serves older clients.

### Authorization, briefly

For HTTP transports, MCP builds on **OAuth 2.1**:
- The MCP server is an OAuth *resource server* and the client an OAuth *client*. A separate *authorization server* signs the user in and issues tokens.
- The client finds that server through the MCP server's **Protected Resource Metadata** (RFC 9728), uses PKCE, and names its target with a **resource indicator** (RFC 8707). Servers must reject tokens not issued for them as the audience.
- **Token passthrough**, forwarding the client's token to an upstream API, is forbidden. It invites the confused-deputy problem, where a server is tricked into using its authority for someone else.
- 2026-07-28 adds mandatory `iss` validation (RFC 9207) against mix-up attacks, and prefers **Client ID Metadata Documents** for client registration.

Who the agent acts *as* is covered in [§33](33-agent-identity.md).

### Security risks

Every risk below follows from P9: tool metadata and results enter the same channel as instructions. The spec says tools "represent arbitrary code execution" and that annotations are untrusted unless they come from a trusted server.

- **Tool poisoning.** Invariant Labs (Apr 1, 2025) hid instructions in a harmless-looking tool's description. The model read `~/.ssh/id_rsa` and `~/.cursor/mcp.json` and smuggled them out through a tool parameter, behind a simplified confirmation dialog.
- **Rug pulls.** A server changes a description *after* approval, so approving at install time proves nothing about tomorrow's `tools/list`.
- **Tool shadowing.** A malicious server's description changes how the agent uses a *trusted* server's tools, because all descriptions share one context.
- **Over-broad servers.** A token that can read every repository or write to production turns any injection into a breach. Local stdio servers are arbitrary code running with your privileges.

The mitigations are least privilege, not prompt pleading. Scope tokens narrowly, allowlist servers and tools, pin versions and hash tool definitions (re-approve on change), confirm writes with a human, and sandbox local servers ([§32](32-security-guardrails.md)).

### MCP vs plain tool use

MCP is a **distribution and interoperability layer**, not a better way to call functions. Inside one application with a handful of tools you own, plain tool definitions ([§10](10-tool-use.md)) are simpler: no extra process, no JSON-RPC, no second auth system. MCP pays off when tools serve several hosts, when third parties maintain them, when users bring their own, or when an organization wants one governed catalog.

### The context cost of many tools

Each connected tool's name, description and schema are injected into *every* request. In Anthropic's example, five servers (GitHub, Slack, Sentry, Grafana, Splunk) expose 58 tools worth about 55K tokens "before the conversation even starts", and internally they saw 134K tokens of definitions before optimization. Similar names such as `notification-send-user` and `notification-send-channel` also cause wrong picks (P3). There are two mitigations. **Tool search** (`defer_loading: true`, loaded on demand) gave an 85% reduction. **Code execution with MCP**, which exposes tools as code files the agent imports, cut one workflow from 150,000 to 2,000 tokens.

### A2A: agent to agent

MCP connects an agent to a **tool**, a function that is called and returns. A2A connects an agent to another **agent**, possibly another vendor's on another framework, which stays deliberately **opaque**: peers don't share prompts, plans or tools. The spec has four parts:

- **Agent Card.** A JSON document, conventionally at `https://{domain}/.well-known/agent-card.json`. It lists `supportedInterfaces` (URL, protocol binding, version), `capabilities` (`streaming`, `pushNotifications`), `securitySchemes` (such as OAuth or OpenID Connect) and **skills**, the advertised task types with examples. Cards can be **signed** with JWS so clients can verify the publisher. Think of an OpenAPI document plus a service-registry entry.
- **Tasks.** `SendMessage` returns a direct `Message` or a `Task` that moves through states:
  - working: `TASK_STATE_SUBMITTED`, `TASK_STATE_WORKING`
  - interrupted: `TASK_STATE_INPUT_REQUIRED`, `TASK_STATE_AUTH_REQUIRED`
  - terminal: `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`, `TASK_STATE_REJECTED`

  Outputs arrive as **artifacts**, and a `contextId` groups related tasks. If you have polled a Databricks job run's state, the shape is familiar.
- **Updates.** Poll with `GetTask`, stream over SSE (`SendStreamingMessage`, `SubscribeToTask`), or register a webhook for **push notifications**, which suit tasks that run for hours.
- **Protocol bindings.** The same operations run over JSON-RPC 2.0, gRPC and HTTP+JSON/REST.

The A2A spec states the division of labor: a client agent delegates to a server agent, which "might use MCP to interact with several underlying tools". In short, **MCP is agent↔tool (vertical) and A2A is agent↔agent (horizontal)**. Use A2A at organizational or vendor boundaries. Inside one codebase, the patterns of [§13](13-multi-agent.md) need no wire protocol.

### Governance and status in 2026

- **MCP** is an AAIF project. AAIF launched December 9, 2025, co-founded by Anthropic, Block and OpenAI, with MCP, goose and AGENTS.md as its founding projects. MCP's governance stayed with its maintainers and the SEP (Specification Enhancement Proposal) process, and standards-track SEPs now need a conformance test to reach Final. Current spec: 2026-07-28 **(GA)**.
- **A2A** spec v1.0.0 **(GA)** was accepted as an AAIF Growth Stage project (announced Aug 27, 2026). The project claims backing from over 150 organizations and native support in Google Cloud, AWS Bedrock AgentCore Runtime and Azure AI Foundry. Production cross-vendor use is less visible than MCP's.
- One neutral home for both protocols, alongside agentgateway, lowers the risk of a vendor fork.

## Comparison

| | Plain tool use | MCP | A2A |
|---|---|---|---|
| Connects | One app to its own functions | Any host to any tool or data server | Any agent to any other agent |
| Unit of work | A function call | A function call (or a task, via the extension) | A long-running, multi-turn task |
| Discovery | Hard-coded in the app | `tools/list` at runtime | Agent Card at a well-known URL |
| State | In your app | Stateless protocol; explicit handles | Task and context IDs, lifecycle states |
| Strength | Simplest and fastest | N+M ecosystem, shared auth and governance | Opaque, cross-vendor delegation |
| Weakness | N×M if you have many apps | Context cost; supply-chain risk | Heavier; adoption still forming |
| Choose when | One app, few tools you own | Tools shared across hosts or teams | Delegating to agents you don't own |

| Transport | How it works | Auth | Choose when |
|---|---|---|---|
| stdio | Host spawns the server and exchanges newline-delimited JSON-RPC over stdin and stdout | Environment variables | Local tools, developer machines |
| Streamable HTTP | `POST` per message, JSON or SSE reply, routing headers | OAuth 2.1 | Remote, shared, multi-tenant servers |

## What it didn't solve

Protocols made plugging in a tool cheap, so people plug in many. Every connected server's definitions, and every tool result, land in the context window. A long agent run accumulates thousands of tokens of transcripts, file contents and outputs. Because context is a finite attention budget that rots as it grows (P3), the agent gets slower, costlier and less accurate the longer it works. Deciding what goes into the window, and what stays out, became its own discipline.

→ Next: [§16 Context Engineering](16-context-engineering.md)

## Check your understanding

**Q: Why does MCP turn N×M integrations into N+M, and what does it leave unstandardized?**

Each host implements an MCP client once and each system implements an MCP server once, so any host can discover and call any server through the same JSON-RPC messages: N+M implementations instead of N×M. It standardizes discovery, invocation, transports and auth. It does not standardize whether a tool is well designed, what its description makes the model do, or what it costs in context. A bad tool behind MCP is still a bad tool, only easier to install.

**Q: Why did the 2026-07-28 revision remove the initialize handshake and the session, and how does a server keep state now?**

Sessions pinned each client to the instance that issued its `Mcp-Session-Id`, which forced sticky routing and shared session stores and made horizontal scaling awkward. Now every request carries its version and capabilities in `_meta`, so any instance can serve it, and mid-call questions use multi round-trip results whose `requestState` travels in the payload. A server that needs cross-call state mints an explicit handle that the model passes back as an argument, so state management moves into tool design.

**Q: What would happen if you connected 15 MCP servers exposing about 10 tools each to one agent?**

About 150 tool definitions would be injected into every request, plausibly tens of thousands of tokens, before the user says anything. That raises cost and latency (P10), dilutes attention (P3), and increases wrong picks between similarly named tools. The fixes are to load fewer tools per task, defer them behind tool search, or let the agent call tools through code. If you really need only three tools, connect only those.

**Q: MCP vs plain tool use: when is a protocol overkill?**

Plain tool use is a JSON Schema in your request and a function in your process. MCP adds a separate server process or HTTP service, JSON-RPC, version negotiation and often OAuth. That overhead buys reuse across hosts, third-party maintenance and central governance. For one application with a few tools you own, especially on a latency-sensitive path, it buys nothing, so define the tools directly.

**Q: Why is tool poisoning possible even when the user approves every tool call?**

The attack lives in the tool's *description*, which the model reads as context (P9), not in the visible call. A poisoned description can tell the model to read a secret file and slip it into an innocuous-looking parameter, and confirmation dialogs often hide full arguments. Rug pulls make it worse, because the description can change after approval. The defense is least privilege, meaning that the server and its tokens can't reach the secrets, plus pinned, re-reviewed tool definitions. Better prompting is not a defense.

**Q: Why not just wrap a remote agent as an MCP tool instead of using A2A?**

An MCP tool models a function call: a request with a schema and a result. A remote agent may run for hours, ask for input or authentication mid-task, stream partial artifacts and keep its internals opaque, which A2A models with task states, push notifications and signed Agent Cards. Wrapping works for a quick, stateless sub-agent, and MCP's Tasks extension narrows the gap. For long-running delegation across organizations, A2A fits better.

**Q: What would happen if a stdio MCP server writes debug output with `print()`?**

On stdio, stdout *is* the protocol channel, and every line is expected to be a JSON-RPC message. A stray print injects non-JSON bytes, so the client fails to parse responses and the connection breaks in confusing ways. Log to stderr or OpenTelemetry, which is also the spec's replacement for deprecated Logging. Streamable HTTP servers don't have this problem, because the HTTP body is separate from process output.

## Takeaways

- MCP and A2A apply P11: standard interfaces turn N×M custom integrations into N+M.
- MCP has hosts, clients and servers. Servers offer tools (model-controlled), resources (application-driven) and prompts (user-controlled), all over JSON-RPC 2.0.
- MCP feeds tool use rather than replacing it. The host maps `tools/list` into tool definitions and `tool_use` into `tools/call` (P6).
- The 2026-07-28 spec is stateless: no handshake or session, `_meta` on every request, multi round-trip results, Tasks and MCP Apps as extensions, and Roots, Sampling and Logging deprecated.
- Remote MCP uses OAuth 2.1 with audience-bound tokens, and token passthrough is forbidden.
- Tool descriptions are untrusted instructions (P9). Defend against poisoning and rug pulls with least privilege and pinned definitions.
- Every connected tool costs context on every request. Load fewer, defer them, or call them through code.
- MCP is agent↔tool and A2A is agent↔agent, the latter with Agent Cards, task lifecycles and push notifications. Both are now governed by the Linux Foundation's AAIF.

## Sources

- Anthropic, "Introducing the Model Context Protocol" (Nov 25, 2024): https://www.anthropic.com/news/model-context-protocol
- MCP specification 2026-07-28: https://modelcontextprotocol.io/specification/2026-07-28
- MCP 2026-07-28 changelog: https://modelcontextprotocol.io/specification/2026-07-28/changelog
- MCP base protocol (statelessness, `_meta`): https://modelcontextprotocol.io/specification/2026-07-28/basic
- MCP transports: https://modelcontextprotocol.io/specification/2026-07-28/basic/transports
- MCP tools: https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- MCP authorization: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- MCP security best practices: https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices
- MCP blog, "The 2026-07-28 MCP Specification Release Candidate": https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- MCP extensions overview: https://modelcontextprotocol.io/extensions/overview and MCP Apps: https://modelcontextprotocol.io/extensions/apps/overview
- MCP architecture and intro: https://modelcontextprotocol.io/docs/learn/architecture and https://modelcontextprotocol.io/docs/getting-started/intro
- MCP Python SDK v2 (what's new, running a server): https://py.sdk.modelcontextprotocol.io/whats-new/ and https://py.sdk.modelcontextprotocol.io/run/
- Anthropic, "Donating the Model Context Protocol and establishing the Agentic AI Foundation" (Dec 9, 2025): https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation
- Linux Foundation AAIF announcement (Dec 9, 2025): https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation
- AAIF: https://aaif.io/about/
- Anthropic, "Introducing advanced tool use" (tool search): https://www.anthropic.com/engineering/advanced-tool-use
- Anthropic, "Code execution with MCP" (Nov 4, 2025): https://www.anthropic.com/engineering/code-execution-with-mcp
- Invariant Labs, "MCP Security Notification: Tool Poisoning Attacks" (Apr 1, 2025): https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
- OpenAI, MCP and connectors in the Responses API: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- A2A specification v1.0: https://a2a-protocol.org/latest/specification/
- Google, "Announcing the Agent2Agent Protocol (A2A)" (Apr 9, 2025): https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- Linux Foundation, A2A project launch (Jun 23, 2025): https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents
- A2A, "A New Chapter for A2A: Joining the Agentic AI Foundation" (Aug 27, 2026): https://a2a-protocol.org/latest/blog/2026/08/27/a-new-chapter-for-a2a-joining-the-agentic-ai-foundation/
