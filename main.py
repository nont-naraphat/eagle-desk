"""
eagle-desk: a live "agent desk" dashboard for the Eagle multi-agent team.

  Browser  --POST /api/message (SSE)-->  FastAPI  -->  Claude Managed Agents
                                                        session (Eagle lead ->
                                                        Hawk / Owl subagents)
  and streams every agent turn back to the desk UI as it happens.

Two modes:
  * REAL  - set ANTHROPIC_API_KEY + EAGLE_AGENT_ID + ENV_ID (+ VAULT_IDS).
            Opens a real session with the Eagle orchestrator and relays its
            event stream. Two seams are marked # VERIFY - confirm them against
            the Managed Agents "Session event stream" reference, since that API
            is beta and its exact event shapes may shift.
  * MOCK  - if EAGLE_AGENT_ID is unset, the app serves a scripted Eagle/Hawk/Owl
            conversation so you can deploy and SEE the desk today, then flip to
            REAL by filling .env.

ASCII-only comments (SunPassion convention).
"""

import json
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EAGLE_AGENT_ID = os.environ.get("EAGLE_AGENT_ID", "")      # orchestrator agent id
ENV_ID = os.environ.get("ENV_ID", "")                      # managed-agents environment id
VAULT_IDS = [v for v in os.environ.get("VAULT_IDS", "").split(",") if v.strip()]

REAL = bool(API_KEY and EAGLE_AGENT_ID and ENV_ID)

app = FastAPI(title="eagle-desk")

# one active session for this single-user ops tool (reset via /api/reset)
STATE = {"session_id": None}


def sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


# --- map a raw agent label to a desk lane the UI knows how to colour ----------
def lane(name: str) -> str:
    n = (name or "").lower()
    if "hawk" in n:
        return "hawk"
    if "owl" in n:
        return "owl"
    if "eagle" in n or "chief" in n:
        return "eagle"
    return "eagle"


# ----------------------------------------------------------------- REAL stream
def real_stream(text: str):
    from anthropic import Anthropic
    client = Anthropic(api_key=API_KEY)  # SDK sets the managed-agents beta header

    if not STATE["session_id"]:
        session = client.beta.sessions.create(
            agent={"type": "agent", "id": EAGLE_AGENT_ID},
            environment_id=ENV_ID,
            vault_ids=VAULT_IDS or None,
        )
        STATE["session_id"] = session.id
    sid = STATE["session_id"]

    yield sse({"lane": "user", "kind": "msg", "text": text})

    # VERIFY (1): the user-message event shape for events.send.
    with client.beta.sessions.events.stream(session_id=sid) as stream:
        client.beta.sessions.events.send(
            session_id=sid,
            type="user.message",
            content=[{"type": "text", "text": text}],
        )
        for event in stream:
            # VERIFY (2): field names below. Pull the acting agent's name and any
            # text out of each event; unknowns pass through as a system line so
            # nothing is silently dropped while you tune the mapping.
            etype = getattr(event, "type", "") or ""
            agent = (getattr(event, "agent_name", "")
                     or getattr(event, "source", "")
                     or "eagle")
            piece = ""
            content = getattr(event, "content", None)
            if isinstance(content, list):
                piece = "".join(
                    getattr(b, "text", "") or (b.get("text", "") if isinstance(b, dict) else "")
                    for b in content)
            elif isinstance(content, str):
                piece = content

            if "delegat" in etype or "subagent" in etype:
                yield sse({"lane": lane(agent), "kind": "handoff",
                           "text": piece or etype})
            elif piece:
                yield sse({"lane": lane(agent), "kind": "msg", "text": piece})
            elif etype:
                yield sse({"lane": "system", "kind": "sys", "text": etype})
    yield sse({"lane": "system", "kind": "done", "text": ""})


# ----------------------------------------------------------------- MOCK stream
def mock_stream(text: str):
    script = [
        ("user", "msg", text),
        ("eagle", "msg", "รับเรื่อง เดี๋ยวแยกงานให้ทีม - Hawk เช็ก infra, Owl ดูเมล/ปฏิทิน"),
        ("eagle", "handoff", "-> Hawk: AP-04 ยัง offline อยู่ไหม เช็ก switch port + PoE ด้วย"),
        ("hawk", "msg", "AP-04 offline: port gi3 link Down, PoE Searching (0W, budget เหลือ 81/370W) -> ปัญหาสาย/physical ที่ gi3 ไม่ใช่ config"),
        ("eagle", "handoff", "-> Owl: มีเมลวันนี้ที่ต้องตอบด่วนไหม"),
        ("owl", "msg", "เมลเด่น 2 ฉบับ: vendor ถามสถานะ AP, HR ขอสรุปอุปกรณ์ noncompliant - ร่างตอบไว้ให้แล้ว รออนุมัติ"),
        ("eagle", "msg", "สรุป: AP-04 เป็นที่สาย gi3 (ส่งช่างเช็ก) + มีเมล 2 ฉบับรอคุณกดส่ง อยากให้ส่งเลยไหม?"),
        ("system", "done", ""),
    ]
    for lane_, kind, msg in script:
        yield sse({"lane": lane_, "kind": kind, "text": msg})
        time.sleep(0.6)


@app.post("/api/message")
async def message(request: Request):
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        return StreamingResponse(iter([sse({"lane": "system", "kind": "sys",
                                            "text": "empty message"})]),
                                 media_type="text/event-stream")
    gen = real_stream(text) if REAL else mock_stream(text)
    return StreamingResponse(gen, media_type="text/event-stream")


@app.post("/api/reset")
async def reset():
    STATE["session_id"] = None
    return {"ok": True, "mode": "real" if REAL else "mock"}


@app.get("/api/status")
async def status():
    return {"mode": "real" if REAL else "mock",
            "session": STATE["session_id"]}


STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC, "index.html"))
