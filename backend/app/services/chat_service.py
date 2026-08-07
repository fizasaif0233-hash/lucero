import re
from typing import AsyncIterator, Dict, List, Optional, Set
from uuid import UUID

from app.agents.base import AgentProgress, AgentResult
from app.agents.orchestrator import AgentOrchestrator
from app.agents.research import ResearchAgent
from app.ai.service import AIService
from app.core.config import Settings, get_settings
from app.database.repositories import (
    ConversationRepository,
    MemoryRepository,
    MessageRepository,
)
from app.rag.retriever import RetrievedChunk, Retriever
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Orchestrates specialist agents, optional web research, RAG, and streaming AI."""

    def __init__(
        self,
        ai_service: AIService,
        retriever: Retriever,
        conversations: Optional[ConversationRepository] = None,
        messages: Optional[MessageRepository] = None,
        memories: Optional[MemoryRepository] = None,
        settings: Optional[Settings] = None,
        orchestrator: Optional[AgentOrchestrator] = None,
        research_agent: Optional[ResearchAgent] = None,
    ) -> None:
        self._ai = ai_service
        self._retriever = retriever
        self._conversations = conversations or ConversationRepository()
        self._messages = messages or MessageRepository()
        self._memories = memories or MemoryRepository()
        self._settings = settings or get_settings()
        self._orchestrator = orchestrator or AgentOrchestrator(ai_service, retriever)
        self._research = research_agent or ResearchAgent(
            ai_service,
            retriever,
            enable_web=self._settings.enable_web_research,
            settings=self._settings,
        )

    async def stream_chat(
        self,
        *,
        user_id: str | UUID,
        message: str,
        conversation_id: Optional[UUID] = None,
        model: Optional[str] = None,
        regenerate_message_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, str]]:
        import orjson

        selected_model = model or self._ai.default_model

        try:
            conversation = await self._resolve_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                first_message=message,
                model=selected_model,
                regenerate_message_id=regenerate_message_id,
            )
            conv_id = conversation["id"]

            if regenerate_message_id is None:
                self._messages.create(
                    conversation_id=conv_id,
                    role="user",
                    content=message,
                    model=selected_model,
                )
                if conversation.get("title") == "New conversation":
                    self._conversations.update_title(conv_id, message.strip()[:80])

            history = self._messages.list_for_conversation(conv_id)
            chat_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in history
                if m["role"] in {"user", "assistant"}
            ]

            memory_block = self._format_memory(user_id)
            agents_meta: List[dict] = []
            specialist_overlay = ""
            knowledge = ""
            collaborative = False
            research_sources = 0

            yield {
                "event": "meta",
                "data": orjson.dumps(
                    {
                        "conversation_id": conv_id,
                        "model": selected_model,
                        "mode": "agents",
                    }
                ).decode(),
            }

            async for event in self._orchestrator.run_turn(
                user_id=user_id,
                message=message,
                forced_agent_id=agent_id,
                memory_block=memory_block,
            ):
                etype = event.get("type")
                if etype == "route":
                    agents_meta = event.get("agents") or []
                    collaborative = bool(event.get("collaborative"))
                    yield {
                        "event": "meta",
                        "data": orjson.dumps(
                            {
                                "conversation_id": conv_id,
                                "model": selected_model,
                                "mode": "agents",
                                "agents": agents_meta,
                                "collaborative": collaborative,
                                "route_reason": event.get("reason"),
                            }
                        ).decode(),
                    }
                elif etype == "progress":
                    yield {
                        "event": "progress",
                        "data": orjson.dumps(
                            {
                                "step": event.get("agent_id") or "agent",
                                "detail": event.get("detail") or "",
                                "agent_id": event.get("agent_id"),
                                "agent_name": event.get("agent_name"),
                            }
                        ).decode(),
                    }
                elif etype == "section":
                    yield {
                        "event": "agent_section",
                        "data": orjson.dumps(
                            {
                                "agent_id": event.get("agent_id"),
                                "agent_name": event.get("agent_name"),
                                "content": event.get("content"),
                            }
                        ).decode(),
                    }
                elif etype == "context":
                    knowledge = event.get("knowledge") or ""
                    agents_meta = event.get("agents") or agents_meta
                    collaborative = bool(event.get("collaborative"))
                    specialist_overlay = self._orchestrator.build_system_overlay(
                        event.get("instructions") or "",
                        agents_meta,
                    )

            # Optional live research for investor/distributor discovery
            agent_ids = {a.get("id") for a in agents_meta}
            if self._wants_live_research(message, agent_ids):
                yield {
                    "event": "progress",
                    "data": orjson.dumps(
                        {
                            "step": "research",
                            "detail": "Research Agent searching Assets + web…",
                            "agent_name": "Research Agent",
                        }
                    ).decode(),
                }
                async for item in self._research.run(
                    message,
                    user_id=user_id,
                    search_queries=(message,),
                ):
                    if isinstance(item, AgentProgress):
                        yield {
                            "event": "progress",
                            "data": orjson.dumps(
                                {
                                    "step": item.step,
                                    "detail": item.detail,
                                    "agent_name": "Research Agent",
                                }
                            ).decode(),
                        }
                    elif isinstance(item, AgentResult):
                        research_sources = len(item.sources)
                        knowledge = (
                            f"{knowledge}\n\n{item.context_block}".strip()
                            if knowledge
                            else item.context_block
                        )

            yield {
                "event": "progress",
                "data": orjson.dumps(
                    {
                        "step": "answering",
                        "detail": (
                            "Merging specialist reports…"
                            if collaborative
                            else (
                                f"{agents_meta[0].get('name', 'L.U.C.E.R.O')} responding…"
                                if agents_meta
                                else "L.U.C.E.R.O responding…"
                            )
                        ),
                        "agent_name": (
                            agents_meta[0].get("name")
                            if agents_meta
                            else "L.U.C.E.R.O"
                        ),
                    }
                ).decode(),
            }

            # Ensure UI shows Lucero when no specialist was routed
            if not agents_meta:
                agents_meta = [
                    {
                        "id": "lucero",
                        "name": "L.U.C.E.R.O",
                        "title": "Business Partner",
                    }
                ]

            yield {
                "event": "meta",
                "data": orjson.dumps(
                    {
                        "conversation_id": conv_id,
                        "model": selected_model,
                        "mode": "agents",
                        "agents": agents_meta,
                        "collaborative": collaborative,
                        "research_sources": research_sources,
                    }
                ).decode(),
            }

            # Detect media intent early so we can force capability + finished files
            from app.agents.os_task_router import OsTaskRouter
            from app.media.job_service import JobService
            from app.media.refusal_rewrite import (
                finished_flyer_package,
                looks_like_media_refusal,
                strip_designer_prompt_dumps,
                strip_fake_download_claims,
            )

            prior_user = " ".join(
                m.get("content", "")
                for m in chat_messages
                if m.get("role") == "user" and m.get("content") != message
            )[-2000:]
            os_plan = OsTaskRouter().plan(message, prior_context=prior_user)
            if os_plan.media_job:
                media_overlay = (
                    "MEDIA CAPABILITY (mandatory):\n"
                    "You CAN create images, flyers, landing pages, PDF/PNG exports, and video "
                    "via L.U.C.E.R.O + Replicate.\n"
                    "NEVER say you cannot create images or files.\n"
                    "NEVER give Canva, Illustrator, Photoshop, Midjourney, or Flux tutorials.\n"
                    "NEVER dump Image prompts / Flux / Midjourney lists for the user to copy — "
                    "Replicate generates real PNG/PDF files automatically after your reply.\n"
                    "Return short finished copy only."
                )
                specialist_overlay = (
                    f"{specialist_overlay}\n\n{media_overlay}".strip()
                    if specialist_overlay
                    else media_overlay
                )

            full_response: List[str] = []
            async for token in self._ai.stream_response(
                chat_messages,
                knowledge_context=knowledge or None,
                specialist_overlay=specialist_overlay or None,
                model=selected_model,
                temperature=0.55,
            ):
                full_response.append(token)
                yield {
                    "event": "token",
                    "data": orjson.dumps(token).decode(),
                }

            assistant_text = "".join(full_response).strip()
            if not assistant_text:
                assistant_text = (
                    "I was unable to generate a response. Please try again."
                )

            # Never keep hallucinated Download PNG/PDF lines — real links are appended after the job
            if os_plan.media_job:
                assistant_text = strip_fake_download_claims(assistant_text)

            # If the model still refuses on a media request, replace with finished package
            if os_plan.media_job and looks_like_media_refusal(assistant_text):
                assistant_text = finished_flyer_package(user_message=message)
                # Re-emit as a fresh token block for clients that only keep stream buffer
                yield {
                    "event": "token",
                    "data": orjson.dumps(
                        "\n\n---\n*(Rewriting to finished deliverable…)*\n\n"
                        + assistant_text
                    ).decode(),
                }

            # Prefix attribution for UI clarity when multiple agents
            if collaborative and agents_meta:
                chain = " → ".join(a["name"] for a in agents_meta)
                if not assistant_text.startswith("**"):
                    assistant_text = (
                        f"**Agents:** {chain}\n\n{assistant_text}"
                    )

            saved = self._messages.create(
                conversation_id=conv_id,
                role="assistant",
                content=assistant_text,
                model=selected_model,
            )
            self._conversations.touch(conv_id)

            jobs_meta: List[dict] = []
            assets_meta: List[dict] = []
            try:
                import asyncio

                can_run = bool(os_plan.media_job) and (
                    not os_plan.requires_replicate
                    or bool(self._settings.replicate_api_token)
                    # Print flyers/pptx can still compose without Replicate
                    or os_plan.media_job
                    in {
                        "flyer_image",
                        "print_flyer",
                        "presentation",
                        "pptx",
                        "pitch_deck",
                    }
                )
                if os_plan.media_job and can_run:
                    yield {
                        "event": "progress",
                        "data": orjson.dumps(
                            {
                                "step": "media",
                                "detail": (
                                    f"Building finished {os_plan.media_job} "
                                    "(downloadable print/media file)…"
                                ),
                                "agent_name": "L.U.C.E.R.O Media",
                            }
                        ).decode(),
                    }
                    job_svc = JobService(self._settings)
                    job = job_svc.create(
                        user_id=user_id,
                        task_type=os_plan.media_job,
                        conversation_id=conv_id,
                        input_data={
                            "user_message": message,
                            "assistant_text": assistant_text,
                            "title": os_plan.intent.replace("_", " ").title(),
                        },
                    )
                    # Hide Flux/Midjourney dumps from the chat — user wants images, not prompts
                    display_text = strip_designer_prompt_dumps(
                        strip_fake_download_claims(assistant_text)
                    )
                    if display_text != assistant_text:
                        assistant_text = display_text
                        try:
                            from app.database.client import get_supabase_admin

                            get_supabase_admin().table("messages").update(
                                {"content": assistant_text}
                            ).eq("id", saved["id"]).execute()
                        except Exception:
                            pass

                    # Run heavy media in background — awaiting Replicate inline often
                    # exceeds proxy/browser limits and surfaces as a client "network error".
                    # Frontend pollJob() attaches PNG/PDF downloads when the job finishes.
                    yield {
                        "event": "progress",
                        "data": orjson.dumps(
                            {
                                "step": "media",
                                "detail": (
                                    "Generating Replicate + print files in background…"
                                    if os_plan.media_job
                                    in {"landing_page", "social_pack", "logo", "flyer_image", "print_flyer"}
                                    else "Building media files…"
                                ),
                                "agent_name": "L.U.C.E.R.O Media",
                            }
                        ).decode(),
                    }
                    yield {
                        "event": "job",
                        "data": orjson.dumps(
                            {
                                "id": job["id"],
                                "task_type": job.get("task_type"),
                                "status": "queued",
                                "progress": 0,
                            }
                        ).decode(),
                    }
                    asyncio.create_task(job_svc.process_job(job))
                    jobs_meta.append(
                        {
                            "id": job["id"],
                            "task_type": job.get("task_type"),
                            "status": "queued",
                            "progress": 0,
                            "progress_detail": "Generating print-ready files…",
                            "error_message": None,
                            "result": {},
                        }
                    )
                    note = (
                        "\n\n---\n"
                        "**Generating print-ready PNG & PDF…** "
                        "Download buttons appear here when files are ready "
                        "(usually under a minute)."
                    )
                    if note.strip() not in assistant_text:
                        assistant_text = assistant_text.rstrip() + note
                        try:
                            from app.database.client import get_supabase_admin

                            get_supabase_admin().table("messages").update(
                                {"content": assistant_text}
                            ).eq("id", saved["id"]).execute()
                        except Exception:
                            pass
                elif os_plan.media_job and os_plan.requires_replicate:
                    yield {
                        "event": "progress",
                        "data": orjson.dumps(
                            {
                                "step": "media",
                                "detail": (
                                    "Set REPLICATE_API_TOKEN on Railway to generate "
                                    "AI artwork/video."
                                ),
                                "agent_name": "L.U.C.E.R.O Media",
                            }
                        ).decode(),
                    }
            except Exception as media_exc:
                logger.warning("media_job_enqueue_failed", error=str(media_exc))
                # Still tell the user why files didn't appear
                fail_note = (
                    f"\n\n---\n**Media system error:** {media_exc}. "
                    "Run Supabase migration `006_ai_os.sql` and redeploy the API."
                )
                if fail_note not in assistant_text:
                    assistant_text = assistant_text.rstrip() + fail_note

            yield {
                "event": "done",
                "data": orjson.dumps(
                    {
                        "conversation_id": conv_id,
                        "message_id": saved["id"],
                        "content": assistant_text,
                        "mode": "agents",
                        "agents": agents_meta,
                        "collaborative": collaborative,
                        "jobs": jobs_meta,
                        "assets": assets_meta,
                    }
                ).decode(),
            }
        except Exception as exc:
            logger.exception("chat_stream_failed", user_id=str(user_id))
            yield {"event": "error", "data": str(exc)}

    @staticmethod
    def _wants_live_research(message: str, agent_ids: Set[str]) -> bool:
        lower = (message or "").lower()
        # Explicit / current-info internet intents (Perplexity-style)
        web_triggers = (
            "latest",
            "today",
            "news",
            "recent",
            "research",
            "look up",
            "lookup",
            "search internet",
            "search online",
            "search the web",
            "find online",
            "google",
            "current price",
            "current trend",
            "current trends",
            "competitors",
            "competitor",
            "viral",
            "market research",
            "what's happening",
            "what is happening",
            "live data",
            "up to date",
            "up-to-date",
            "is it real",
            "are they real",
            "legit",
            "legitimate",
            "scam",
            "verify",
            "fact check",
            "fact-check",
            "according to the internet",
            "on the web",
        )
        if any(w in lower for w in web_triggers):
            return True
        # "Is Viral Coaching real?" / "Is X legit?" style verification
        if re.search(r"\bis\s+.+\s+real\b", lower) or re.search(
            r"\bare\s+.+\s+real\b", lower
        ):
            return True
        # Investor / distributor discovery phrasing
        if {"investor", "distributor", "research"} & agent_ids:
            return any(
                w in lower
                for w in (
                    "find",
                    "research",
                    "search",
                    "who should",
                    "look for",
                    "discover",
                    "pipeline",
                )
            )
        return False

    def _format_memory(self, user_id: str | UUID) -> str:
        rows = self._memories.list_for_user(user_id)[:20]
        if not rows:
            return ""
        return "\n".join(
            f"- [{r.get('category') or 'general'}] {r['content']}" for r in rows
        )

    async def _resolve_conversation(
        self,
        *,
        user_id: str | UUID,
        conversation_id: Optional[UUID],
        first_message: str,
        model: str,
        regenerate_message_id: Optional[UUID],
    ) -> dict:
        if regenerate_message_id:
            target = self._messages.get(regenerate_message_id)
            if not target or target["role"] != "assistant":
                raise ValueError("Message to regenerate not found")
            conversation = self._conversations.get(
                target["conversation_id"], user_id
            )
            if not conversation:
                raise ValueError("Conversation not found")
            self._messages.delete_after(
                target["conversation_id"], target["created_at"]
            )
            return conversation

        if conversation_id:
            conversation = self._conversations.get(conversation_id, user_id)
            if not conversation:
                raise ValueError("Conversation not found")
            return conversation

        return self._conversations.create(
            user_id=user_id,
            title=first_message.strip()[:80] or "New conversation",
            model=model,
        )
