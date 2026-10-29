# eagle-desk

Live "agent desk" dashboard for the **Eagle** multi-agent team (Eagle lead →
Hawk infra / Owl comms), built on Claude Managed Agents.

```
eagle-desk/
  main.py                 FastAPI backend (SSE relay of the agent session)
  static/index.html       the desk UI
  Dockerfile
  docker-compose.yml
  .env.example
  push-eagle-desk.sh/.ps1 git force-push helpers
  agents/                 Managed Agents definitions (ant apply ...)
```

## Run (MOCK mode — works today, no API needed)
```
cp .env.example .env         # leave EAGLE_AGENT_ID blank
docker compose up -d --build
```
Open `http://<nas>:8080` → the desk plays a scripted Eagle/Hawk/Owl conversation.

## Go live (REAL mode)
1. `cd agents` and apply the three agents (subagents first):
   ```
   ant apply hawk-infra.md        # -> HAWK_AGENT_ID
   ant apply owl-comms.md         # -> OWL_AGENT_ID
   # put both ids into eagle-orchestrator.md, then:
   ant apply eagle-orchestrator.md   # -> EAGLE_AGENT_ID
   ```
2. Fill `.env`: `ANTHROPIC_API_KEY`, `EAGLE_AGENT_ID`, `ENV_ID` (a managed-agents
   environment), `VAULT_IDS` (MCP auth).
3. Verify the two `# VERIFY` seams in `main.py` against the Managed Agents
   "Session event stream" reference (beta API).
4. `docker compose up -d --build`

> hawk-infra.md = the IT Infra read-only agent. Keep every production write
> behind approval; FortiGate changes go through FortiManager.
