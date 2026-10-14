# 33. Agent Identity and Authorization

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

In 2025–2026, agents began acting across SaaS systems on users' behalf: reading a CRM, filing Jira tickets, querying a warehouse, calling other companies' agents. MCP added OAuth-based authorization in its 2025-03-26 revision and has tightened it in every revision since. [§32](32-security-guardrails.md) showed that agent security rests on least privilege, then asked *whose* privilege. This section answers with identity: who the agent is, whom it acts for, what it may do, and how you prove it afterwards. P9 sets the rules for credentials, P6 says where they live, and P11 explains why the answer is OAuth rather than something new.

## Why this exists

Before agents, identity came in two shapes. **Humans** signed in through single sign-on (SSO), one login at a corporate identity provider (IdP) such as Okta or Microsoft Entra. **Services** ran as service accounts with fixed permissions. An agent fits neither. It is software, yet it acts on a person's request, chooses actions probabilistically (P4), and reads untrusted text that can redirect it (P9). The first shortcuts each break predictably:

- **Give the agent the user's credentials** (a password or personal API key). The agent now has *all* of the user's power, logs can't tell the agent from the person, and you can't revoke one without the other.
- **Run the agent as a shared service account with broad access.** Any user can now get the agent to do what they personally can't, by asking or by planting a document it reads. That is a **confused deputy**: a program with authority tricked into using it for someone else. OWASP's agentic list calls the missing distinction an "attribution gap" (ASI03).
- **Paste a token into the prompt.** Whatever is in context can be repeated, logged or exfiltrated by an injection (P9).

What you need instead: an identity for the agent, a record of whose behalf it acts on, credentials narrowed to the task and kept out of the context window, and an audit trail naming both parties.

## How it works (under the hood)

### 1. Who is the agent? Delegated vs autonomous authority

A **principal** is anything that can be authenticated and granted permissions: a user, a service account, a workload. An agent can stand in three relations to principals:

- **Delegated authority (on behalf of a user).** The agent has its own client identity, and the user grants it a subset of their permissions. Its effective rights are the *intersection* of what the user may do and what the user granted (the scopes). This is the right model whenever the agent touches a user's data. The IETF WIMSE draft on agent identity (Sep 2026) puts both names in the access token: the agent in `client_id` and the user in `sub`.
- **Autonomous authority (its own principal).** The agent runs as a service account or workload identity, with permissions granted directly. This fits scheduled or event-driven work with no user in the loop, such as a nightly triage agent. Keep those permissions narrow, because no user's rights limit them.
- **Impersonation** (the anti-pattern). The agent presents the user's own credentials, so downstream systems see only the user.

```text
  delegated access token (JWT claims)        autonomous access token
  ┌────────────────────────────────────────┐  ┌───────────────────────────────────┐
  │ sub:       alice@corp.example   ◄ user │  │ sub:       agent:nightly-triage   │
  │ client_id: agent:invoice-bot   ◄ agent │  │ client_id: agent:nightly-triage   │
  │ aud:       https://billing.example.com │  │ aud:       https://jira.example   │
  │ scope:     invoices:read               │  │ scope:     issues:comment         │
  │ exp:       now + 5 min                 │  │ exp:       now + 5 min            │
  └────────────────────────────────────────┘  └───────────────────────────────────┘
  effective rights = alice's rights ∩ scope     effective rights = scope
```

### 2. OAuth 2.1, briefly

OAuth is the standard for **delegated authorization**: letting a client use an API on a user's behalf without seeing the user's password. Its four roles are the **resource owner** (the user), the **client** (your agent application), the **authorization server** (AS), which signs the user in, asks consent and issues tokens, and the **resource server**, the API that accepts the tokens. Four terms carry most of the meaning:

- **Access token:** a short-lived credential sent on every request (`Authorization: Bearer ...`). Whoever holds it can use it.
- **Refresh token:** a longer-lived credential the client trades for fresh access tokens. Keep it secret; it never goes to resource servers.
- **Scope:** a named permission, such as `invoices:read`.
- **Audience:** the resource server a token is valid for (the `aud` claim). RFC 8707's `resource` parameter asks the AS to bind the token to one audience.

In the **authorization code flow with PKCE**, used when a user is at a browser:

1. The client makes a random **code verifier** and sends only its SHA-256 hash, the **code challenge**, with the authorization request.
2. The user logs in at the AS and consents.
3. The AS redirects back with a short-lived **authorization code**.
4. The client redeems the code *plus the verifier*, and the AS checks the verifier's hash against the challenge.

**PKCE** (Proof Key for Code Exchange, RFC 7636) means an intercepted code is useless without the verifier, which never left the client. **OAuth 2.1**, still an IETF draft (revision 16, Sep 2026), consolidates a decade of OAuth 2.0 practice. PKCE is required and its `plain` method removed, the implicit and password grants are gone, redirect URIs must match exactly, bearer tokens may not appear in query strings, and public clients' refresh tokens must be sender-constrained or one-time use. An agent acting as itself uses the **client credentials grant** instead, with no user and no browser.

```python
import base64, hashlib, secrets
from urllib.parse import urlencode

def s256(verifier: str) -> str:                   # code_challenge = BASE64URL(SHA256(verifier))
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")  # no "=" padding

# RFC 7636 Appendix B test vector: an implementation must reproduce it exactly.
assert s256("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == \
    "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

CLIENT_ID = "https://agent.example.com/oauth/client.json"  # a Client ID Metadata Document URL
RESOURCE = "https://billing.example.com/mcp"     # RFC 8707: the server the token is for

verifier = secrets.token_urlsafe(48)              # 64 chars of [A-Za-z0-9_-]; spec allows 43-128
state = secrets.token_urlsafe(16)                 # CSRF check when the redirect comes back
# Keep verifier, state and the AS's validated issuer together, client-side only.
authorize_url = "https://auth.example.com/authorize?" + urlencode({
    "response_type": "code", "client_id": CLIENT_ID,
    "redirect_uri": "http://127.0.0.1:8765/callback",
    "scope": "invoices:read",                     # least privilege; step up later if needed
    "state": state,
    "code_challenge": s256(verifier), "code_challenge_method": "S256",
    "resource": RESOURCE,
})
# After the redirect (check state, and iss per RFC 9207), POST this to the token endpoint.
# OAuth 2.0 servers also expect redirect_uri here; the OAuth 2.1 draft drops it.
token_request = {
    "grant_type": "authorization_code", "code": "<code from the redirect>",
    "code_verifier": verifier,                    # proves the redeemer started this flow
    "client_id": CLIENT_ID, "resource": RESOURCE,
}
print(authorize_url)
```

### 3. MCP authorization in the 2026-07-28 spec

MCP authorization is optional and covers HTTP transports. A stdio server "SHOULD NOT follow this specification" and takes credentials from its environment. Where it applies **(GA)**, the MCP server is an OAuth 2.1 resource server and the MCP client an OAuth client, with a separate or co-hosted authorization server.

**Discovery.** Servers MUST publish **Protected Resource Metadata** (RFC 9728), a JSON document at a well-known URL listing their `authorization_servers`. Clients then fetch the AS's metadata (RFC 8414 or OpenID Connect Discovery) and MUST check that its `issuer` matches.

```text
MCP client                     MCP server (resource server)          Authorization server
  │ POST /mcp (no token) ──────────►│
  │◄─ 401 WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource",
  │                                scope="files:read"
  │ GET protected resource metadata ►│ → {"authorization_servers": ["https://auth…"]}
  │ GET /.well-known/oauth-authorization-server ─────────────────────────►│ check issuer, PKCE
  │ browser → /authorize ?client_id=<CIMD URL> &code_challenge=… &resource=<server URI> ►│
  │◄──────────────────────────────── code + iss  (iss must equal the recorded issuer) ───│
  │ POST /token  code + code_verifier + resource ────────────────────────►│
  │◄──────────────────────────────── access_token (aud = this MCP server) ───────────────│
  │ POST /mcp  Authorization: Bearer … ►│ validate audience + scope → 200, or 403 insufficient_scope
```

**Client registration.** An AS must know a client before issuing tokens. In order of preference:
1. **Pre-registration**, when client and server already have a relationship.
2. **Client ID Metadata Documents (CIMD)**, a SHOULD. The `client_id` is an HTTPS URL pointing to a JSON document with the client's name and redirect URIs. The AS fetches it, checks the redirect URI, and may apply domain trust policies. It fits MCP's common case of a client and server that have never met.
3. **Dynamic Client Registration** (RFC 7591), deprecated in 2026-07-28 and "retained for backwards compatibility".
4. Asking the user for client details.

**Hard requirements.** PKCE with `S256`, and clients MUST refuse an AS whose metadata lacks `code_challenge_methods_supported`. The `resource` parameter, set to the server's canonical URI, goes in both the authorization and token requests. The token travels in the `Authorization` header of every request, never the query string. Servers MUST validate that tokens were issued "specifically for them as the intended audience". New in 2026-07-28, clients validate the `iss` parameter (RFC 9207), which defeats **mix-up attacks** where a malicious AS gets a client to send it a code from an honest one, and they key stored credentials to the issuing AS.

**Step-up authorization.** Start with minimal scopes. When a call needs more, the server answers `403` with `error="insufficient_scope"` and the required scopes, and the client re-authorizes with the union of old and new scopes. The security guide warns against wildcard scopes and against treating a token's scopes as sufficient "without server-side authorization logic."

**Extensions.** **OAuth Client Credentials** (a draft) covers machine-to-machine access, preferring signed JWT assertions (RFC 7523) to client secrets. **Enterprise-Managed Authorization** (stable) hands the decision to the company's IdP, as described below.

### 4. Token passthrough and the confused deputy

**Token passthrough** is an MCP server accepting a token not issued to it and forwarding it downstream. Servers "MUST NOT accept or transit any other tokens." The security guide's reasons: it bypasses controls such as rate limits that depend on the token's audience, logs show the wrong identity, and a stolen token turns the server into an exfiltration proxy. When an MCP server calls GitHub, it should act as GitHub's OAuth client with a *separate* token from GitHub's authorization server.

The spec also documents a confused-deputy attack on **MCP proxy servers** that use one static client ID with a third-party AS. Once a user has consented, a consent cookie lets an attacker's newly registered client, with its malicious redirect URI, skip the consent screen and receive the code. The fix is per-client consent at the proxy.

The same problem appears whenever a high-privilege agent trusts a low-privilege one. In OWASP's ASI03 example, an email-sorting agent relays a forged instruction to a finance agent, which pays because it trusts "an internal agent". Authorize each hop against the *original user's* identity. **OAuth Token Exchange** (RFC 8693) swaps an incoming token for a narrower one for the next hop, and its `act` (actor) claim records who acts for whom.

### 5. Scoped, short-lived credentials that never enter context

The P9 rule for secrets: **anything in the context window can leak**, through injection, logs or the model repeating it. So credentials stay in the harness (P6), attached when a tool executes and never shown to the model. The **broker** below holds refresh tokens from a **vault** (a secrets manager), mints audience-bound, minimum-scope access tokens per tool, caches them for minutes, and returns only data. The `tool_use` dict mirrors the Messages API block ([§10](10-tool-use.md)), and the return value becomes a `tool_result`.

```python
import json, secrets, time

# Per-tool least privilege: each tool maps to one audience (resource) and its minimum scope.
TOOL_GRANTS = {
    "list_invoices":  ("https://billing.example.com", "invoices:read"),
    "refund_invoice": ("https://billing.example.com", "invoices:refund"),
}
STEP_UP = {"refund_invoice"}                     # needs a fresh human yes on every call

class CredentialBroker:
    """Runs in the harness. Holds refresh tokens (from a vault) and mints short-lived,
    audience-bound access tokens per (user, tool). The model never sees any of them."""
    def __init__(self, agent_id: str, vault: dict):
        self.agent_id, self.vault, self.cache = agent_id, vault, {}

    def post_token_endpoint(self, form: dict) -> dict:  # stub for an HTTPS POST to the AS
        return {"access_token": "at_" + secrets.token_urlsafe(16), "expires_in": 300}

    def token_for(self, user: str, tool: str) -> str:
        audience, scope = TOOL_GRANTS[tool]
        hit = self.cache.get((user, scope))
        if hit and hit[1] - time.time() > 30:     # reuse until 30 s before expiry
            return hit[0]
        resp = self.post_token_endpoint({"grant_type": "refresh_token",
            "refresh_token": self.vault[user],    # the user's grant, stored outside context
            "scope": scope, "resource": audience})  # RFC 8707: token valid only at audience
        self.cache[(user, scope)] = (resp["access_token"], time.time() + resp["expires_in"])
        return resp["access_token"]

def run_tool(broker, user, tool_use: dict, approve, call_api, audit: list) -> str:
    name, args = tool_use["name"], tool_use["input"]   # what the model asked for (P6)
    if name not in TOOL_GRANTS:
        return "error: unknown tool"
    if name in STEP_UP and not approve(user, name, args):
        return "refused: the user did not approve this action"
    token = broker.token_for(user, name)           # lives only in this stack frame
    result = call_api(name, args, headers={"Authorization": f"Bearer {token}"})
    audit.append({"ts": time.time(), "agent": broker.agent_id, "on_behalf_of": user,
                  "tool": name, "args": args, "scope": TOOL_GRANTS[name][1]})
    return json.dumps(result)                      # only data goes back into the context
```

Hosted runtimes now do this for you. In **Claude Managed Agents** **(Preview)**, vault credentials never enter the sandbox: MCP calls pass through a proxy that adds the OAuth token, and environment-variable secrets appear in the sandbox as opaque placeholders replaced at egress, only on requests to allowed hosts.

**Workload identity** removes even the refresh token. The platform a workload runs on (Kubernetes, a cloud VM, a CI runner) issues it a short-lived signed identity token, such as an OIDC JWT or a SPIFFE identity document, which it exchanges for a short-lived access token. No long-lived secret is stored anywhere.
- **OpenAI's workload identity federation** maps a trusted provider's token claims to a service account. Sources include Kubernetes, AWS, Azure, Google Cloud, GitHub Actions and SPIFFE, with X.509 certificates in beta. No refresh token is issued: "To renew, repeat the exchange."
- **Anthropic's Workload Identity Federation** **(GA)** uses service accounts and federation rules. Its identity-backed API keys stop working when their user or service account is removed.
- **Cloud IAM** does the same within each cloud: AWS IAM roles, Google Cloud workload identity federation, Azure managed identities.

### 6. Per-tool authorization and step-up approval

Authorize in code at the tool layer, as the broker does, and again at the resource server, which checks the token *and* applies its own policy, such as row-level security. Two kinds of "step-up" are easy to confuse. **Step-up authorization** gets *more scope* from the AS, as with MCP's `insufficient_scope` challenge. **Step-up approval** has a human confirm *one specific action*, like the broker's `STEP_UP` set or `always_ask` tools ([§20](20-agent-runtime.md)).

The WIMSE draft says confirmations in the agent's own UI "do not by themselves constitute authorization". It suggests binding them to an AS event, for example with OpenID **CIBA** (Client-Initiated Backchannel Authentication), which pushes an approval request to the user's phone. Short-lived tokens also limit **authorization drift**, OWASP's time-of-check to time-of-use case: a user's spending limit is cut mid-workflow while the agent carries on with its original token.

### 7. Audit: who did what, on whose behalf

Each action's record names the **actor** (agent identity and version), the **principal** (the user, from `sub`), the delegation chain (`act` claims, parent agents), the tool, arguments and scopes, the decision and approver, the trace ID ([§27](27-observability.md)) and the context sources ([§32](32-security-guardrails.md)). Because the agent has its own `client_id`, a SaaS audit log can show "Alice via invoice-bot" rather than just "Alice". Token passthrough and impersonation erase exactly that distinction.

### 8. Agent-to-agent authentication

A2A states that "identity information is handled at the protocol layer, not within A2A semantics". An Agent Card declares `securitySchemes` (API key, HTTP bearer, OAuth 2.0, OpenID Connect or mutual TLS). Clients get credentials out of band, and servers MUST authenticate every request, then authorize by skill, action or scope. Mid-task, an agent can enter `TASK_STATE_AUTH_REQUIRED`, and the client may pass that request up its own chain.

**Agent Card signing** uses JWS (RFC 7515) over the card canonicalized with JCS (RFC 8785), excluding the `signatures` field itself. A valid signature proves who published the card and that it wasn't altered, not that the agent behaves as described. OWASP's "forged agent persona" scenario (ASI03), a fake "Admin Helper" card in an internal registry, is why you verify signatures and allow-list publishers. For workload-to-workload calls, the WIMSE drafts add mTLS, proof tokens and HTTP message signatures.

### 9. Emerging standards (drafts, not settled)

"Agent identity" is a label still forming, and most of the work applies existing OAuth and workload-identity standards rather than inventing new ones. As of October 2026:

- **IETF WIMSE** (Workload Identity in Multi System Environments) working group: *AI Identity Management System* (`draft-ietf-wimse-aims-00`, Sep 15, 2026), by authors from Defakto, AWS, Zscaler, Ping Identity, OpenAI and Okta, replacing `draft-klrc-aiagent-auth`. Its thesis is "agents are workloads": use SPIFFE identifiers, OAuth, transaction tokens and CIBA, and define no new protocol. It is an informational working-group draft.
- **IETF OAuth working group:** *Identity Assertion JWT Authorization Grant* (ID-JAG, rev 04), the basis of MCP's Enterprise-Managed Authorization; *Identity and Authorization Chaining Across Domains* (rev 17, in the RFC Editor queue); *Transaction Tokens* (rev 11); and OAuth 2.1 itself (rev 16).
- **Individual drafts**, such as *On-Behalf-Of User Authorization for AI Agents* (rev 02, Feb 2026), are proposals, not adopted work.
- **OpenID Foundation:** *Identity Management for Agentic AI* (Oct 7, 2025) finds existing standards cover agents inside one organization or on a user's own data, and flags recursive delegation, consent fatigue and fragmented agent identities as open gaps.

### 10. Enterprise rollout

- **SSO and central policy.** With MCP's **Enterprise-Managed Authorization**, employees sign in once through the corporate IdP. The client exchanges that identity assertion for an ID-JAG, which the MCP server's AS accepts. The IdP decides which servers each employee can reach, and offboarding is one revocation "across all MCP clients".
- **RBAC for agents.** RBAC (role-based access control) grants permissions to roles, not individuals. Give each agent its own principal with roles, and give users roles that govern which agents and tools they may use. OpenAI's federation guidance generalizes: one principal per workload, separate production from non-production, match claims exactly, keep token lifetimes short.
- **Spend controls by identity:** per-agent and per-user budgets and session caps ([§20](20-agent-runtime.md)), which also make chargeback possible ([§30](30-cost-latency-reliability.md)).
- **Lifecycle:** every agent identity needs a named human owner, access reviews and decommissioning, so orphaned agents don't keep live credentials.

### 11. The data-engineering analogy

You have solved this problem before, in the warehouse. Databricks Apps offers agents two modes. **App authorization** uses an automatically created service principal, and "all users who interact with the app share the same permissions". **User authorization**, formerly on-behalf-of (OBO), runs as the requesting user, for "user-specific permissions, audit trails, or fine-grained access control with Unity Catalog". That is autonomous vs delegated authority. Snowflake's **owner's-rights** stored procedures are deputies with their own authority, which become confused deputies if callers control their inputs; **caller's-rights** procedures run with the caller's privileges.

**Row-level security is the last line.** Row filters and column masks work only if the query carries the real user's identity. A delegated token lets your existing RLS confine a hijacked agent to what that user could see. A god-mode service account bypasses all of it, the permission leak [§9](09-rag.md) warned about.

### Failure modes

- A shared admin service account, making every user an admin through the prompt.
- Token passthrough, or skipping audience checks.
- Long-lived keys in prompts, sandboxes or readable environment variables.
- Wildcard scopes requested up front.
- Tokens cached across users or tasks (ASI03).
- A UI click treated as authorization; unverified Agent Cards; ownerless agent identities.

## Comparison

**Whose authority does the agent use?**

| Model | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Impersonation | Agent uses the user's own credentials | Trivial to build | Full user power; logs can't tell agent from user; no separate revocation | Never in production |
| Delegated (OBO) | Agent's own `client_id`, user in `sub`, scoped token | Bounded by user's rights; RLS and audit work | Needs consent flows and refresh handling | Agent acts on a user's data |
| Own principal | Service account or workload identity | No user needed; simple ops | Nothing limits it but its grants; confused-deputy risk if many users drive it | Scheduled or system jobs |
| Enterprise-managed | IdP issues ID-JAG per policy; AS exchanges it for a token | Central policy and revocation; SSO | IdP and client support still rolling out | Company-wide agent and MCP rollouts |

**MCP client registration (2026-07-28)**

| Mechanism | How it works | Strength | Weakness | Choose when |
|---|---|---|---|---|
| Pre-registration | Client ID issued out of band | Simple, explicit trust | Doesn't scale to unknown servers | Known client–server pairs |
| Client ID Metadata Document | `client_id` is an HTTPS URL to a JSON document the AS fetches | No prior relationship; AS can apply domain trust policy | AS must guard against SSRF; localhost redirect impersonation | Default for open ecosystems |
| Dynamic Client Registration | Client POSTs metadata to a registration endpoint | Widely implemented | Deprecated in MCP; part of the documented proxy consent attack | Only for older authorization servers |

**Credentials**

| Type | Lifetime | Where it lives | Risk if leaked | Choose when |
|---|---|---|---|---|
| Static API key | Until rotated | Env var, config | High: broad and long-lived | Local development only |
| OAuth access + refresh tokens | Minutes + days | Vault; broker in harness | Bounded by scope, audience and expiry | User-delegated access |
| Workload identity federation | Minutes; no refresh token | Platform-issued, nothing stored | Low: short-lived, claim-bound | Production services, CI, scheduled agents |
| Vault-injected at egress | Managed by platform | Outside the sandbox | Not readable by agent code | Hosted agent runtimes |

## What it didn't solve

Identity, scopes and audit logs answer what you owe your users: their data is used only as they allowed, and you can show who did what. They don't answer what you owe everyone else. Regulators now require risk assessments, transparency about AI use, human oversight and record-keeping, on timelines that differ by jurisdiction and are still moving. Those obligations reach beyond any one user's consent.
→ Next: [§34 Governance and Regulation](34-governance-regulation.md)

## Check your understanding

**Q: Why shouldn't an internal agent run as one shared service account, even if every user is allowed to use the agent?**

The account's permissions apply whoever is asking, so any user, or any document the agent reads, can steer it into actions the requester couldn't take: a confused deputy (P9). Logs show only the service account, an attribution gap. Delegated tokens with the user in `sub` keep the agent inside that user's rights, so row-level security and audit still work. A shared principal suits only system jobs that no user drives.

**Q: What would happen if an MCP server forwarded the client's token straight to the GitHub API?**

That is token passthrough, which MCP forbids. GitHub would receive a token not issued for that hop, so audience-dependent controls are bypassed, logs blame the wrong party, and a stolen token can use the server as a proxy. The server should accept only tokens issued to itself and call GitHub as its own OAuth client with a separate token.

**Q: How does PKCE protect the authorization code flow, and what would an attacker with an intercepted code lack?**

The client sends only the SHA-256 challenge up front and keeps the verifier. Redeeming the code requires the verifier, which the authorization server hashes and compares. An attacker who intercepts the redirect has the code but not the verifier, so the token request fails. That is why OAuth 2.1 requires PKCE and MCP clients refuse servers without S256 support.

**Q: Delegated vs autonomous authority: when should an agent be its own principal?**

Use delegated authority for any action on a user's data: rights are the user's permissions intersected with the granted scopes, and audits name both parties. Use autonomous authority for work with no user in the loop, such as nightly triage, where the agent's own grants are the only limit and must be narrow. Many agents mix the two, acting as themselves for system tasks and with a delegated token when they touch a person's data.

**Q: Why must credentials never enter the model's context, even for a model you trust?**

Trusting the model doesn't mean trusting everything it reads. An injected instruction can make it copy a secret into a tool argument, a URL or its reply (P9), and context also lands in logs and traces. With a harness-side broker or an egress vault, a hijacked agent can only request tool calls. The harness executes them with a short-lived, narrow token the model never sees, so there is nothing to steal.

**Q: What does a valid Agent Card signature prove, and what doesn't it?**

The JWS over the canonicalized card proves it came from the key holder and wasn't altered, so a forged "Admin Helper" card fails. It doesn't prove the publisher is trustworthy, that the agent behaves as its skills claim, or that its output is safe to act on. You still need a publisher allow-list, per-request authentication and authorization, and treatment of remote output as untrusted ([§32](32-security-guardrails.md)).

**Q: Why isn't a user's click on "Approve" in the agent's UI the same as authorization?**

The click happens in software the agent controls and leaves nothing a resource server can verify; a hijacked or buggy client could fake it. Authorization means the authorization server issues a token or step-up grant that the resource server checks, and the WIMSE draft recommends binding approvals to such an event, for example via CIBA. Keep UI approvals as a usability layer on top of real scopes.

## Takeaways

- An agent is software acting for someone. Give it its own identity and record whom it acts for: `client_id` for the agent, `sub` for the user.
- Prefer delegated authority for user data: the user's rights intersected with the granted scopes, so existing row-level security still applies.
- OAuth 2.1 basics: authorization code + PKCE, short-lived audience-bound access tokens, secret refresh tokens, minimal scopes.
- MCP 2026-07-28: Protected Resource Metadata, CIMD over the now-deprecated Dynamic Client Registration, mandatory `resource`, PKCE S256 and audience checks, and `iss` validation.
- Token passthrough is forbidden. Each hop gets its own token; RFC 8693 token exchange can downscope it and record the actor chain.
- Credentials never enter context (P9). A harness-side broker, vault or workload identity attaches them at execution time.
- Real approval is a verifiable authorization event, not just a UI click.
- Agent identity standards are still drafts (WIMSE, OAuth WG, OpenID). Most of the work is applying OAuth and workload identity well.

## Sources

- MCP specification 2026-07-28, Authorization: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- MCP 2026-07-28, Authorization Server Discovery: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery
- MCP 2026-07-28, Client Registration: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration
- MCP 2026-07-28, Authorization Security Considerations: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
- MCP Security Best Practices (token passthrough, confused deputy, scope minimization): https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
- MCP changelogs, 2025-03-26 and 2026-07-28: https://modelcontextprotocol.io/specification/2025-03-26/changelog ; https://modelcontextprotocol.io/specification/2026-07-28/changelog
- MCP extensions, Enterprise-Managed Authorization: https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization
- MCP extensions, OAuth Client Credentials: https://modelcontextprotocol.io/extensions/auth/oauth-client-credentials
- The OAuth 2.1 Authorization Framework, draft-ietf-oauth-v2-1-16 (Sep 2026): https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/
- RFC 7636, Proof Key for Code Exchange: https://www.rfc-editor.org/rfc/rfc7636
- RFC 8707, Resource Indicators for OAuth 2.0: https://www.rfc-editor.org/rfc/rfc8707
- RFC 9728, OAuth 2.0 Protected Resource Metadata: https://www.rfc-editor.org/rfc/rfc9728
- RFC 9207, OAuth 2.0 Authorization Server Issuer Identification: https://www.rfc-editor.org/rfc/rfc9207
- RFC 8693, OAuth 2.0 Token Exchange: https://www.rfc-editor.org/rfc/rfc8693
- OAuth Client ID Metadata Document (draft): https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/
- Kasselman et al., "AI Identity Management System", draft-ietf-wimse-aims-00 (Sep 15, 2026): https://datatracker.ietf.org/doc/draft-ietf-wimse-aims/
- Identity Assertion JWT Authorization Grant (draft): https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/
- OAuth Identity and Authorization Chaining Across Domains (draft): https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-chaining/
- Transaction Tokens (draft): https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/
- OAuth 2.0 Extension: On-Behalf-Of User Authorization for AI Agents (individual draft): https://datatracker.ietf.org/doc/draft-oauth-ai-agents-on-behalf-of-user/
- OpenID Foundation, "Identity Management for Agentic AI" (Oct 7, 2025): https://openid.net/new-whitepaper-tackles-ai-agent-identity-challenges/ ; https://arxiv.org/abs/2510.25819
- A2A Protocol specification (Agent Cards, signatures, authentication): https://a2a-protocol.org/latest/specification/
- OWASP Top 10 for Agentic Applications for 2026 (ASI03, ASI07): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OpenAI docs, Workload identity federation: https://developers.openai.com/api/docs/guides/workload-identity-federation
- Claude docs, Authentication (API keys, Workload Identity Federation): https://platform.claude.com/docs/en/manage-claude/authentication
- Claude Managed Agents docs, Vaults: https://platform.claude.com/docs/en/managed-agents/vaults
- Databricks docs, Authentication for agents on Databricks Apps: https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication
- Snowflake docs, Caller's rights and owner's rights stored procedures: https://docs.snowflake.com/en/developer-guide/stored-procedure/stored-procedures-rights
