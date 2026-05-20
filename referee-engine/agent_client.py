"""
OpenClaw Agent client — drives agents via docker exec and the CLI.

Design: use the validated `openclaw agent -m` CLI path instead of the Gateway WebSocket,
which depends on device pairing/signing flows that are not as well exercised in tests.
"""
import asyncio
import json
import logging
import base64
import os
import re
import shlex
from typing import Any, Dict, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time

logger = logging.getLogger(__name__)


MESSAGE_MODE_NORMAL = "normal"
MESSAGE_MODE_BUFFERED = "buffered"
MESSAGE_MODE_INTERRUPT = "interrupt"


@dataclass
class BufferedMessage:
    message: str
    message_kind: str
    timeout: Optional[int] = None
    dedupe_key: Optional[str] = None
    merge_strategy: str = "replace"
    stream_callback: Optional[Callable[[str], object]] = None
    merged_count: int = 1


@dataclass
class AgentSession:
    """Per-agent session state."""
    player_id: int
    container_name: str
    target_container: str
    target_ip: str
    ready: bool = False
    runtime_ready: bool = False
    session_ready: bool = False
    interactive_ready: bool = False
    init_ready: bool = False
    last_response: Optional[str] = None
    session_id: Optional[str] = None
    started_at: Optional[datetime] = None
    logs: List[Dict] = field(default_factory=list)
    init_error_reason: Optional[str] = None
    init_error_details: Optional[str] = None
    last_partial_stdout: Optional[str] = None
    last_partial_stderr: Optional[str] = None
    last_activity_at: Optional[float] = None
    last_stream_output_at: Optional[float] = None
    last_keepalive_sent_at: Optional[float] = None
    last_session_activity_signature: Optional[str] = None
    last_code_activity_signature: Optional[str] = None
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    in_flight_message_kind: Optional[str] = None
    in_flight_message_mode: Optional[str] = None
    in_flight_started_at: Optional[float] = None
    last_completed_message_kind: Optional[str] = None
    buffered_messages: List[BufferedMessage] = field(default_factory=list)
    buffered_messages_frozen: bool = False
    # R2 (RESEARCH_PLAN.md §4.2, §6.2): per-session token accounting. Populated
    # in _send_message_locked from the OpenAI-style `usage` block on each agent
    # response. The referee sums these across agent_sessions to enforce the
    # per-match input/output ceilings and to record real token spend in the JSONL.
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_messages: int = 0

    @property
    def is_busy(self) -> bool:
        return self.send_lock.locked() or self.in_flight_message_kind is not None

    @property
    def has_buffered_messages(self) -> bool:
        return bool(self.buffered_messages)


@dataclass
class InitResult:
    success: bool
    reason: Optional[str] = None
    details: Optional[str] = None


class AgentClient:
    """
    Agent client — manages OpenClaw agent containers.

    Uses docker exec to run the openclaw agent CLI. Supports:
    - Writing OpenClaw config (model provider, proxy, etc.)
    - Sending prompts and awaiting responses
    - Tracking session logs
    - Sending heartbeat updates
    """

    # OpenClaw config constants (validated against real container runs)
    OPENCLAW_CONFIG_PATH = "/home/node/.openclaw/openclaw.json"
    OPENCLAW_SESSION_DIR = "/home/node/.openclaw/agents/main/sessions"
    TARGET_CODE_PATHS = (
        "/app",
        "/app/static",
        "/app/data",
    )
    GATEWAY_BOOTSTRAP_TIMEOUT = 300
    CONFIG_WAIT_TIMEOUT = 30
    CONFIG_WAIT_POLL_INTERVAL = 2
    CONFIG_GATEWAY_GRACE_PERIOD = 20
    CONFIG_COPY_TIMEOUT = 10
    POST_CONFIG_APPLY_DELAY = 5
    CONFIG_VERIFY_RETRY_DELAY = 3
    GATEWAY_STATE_READ_TIMEOUT = 15
    GATEWAY_MODEL_APPLY_TIMEOUT = 90
    GATEWAY_MODEL_POLL_INTERVAL = 2
    INIT_PROMPT_TIMEOUT = 180
    StreamCallback = Callable[[str], object]

    @staticmethod
    def _default_models_provider_key(llm_base_url: str) -> str:
        """OpenClaw `models.providers` key; must match how the gateway reports `agent model:`."""
        if "openrouter.ai" in (llm_base_url or "").strip().lower():
            # OpenRouter is OpenAI-completions compatible; reuse the built-in `openai` provider
            # slot so the gateway reloads off the same provider tree as the default image.
            return "openai"
        # Legacy default used before OpenRouter auto-detection.
        return "routerss"

    @staticmethod
    def _normalize_session_search_text(value: str) -> str:
        normalized = re.sub(r"[*`]+", "", value or "")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()
    
    def __init__(
        self,
        llm_api_key: str,
        llm_base_url: str = "",
        llm_model: str = "claude-sonnet-4-6",
        proxy_url: str = "http://host.docker.internal:7897",
        agent_timeout: int = 600,
        provider_name: Optional[str] = None,
    ):
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.provider_name = (
            provider_name
            if provider_name is not None
            else AgentClient._default_models_provider_key(llm_base_url)
        )
        self.qualified_model = f"{self.provider_name}/{llm_model}"
        self.proxy_url = proxy_url
        self.agent_timeout = agent_timeout
        # OpenRouter's gateway log never reflects the model name we configure
        # (it shows the bundled default `openai/gpt-5.5` until first send), so
        # waiting the full 180s is pure dead time — the wait always falls
        # through to the disk-config warning path. Keep it short.
        self.gateway_model_apply_timeout = (
            30
            if "openrouter.ai" in (llm_base_url or "").strip().lower()
            else self.GATEWAY_MODEL_APPLY_TIMEOUT
        )
        self.sessions: Dict[int, AgentSession] = {}

    @staticmethod
    def _mark_session_activity(session: AgentSession) -> None:
        session.last_activity_at = time.monotonic()

    @staticmethod
    def _mark_runtime_ready(session: AgentSession) -> None:
        session.runtime_ready = True

    @staticmethod
    def _mark_session_ready(session: AgentSession) -> None:
        session.runtime_ready = True
        session.session_ready = True

    @staticmethod
    def _mark_interactive_ready(session: AgentSession) -> None:
        session.runtime_ready = True
        session.session_ready = bool(session.session_id) or session.session_ready
        session.interactive_ready = True

    @staticmethod
    def _mark_init_ready(session: AgentSession) -> None:
        session.ready = True
        session.runtime_ready = True
        session.session_ready = bool(session.session_id) or session.session_ready
        session.interactive_ready = True
        session.init_ready = True

    @staticmethod
    def is_session_busy(session: AgentSession) -> bool:
        return session.is_busy

    @staticmethod
    def has_buffered_message_kind(session: AgentSession, message_kind: str) -> bool:
        return any(item.message_kind == message_kind for item in session.buffered_messages)

    @staticmethod
    def freeze_buffered_messages(session: AgentSession) -> None:
        session.buffered_messages_frozen = True

    @staticmethod
    def unfreeze_buffered_messages(session: AgentSession) -> None:
        session.buffered_messages_frozen = False

    async def enqueue_buffered_message(
        self,
        session: AgentSession,
        message: str,
        *,
        message_kind: str,
        timeout: Optional[int] = None,
        stream_callback: Optional[StreamCallback] = None,
        dedupe_key: Optional[str] = None,
        merge_strategy: str = "replace",
        auto_drain: bool = True,
    ) -> str:
        if timeout is None:
            timeout = self.agent_timeout

        existing: Optional[BufferedMessage] = None
        dedupe_value = dedupe_key or message_kind
        if dedupe_value:
            existing = next(
                (item for item in session.buffered_messages if item.dedupe_key == dedupe_value),
                None,
            )

        if existing is not None:
            existing.timeout = timeout
            existing.stream_callback = stream_callback or existing.stream_callback
            existing.merged_count += 1
            if merge_strategy == "append" and message not in existing.message:
                existing.message = f"{existing.message}\n{message}" if existing.message else message
            else:
                existing.message = message
            logger.info(
                f"[Player {session.player_id}] buffered message merged: "
                f"kind={message_kind} frozen={session.buffered_messages_frozen} total_buffered={len(session.buffered_messages)}"
            )
            return "merged"

        session.buffered_messages.append(
            BufferedMessage(
                message=message,
                message_kind=message_kind,
                timeout=timeout,
                dedupe_key=dedupe_value,
                merge_strategy=merge_strategy,
                stream_callback=stream_callback,
            )
        )
        logger.info(
            f"[Player {session.player_id}] buffered message queued: "
            f"kind={message_kind} frozen={session.buffered_messages_frozen} total_buffered={len(session.buffered_messages)}"
        )

        if auto_drain and not session.buffered_messages_frozen and not self.is_session_busy(session):
            delivered_count = await self.drain_buffered_messages(session)
            if delivered_count > 0:
                return "sent"

        return "queued"

    async def drain_buffered_messages(self, session: AgentSession) -> int:
        delivered = 0
        while session.buffered_messages and not session.buffered_messages_frozen:
            buffered = session.buffered_messages.pop(0)
            logger.info(
                f"[Player {session.player_id}] draining buffered message: "
                f"kind={buffered.message_kind} merged_count={buffered.merged_count} remaining={len(session.buffered_messages)}"
            )
            response = await self.send_message(
                session,
                buffered.message,
                timeout=buffered.timeout,
                stream_callback=buffered.stream_callback,
                message_kind=buffered.message_kind,
                message_mode=MESSAGE_MODE_BUFFERED,
                drain_buffered_after=False,
            )
            if buffered.message_kind in {"keepalive", "attack_keepalive"} and response is not None:
                session.last_keepalive_sent_at = time.monotonic()
            delivered += 1
        return delivered

    async def _resolve_session_file(self, session: AgentSession) -> Optional[str]:
        session_file: Optional[str] = None

        if session.session_id:
            candidate_file = f"{self.OPENCLAW_SESSION_DIR}/{session.session_id}.jsonl"
            exists = await self._exec(
                session.container_name,
                f"test -f {candidate_file} && printf ok"
            )
            if exists.strip() == "ok":
                session_file = candidate_file
            else:
                logger.warning(
                    f"[Player {session.player_id}] Expected session log missing for session_id={session.session_id}; falling back to latest .jsonl"
                )

        if session_file is None:
            result = await self._exec(
                session.container_name,
                f"sh -lc 'ls -t {self.OPENCLAW_SESSION_DIR}/*.jsonl 2>/dev/null | head -1'"
            )

            if not result.strip():
                return None

            session_file = result.strip()

        return session_file

    async def observe_session_activity(self, session: AgentSession, tail_lines: int = 8) -> bool:
        session_file = await self._resolve_session_file(session)
        if session_file is None:
            return False

        snapshot = await self._exec(
            session.container_name,
            (
                "sh -lc '"
                f"if [ -f {session_file} ]; then "
                f"wc -c < {session_file} 2>/dev/null; "
                "printf "
                "\"\\n__TAIL__\\n\"; "
                f"tail -n {tail_lines} {session_file} 2>/dev/null || cat {session_file} 2>/dev/null; "
                "fi'"
            )
        )
        if not snapshot.strip():
            return False

        if snapshot != session.last_session_activity_signature:
            session.last_session_activity_signature = snapshot
            self._mark_session_activity(session)
            return True

        return False

    async def observe_code_activity(self, session: AgentSession) -> bool:
        watched_paths = " ".join(shlex.quote(path) for path in self.TARGET_CODE_PATHS)
        snapshot = await self._exec(
            session.target_container,
            (
                "sh -lc '"
                f"for path in {watched_paths}; do "
                "if [ -e \"$path\" ]; then "
                r"find \"$path\" -type f \\\(" 
                "-name \"*.py\" -o -name \"*.js\" -o -name \"*.ts\" -o -name \"*.tsx\" -o -name \"*.jsx\" "
                "-o -name \"*.json\" -o -name \"*.yaml\" -o -name \"*.yml\" -o -name \"*.toml\" "
                "-o -name \"*.ini\" -o -name \"*.conf\" -o -name \"*.env\" -o -name \"*.txt\" "
                r"-o -name \"*.html\" -o -name \"*.css\" -o -name \"*.sql\" -o -name \"*.sh\" \\\) "
                "-printf \"%T@ %p\\n\" 2>/dev/null; "
                "fi; done | sort -nr | head -n 20'"
            )
        )
        if not snapshot.strip():
            return False

        if snapshot != session.last_code_activity_signature:
            session.last_code_activity_signature = snapshot
            self._mark_session_activity(session)
            return True

        return False
    
    async def configure_container(self, container_name: str) -> InitResult:
        """
        Configure the OpenClaw container model provider.

        Writes full config via docker cp, then verifies it.
        Important: `"api": "openai-completions"` is required or requests may fail.
        """
        bootstrap_wait = await self._wait_for_gateway_bootstrap(container_name)
        if not bootstrap_wait.success:
            logger.error(f"[{container_name}] {bootstrap_wait.details}")
            return bootstrap_wait

        config_wait = await self._wait_for_gateway_config(container_name)
        if not config_wait.success:
            logger.error(f"[{container_name}] {config_wait.details}")
            return config_wait
        
        existing_config_str = await self._exec(
            container_name,
            f"cat {self.OPENCLAW_CONFIG_PATH}"
        )
        
        try:
            existing_config = json.loads(existing_config_str)
        except json.JSONDecodeError:
            logger.warning(f"[{container_name}] Could not parse existing config, using empty")
            existing_config = {}
        
        gateway_section = existing_config.get("gateway", {})

        existing_models = existing_config.get("models")
        if not isinstance(existing_models, dict):
            existing_models = {}
        merged_providers: Dict[str, Any] = dict(existing_models.get("providers") or {})

        provider_block: Dict[str, Any] = {
            "apiKey": self.llm_api_key,
            "api": "openai-completions",
            "models": [
                {
                    "id": self.llm_model,
                    "name": self.llm_model,
                }
            ],
        }
        if self.llm_base_url:
            provider_block["baseUrl"] = self.llm_base_url

        if self.provider_name == "openai" and "openrouter.ai" in (self.llm_base_url or "").strip().lower():
            prior = merged_providers.get("openai")
            prior_dict = dict(prior) if isinstance(prior, dict) else {}
            prior_dict.update(provider_block)
            merged_providers["openai"] = prior_dict
        else:
            merged_providers[self.provider_name] = provider_block

        new_config = {
            **existing_config,
            "gateway": gateway_section,
            "agents": {
                "defaults": {
                    "model": self.qualified_model,
                }
            },
            "models": {
                **existing_models,
                "mode": existing_models.get("mode", "merge"),
                "providers": merged_providers,
            },
        }

        if self.llm_base_url and self.provider_name != "openai":
            new_config["models"]["providers"][self.provider_name]["baseUrl"] = self.llm_base_url
        
        config_json = json.dumps(new_config, indent=2)
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_json)
            tmp_path = f.name
        
        try:
            proc = await asyncio.create_subprocess_shell(
                f"docker cp {tmp_path} {container_name}:{self.OPENCLAW_CONFIG_PATH}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.CONFIG_COPY_TIMEOUT)
            if proc.returncode != 0:
                logger.error(f"[{container_name}] docker cp failed: {stderr.decode()}")
                return InitResult(False, "CONFIG_COPY_FAILED", stderr.decode("utf-8", errors="replace").strip() or "docker cp failed")
        finally:
            os.unlink(tmp_path)
        
        # docker cp creates files as root; OpenClaw runs as node
        await self._exec_as_root(container_name, f"chown node:node {self.OPENCLAW_CONFIG_PATH}")
        
        await asyncio.sleep(self.POST_CONFIG_APPLY_DELAY)
        
        verify = await self._exec(
            container_name,
            f"cat {self.OPENCLAW_CONFIG_PATH}"
        )
        
        if not verify:
            logger.warning(f"[{container_name}] Verify read returned empty, retrying...")
            await asyncio.sleep(self.CONFIG_VERIFY_RETRY_DELAY)
            verify = await self._exec(
                container_name,
                f"cat {self.OPENCLAW_CONFIG_PATH}"
            )
        
        if self.qualified_model not in verify or "openai-completions" not in verify:
            logger.error(f"[{container_name}] Config verification failed. Got: {verify[:300]}")
            logger.info(f"[{container_name}] Attempting fallback with openclaw config set...")
            fallback_result = await self._fallback_configure(container_name)
            if not fallback_result.success:
                return fallback_result
        else:
            logger.info(f"[{container_name}] OpenClaw config file updated: model={self.qualified_model}")

        live_model, live_details = await self._wait_gateway_model_applied(container_name)
        if live_model != self.qualified_model:
            verify_live = await self._exec(container_name, f"cat {self.OPENCLAW_CONFIG_PATH}")
            disk_ok = self.qualified_model in verify_live and "openai-completions" in verify_live
            if disk_ok:
                logger.warning(
                    f"[{container_name}] Gateway log still shows {live_model!r} after "
                    f"{self.gateway_model_apply_timeout}s, but openclaw.json lists {self.qualified_model}; "
                    "continuing (OpenClaw may apply the model on first use or delay log updates)."
                )
                return InitResult(True)
            details = (
                f"expected live model {self.qualified_model}, observed {live_model or 'unknown'}"
                f"; recent gateway logs: {live_details}"
            )
            logger.error(f"[{container_name}] {details}")
            return InitResult(False, "GATEWAY_RELOAD_TIMEOUT", details)

        logger.info(f"[{container_name}] OpenClaw configured and active: model={live_model}")
        return InitResult(True)

    async def _config_file_exists(self, container_name: str) -> bool:
        result = await self._exec(
            container_name,
            f"test -f {self.OPENCLAW_CONFIG_PATH} && echo ok"
        )
        return result.strip() == "ok"

    async def _gateway_appears_live(self, container_name: str) -> Tuple[bool, str]:
        recent_events = await self._read_recent_gateway_events(container_name)
        if recent_events:
            return True, recent_events

        live_model = await self._read_live_gateway_model(container_name)
        if live_model:
            return True, f"observed live model {live_model}"

        return False, ""

    async def _wait_for_gateway_bootstrap(self, container_name: str) -> InitResult:
        deadline = asyncio.get_running_loop().time() + self.GATEWAY_BOOTSTRAP_TIMEOUT
        last_details = ""

        while asyncio.get_running_loop().time() < deadline:
            is_live, live_details = await self._gateway_appears_live(container_name)
            if is_live:
                return InitResult(True)

            if live_details:
                last_details = live_details

            await asyncio.sleep(self.CONFIG_WAIT_POLL_INTERVAL)

        details = (
            f"Gateway did not reach bootstrap-ready state within {self.GATEWAY_BOOTSTRAP_TIMEOUT} seconds"
            f"; recent gateway logs: {last_details or 'no startup signals captured'}"
        )
        return InitResult(False, "GATEWAY_BOOT_TIMEOUT", details)

    async def _wait_for_gateway_config(self, container_name: str) -> InitResult:
        deadline = asyncio.get_running_loop().time() + self.CONFIG_WAIT_TIMEOUT

        while asyncio.get_running_loop().time() < deadline:
            if await self._config_file_exists(container_name):
                return InitResult(True)

            await asyncio.sleep(self.CONFIG_WAIT_POLL_INTERVAL)

        grace_deadline = asyncio.get_running_loop().time() + self.CONFIG_GATEWAY_GRACE_PERIOD
        logger.warning(
            f"[{container_name}] Gateway is live but config file is still missing; granting {self.CONFIG_GATEWAY_GRACE_PERIOD}s grace"
        )
        while asyncio.get_running_loop().time() < grace_deadline:
            if await self._config_file_exists(container_name):
                return InitResult(True)
            await asyncio.sleep(self.CONFIG_WAIT_POLL_INTERVAL)

        return InitResult(
            False,
            "CONFIG_FILE_MISSING",
            f"Gateway config file was not created within {self.CONFIG_WAIT_TIMEOUT + self.CONFIG_GATEWAY_GRACE_PERIOD} seconds after gateway bootstrap"
        )
    
    async def _fallback_configure(self, container_name: str) -> InitResult:
        await self._exec(container_name, f"openclaw config set agents.defaults.model {self.qualified_model}")
        
        config_payload = {
            "mode": "merge",
            "providers": {
                self.provider_name: {
                    "apiKey": self.llm_api_key,
                    "api": "openai-completions",
                    "models": [{"id": self.llm_model, "name": self.llm_model}]
                }
            }
        }
        if self.llm_base_url:
            config_payload["providers"][self.provider_name]["baseUrl"] = self.llm_base_url
        config_json = json.dumps(config_payload)
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_json)
            tmp_path = f.name
        
        try:
            existing = await self._exec(container_name, f"cat {self.OPENCLAW_CONFIG_PATH}")
            try:
                cfg = json.loads(existing)
            except json.JSONDecodeError:
                cfg = {}
            
            cfg["agents"] = {"defaults": {"model": self.qualified_model}}
            cfg["models"] = json.loads(config_json)
            
            with open(tmp_path, 'w') as f:
                json.dump(cfg, f, indent=2)
            
            proc = await asyncio.create_subprocess_shell(
                f"docker cp {tmp_path} {container_name}:{self.OPENCLAW_CONFIG_PATH}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=self.CONFIG_COPY_TIMEOUT)
        finally:
            os.unlink(tmp_path)
        
        await self._exec_as_root(container_name, f"chown node:node {self.OPENCLAW_CONFIG_PATH}")
        await asyncio.sleep(self.POST_CONFIG_APPLY_DELAY)
        
        verify = await self._exec(container_name, f"cat {self.OPENCLAW_CONFIG_PATH}")
        success = self.qualified_model in verify and "openai-completions" in verify
        if success:
            logger.info(f"[{container_name}] Fallback config succeeded")
        else:
            logger.error(f"[{container_name}] Fallback config also failed. Got: {verify[:200]}")
        if success:
            return InitResult(True)
        return InitResult(
            False,
            "CONFIG_VERIFICATION_FAILED",
            f"Config file did not contain expected provider/model after fallback: {verify[:200]}"
        )

    async def _read_live_gateway_model(self, container_name: str) -> Optional[str]:
        script = """
import json
from pathlib import Path

last_model = ''
for path in sorted(Path('/tmp/openclaw').glob('openclaw-*.log')):
    try:
        for raw in path.read_text(errors='replace').splitlines():
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            message = payload.get('1')
            if isinstance(message, str) and message.startswith('agent model: '):
                last_model = message.split('agent model: ', 1)[1].strip()
    except Exception:
        continue

if last_model:
    print(last_model)
"""
        command = shlex.quote(f"python3 - <<'PY'\n{script}\nPY")
        result = await self._exec(
            container_name,
            f"sh -lc {command}",
            timeout=self.GATEWAY_STATE_READ_TIMEOUT,
        )
        value = result.strip()
        return value or None

    async def _read_recent_gateway_events(self, container_name: str) -> str:
        script = """
import json
from pathlib import Path

events = []
keywords = (
    'config change',
    'SIGUSR1',
    'agent model:',
    'listening on ws://',
    'Browser control listening',
    'Generated a new token',
)

for path in sorted(Path('/tmp/openclaw').glob('openclaw-*.log')):
    try:
        for raw in path.read_text(errors='replace').splitlines():
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            parts = []
            for key in ('1', '2'):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())

            message = ' '.join(parts)
            if message and any(keyword in message for keyword in keywords):
                ts = payload.get('time', '')
                events.append(f"{ts} {message}".strip())
    except Exception:
        continue

for item in events[-10:]:
    print(item)
"""
        command = shlex.quote(f"python3 - <<'PY'\n{script}\nPY")
        result = await self._exec(
            container_name,
            f"sh -lc {command}",
            timeout=self.GATEWAY_STATE_READ_TIMEOUT,
        )
        compact = " | ".join(line.strip() for line in result.splitlines() if line.strip())
        return compact[:800]

    async def _wait_gateway_model_applied(
        self,
        container_name: str,
        timeout: Optional[int] = None,
    ) -> Tuple[Optional[str], str]:
        if timeout is None:
            timeout = self.gateway_model_apply_timeout
        deadline = asyncio.get_running_loop().time() + timeout
        last_model: Optional[str] = None
        last_details = ""

        while asyncio.get_running_loop().time() < deadline:
            last_model = await self._read_live_gateway_model(container_name)
            last_details = await self._read_recent_gateway_events(container_name)
            if last_model == self.qualified_model:
                return last_model, last_details
            await asyncio.sleep(self.GATEWAY_MODEL_POLL_INTERVAL)

        return last_model, last_details

    def _extract_ready_texts(self, response: str) -> Tuple[Optional[str], List[str]]:
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            return None, [response]

        status = payload.get("status") if isinstance(payload, dict) else None
        texts: List[str] = []

        if isinstance(payload, dict):
            result = payload.get("result")
            if isinstance(result, dict):
                payloads = result.get("payloads")
                if isinstance(payloads, list):
                    for item in payloads:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str) and text.strip():
                                texts.append(text.strip())

            content = payload.get("content")
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())

            text = payload.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())

            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                texts.append(message.strip())

        if not texts:
            texts = [response]

        return status if isinstance(status, str) else None, texts

    def _classify_ready_response(self, response: str) -> InitResult:
        if "[READY]" in response:
            return InitResult(True, "READY_MARKER", "Detected explicit [READY] marker")

        status, texts = self._extract_ready_texts(response)
        combined = "\n".join(texts).strip()
        normalized = combined.lower()

        if not normalized:
            details = combined[:500] if combined else response[:500]
            return InitResult(False, "INIT_PROMPT_NO_READY", details)

        blocked_phrases = [
            "can't",
            "cannot",
            "unable",
            "permission denied",
            "authentication failed",
            "auth failed",
            "no access",
            "access denied",
            "not available",
            "[hermes_timeout]",
            "timeout",
            "timed out",
            "api call failed",
            "connection error",
            "network error",
            "service unavailable",
            "error:",
            "traceback",
            "exception",
        ]
        if any(phrase in normalized for phrase in blocked_phrases):
            return InitResult(False, "INIT_PROMPT_ERROR", combined[:500])

        if status in {"error", "failed"}:
            details = combined[:500] if combined else response[:500]
            return InitResult(False, "INIT_PROMPT_ERROR", details)

        ready_phrases = [
            "starting defense phase",
            "initiating defense",
            "initiating defense protocol",
            "starting reconnaissance and hardening",
            "starting reconnaissance",
            "beginning hardening",
            "starting to harden",
            "starting defense",
            "starting hardening",
            "understood. starting",
            "roger that. initiating",
        ]

        leading_texts = texts[:2]
        for text in leading_texts:
            lowered = text.lower()
            for phrase in ready_phrases:
                if phrase in lowered:
                    details = f"Matched fallback ready phrase '{phrase}' in: {text[:240]}"
                    return InitResult(True, "READY_FALLBACK_INTENT", details)

        details = combined[:500] if combined else response[:500]
        return InitResult(True, "READY_NON_ERROR_RESPONSE", details)
    
    async def initialize_agent(
        self,
        session: AgentSession,
        system_prompt: str,
        stream_callback: Optional[StreamCallback] = None,
    ) -> InitResult:
        """
        Initialize the agent: configure container, send system prompt, wait for READY.

        Returns:
            InitResult with success if the agent sent a READY signal.
        """
        session.started_at = datetime.now()
        self._mark_runtime_ready(session)
        session.init_error_reason = None
        session.init_error_details = None

        # 1. Configure container
        logger.info(f"[Player {session.player_id}] Configuring OpenClaw container...")
        config_result = await self.configure_container(session.container_name)
        if not config_result.success:
            session.init_error_reason = config_result.reason
            session.init_error_details = config_result.details
            return config_result
        
        # 2. Send system prompt
        logger.info(f"[Player {session.player_id}] Sending system prompt...")
        # Live-model check is advisory only: OpenClaw's gateway log frequently
        # lags the actual config (it can show the bundled default until the model
        # is exercised on first send). The earlier _wait_for_gateway_config step
        # already logged a warning and decided to continue, so failing hard here
        # blocks every OpenRouter match on a cosmetic log mismatch.
        live_model = await self._read_live_gateway_model(session.container_name)
        if live_model and live_model != self.qualified_model:
            logger.warning(
                f"[Player {session.player_id}] Live model log mismatch "
                f"(log={live_model} cfg={self.qualified_model}); proceeding — "
                f"model is applied on first agent send."
            )

        response = await self.send_message(
            session,
            system_prompt,
            timeout=self.INIT_PROMPT_TIMEOUT,
            stream_callback=stream_callback,
            message_kind="init",
            message_mode=MESSAGE_MODE_NORMAL,
        )
        
        if response is None:
            logger.error(f"[Player {session.player_id}] No response to system prompt")
            session.init_error_reason = "INIT_PROMPT_NO_RESPONSE"
            session.init_error_details = "Agent returned no response to the initialization prompt"
            return InitResult(False, session.init_error_reason, session.init_error_details)
        
        # 3. Detect READY signal
        ready_result = self._classify_ready_response(response)
        if ready_result.success:
            self._mark_init_ready(session)
            if ready_result.reason == "READY_FALLBACK_INTENT":
                logger.info(
                    f"[Player {session.player_id}] READY accepted via fallback: {ready_result.details}"
                )
            else:
                logger.info(f"[Player {session.player_id}] READY signal received")
            return ready_result

        logger.warning(
            f"[Player {session.player_id}] No READY signal in response: "
            f"{response[:200]}"
        )
        session.init_error_reason = ready_result.reason or "INIT_PROMPT_NO_READY"
        session.init_error_details = ready_result.details or response[:500]
        return InitResult(False, session.init_error_reason, session.init_error_details)
    
    async def send_message(
        self,
        session: AgentSession,
        message: str,
        timeout: Optional[int] = None,
        stream_callback: Optional[StreamCallback] = None,
        message_kind: str = "message",
        message_mode: str = MESSAGE_MODE_NORMAL,
        drain_buffered_after: bool = True,
    ) -> Optional[str]:
        """
        Send a message to the agent and wait for a response.

        Uses `openclaw agent -m`; returns content from the JSON response.
        """
        if timeout is None:
            timeout = self.agent_timeout

        if message_mode == MESSAGE_MODE_BUFFERED:
            return await self._send_message_locked(
                session,
                message,
                timeout=timeout,
                stream_callback=stream_callback,
                message_kind=message_kind,
                message_mode=message_mode,
                drain_buffered_after=drain_buffered_after,
            )

        return await self._send_message_locked(
            session,
            message,
            timeout=timeout,
            stream_callback=stream_callback,
            message_kind=message_kind,
            message_mode=message_mode,
            drain_buffered_after=drain_buffered_after,
        )

    async def _send_message_locked(
        self,
        session: AgentSession,
        message: str,
        timeout: int,
        stream_callback: Optional[StreamCallback],
        *,
        message_kind: str,
        message_mode: str,
        drain_buffered_after: bool,
    ) -> Optional[str]:
        response_text: Optional[str] = None

        async with session.send_lock:
            session.in_flight_message_kind = message_kind
            session.in_flight_message_mode = message_mode
            session.in_flight_started_at = time.monotonic()
            self._mark_session_activity(session)

            preview = " ".join(message.split())[:160]
            logger.info(
                f"[Player {session.player_id}] send_message start: "
                f"session_id={session.session_id or 'unknown'} kind={message_kind} mode={message_mode} "
                f"timeout={timeout}s preview={preview}"
            )

            # Base64-encode payload for safe shell passing
            msg_b64 = base64.b64encode(message.encode()).decode()

            cmd = self.build_agent_exec_command(session, msg_b64, timeout)

            try:
                result = await self._exec(
                    session.container_name,
                    cmd,
                    timeout=timeout + 30,
                    stream_callback=stream_callback,
                    session=session,
                    message_kind=message_kind,
                    message_mode=message_mode,
                )
                logger.info(
                    f"[Player {session.player_id}] send_message completed: "
                    f"session_id={session.session_id or 'unknown'} kind={message_kind} mode={message_mode} "
                    f"result_bytes={len(result) if result else 0}"
                )

                session.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "direction": "agent_response",
                    "message_kind": message_kind,
                    "message_mode": message_mode,
                    "content": result[:2000] if result else "(empty)"
                })

                if result:
                    # The openclaw CLI sometimes prefixes its JSON output with plain-text
                    # warnings (e.g. "EMBEDDED FALLBACK: Gateway agent failed; running embedded agent…").
                    # Strip leading non-JSON noise by parsing from the first balanced `{`.
                    def _extract_json_object(text: str):
                        for start in (text.find("{"), text.rfind("\n{")):
                            if start < 0:
                                continue
                            if text[start] != "{":
                                start += 1  # account for the leading newline in rfind path
                            depth = 0
                            in_str = False
                            esc = False
                            for i in range(start, len(text)):
                                ch = text[i]
                                if in_str:
                                    if esc:
                                        esc = False
                                    elif ch == "\\":
                                        esc = True
                                    elif ch == "\"":
                                        in_str = False
                                else:
                                    if ch == "\"":
                                        in_str = True
                                    elif ch == "{":
                                        depth += 1
                                    elif ch == "}":
                                        depth -= 1
                                        if depth == 0:
                                            try:
                                                return json.loads(text[start:i + 1])
                                            except json.JSONDecodeError:
                                                break
                        return None

                    try:
                        try:
                            resp = json.loads(result)
                        except json.JSONDecodeError:
                            resp = _extract_json_object(result)
                            if resp is None:
                                raise
                        # OpenClaw responses use `payloads[].text` for the assistant message;
                        # older shapes used `content`/`text`/`message`. Fall back through both.
                        content = None
                        if isinstance(resp, dict):
                            content = resp.get("content") or resp.get("text") or resp.get("message")
                            if content is None and isinstance(resp.get("payloads"), list) and resp["payloads"]:
                                first = resp["payloads"][0]
                                if isinstance(first, dict):
                                    content = first.get("text") or first.get("content")
                        if content is None:
                            content = result
                        session.last_response = str(content)
                        self._mark_session_activity(session)
                        meta = resp.get("meta") if isinstance(resp, dict) else None
                        agent_meta = meta.get("agentMeta") if isinstance(meta, dict) else None
                        sid = agent_meta.get("sessionId") if isinstance(agent_meta, dict) else None
                        if sid and not session.session_id:
                            session.session_id = sid
                            self._mark_session_ready(session)
                            logger.info(f"[Player {session.player_id}] Session ID captured: {sid}")
                        # R2: extract token usage. The OpenClaw gateway exposes
                        # usage in `meta.agentMeta.usage` (cumulative) and
                        # `meta.agentMeta.lastCallUsage` (per send). We prefer
                        # the per-call number; fall back to OpenAI-style keys.
                        usage = None
                        if isinstance(resp, dict):
                            for candidate in (
                                (agent_meta or {}).get("lastCallUsage") if isinstance(agent_meta, dict) else None,
                                (agent_meta or {}).get("usage") if isinstance(agent_meta, dict) else None,
                                (meta or {}).get("usage") if isinstance(meta, dict) else None,
                                resp.get("usage"),
                            ):
                                if isinstance(candidate, dict):
                                    usage = candidate
                                    break
                        if usage:
                            in_tok = (usage.get("input")
                                      or usage.get("prompt_tokens")
                                      or usage.get("input_tokens") or 0)
                            out_tok = (usage.get("output")
                                       or usage.get("completion_tokens")
                                       or usage.get("output_tokens") or 0)
                            try:
                                session.tokens_input += int(in_tok)
                                session.tokens_output += int(out_tok)
                                session.tokens_messages += 1
                            except (TypeError, ValueError):
                                pass
                        session.last_completed_message_kind = message_kind
                        response_text = session.last_response
                    except json.JSONDecodeError:
                        session.last_response = result
                        self._mark_session_activity(session)
                        session.last_completed_message_kind = message_kind
                        response_text = result

                if result is None:
                    session.last_completed_message_kind = message_kind

            except asyncio.TimeoutError:
                logger.error(
                    f"[Player {session.player_id}] Agent timed out after {timeout}s: "
                    f"session_id={session.session_id or 'unknown'} kind={message_kind} mode={message_mode} "
                    f"partial_stdout={((session.last_partial_stdout or '')[:240])} "
                    f"partial_stderr={((session.last_partial_stderr or '')[:240])}"
                )
                return None
            except Exception as e:
                logger.error(
                    f"[Player {session.player_id}] Agent error: kind={message_kind} mode={message_mode} error={e}"
                )
                return None
            finally:
                session.in_flight_message_kind = None
                session.in_flight_message_mode = None
                session.in_flight_started_at = None

        if drain_buffered_after and not session.buffered_messages_frozen and session.has_buffered_messages:
            await self.drain_buffered_messages(session)

        return response_text

    def build_agent_exec_command(self, session: AgentSession, message_b64: str, timeout: int) -> str:
        return (
            f"sh -c 'echo {message_b64} | base64 -d | "
            f"openclaw agent --agent main -m \"$(cat)\" --json --timeout {timeout}'"
        )
    
    async def send_heartbeat(
        self,
        session: AgentSession,
        update: str,
    ) -> Optional[str]:
        """Send a heartbeat update (shorter timeout)."""
        return await self.send_message(
            session,
            update,
            timeout=60,
            message_kind="heartbeat",
            message_mode=MESSAGE_MODE_NORMAL,
        )
    
    async def send_interrupt(
        self,
        session: AgentSession,
        alert: str,
    ) -> Optional[str]:
        """Send an interrupt-style alert."""
        result = await self.enqueue_buffered_message(
            session,
            f"[ALERT] {alert}",
            timeout=120,
            message_kind="flag_alert",
            dedupe_key="flag_alert",
            merge_strategy="append",
        )
        return None if result in {"queued", "merged"} else session.last_response
    
    async def get_session_log(self, session: AgentSession) -> Optional[str]:
        """Return the agent's full session log."""
        session_file = await self._resolve_session_file(session)
        if session_file is None:
            return None

        log_content = await self._exec(
            session.container_name,
            f"cat {session_file}"
        )
        
        return log_content if log_content.strip() else None
    
    async def check_session_contains(self, session: AgentSession, keyword: str, tail_lines: int = 50) -> bool:
        """Whether the session file's last N lines contain the given keyword."""
        session_file = await self._resolve_session_file(session)
        if session_file is None:
            return False
        
        tail_content = await self._exec(
            session.container_name,
            f"tail -n {tail_lines} {session_file} 2>/dev/null || cat {session_file} 2>/dev/null"
        )

        if not tail_content:
            return False

        if keyword in tail_content:
            return True

        normalized_keyword = self._normalize_session_search_text(keyword)
        normalized_tail_content = self._normalize_session_search_text(tail_content)
        if normalized_keyword and normalized_keyword in normalized_tail_content:
            return True

        full_content = await self._exec(
            session.container_name,
            f"cat {session_file} 2>/dev/null"
        )
        if not full_content:
            return False

        if keyword in full_content:
            return True

        normalized_full_content = self._normalize_session_search_text(full_content)
        return bool(normalized_keyword) and normalized_keyword in normalized_full_content
    
    async def _exec(
        self,
        container_name: str,
        command: str,
        timeout: int = 60,
        stream_callback: Optional[StreamCallback] = None,
        session: Optional[AgentSession] = None,
        message_kind: Optional[str] = None,
        message_mode: Optional[str] = None,
    ) -> str:
        full_cmd = f"docker exec {container_name} {command}"
        proc: Optional[asyncio.subprocess.Process] = None
        started_at = time.monotonic()
        partial_stdout = ""
        partial_stderr = ""

        if session is None and stream_callback is not None:
            session = getattr(stream_callback, "_agent_session", None)

        def _set_partial(stdout_value: str, stderr_value: str):
            nonlocal partial_stdout, partial_stderr
            partial_stdout = stdout_value
            partial_stderr = stderr_value
            if session is not None:
                session.last_partial_stdout = stdout_value[-4000:] if stdout_value else None
                session.last_partial_stderr = stderr_value[-4000:] if stderr_value else None

        def _try_extract_session_id(line: str):
            if session is not None and not session.session_id:
                try:
                    if '"sessionId"' in line:
                        resp = json.loads(line)
                        if isinstance(resp, dict):
                            sid = resp.get("sessionId")
                            if sid:
                                session.session_id = sid
                                self._mark_session_ready(session)
                                logger.info(f"[Player {session.player_id}] Session ID captured from stream: {sid}")
                except (json.JSONDecodeError, AttributeError):
                    pass
        
        try:
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            if proc.stdout is None or proc.stderr is None:
                logger.error(f"[{container_name}] Missing subprocess pipes for command: {command[:80]}")
                return ""
            stdout_pipe = proc.stdout
            stderr_pipe = proc.stderr
            
            output_lines = []
            
            async def _safe_readline(pipe: asyncio.StreamReader) -> bytes:
                """
                readline() raises ValueError ("Separator is found, but chunk is longer than limit")
                when a single line exceeds the StreamReader's 64KB buffer — common when the
                openclaw agent streams large JSON trace events. Recover by draining the
                buffered prefix via read() and synthesizing a newline so the loop continues.
                """
                while True:
                    try:
                        return await pipe.readline()
                    except ValueError as overflow:
                        chunk = pipe._buffer if hasattr(pipe, "_buffer") else b""
                        # Drop the over-sized fragment; the agent's stream continues with
                        # the next line. We log once per overflow instead of every 2s.
                        try:
                            pipe._buffer.clear()  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        logger.debug(f"stream overflow ({overflow}); dropped {len(chunk)} buffered bytes")
                        return b"\n"

            async def read_stdout():
                while True:
                    line = await _safe_readline(stdout_pipe)
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if decoded:
                        output_lines.append(decoded)
                        if session is not None:
                            self._mark_session_activity(session)
                        _set_partial("\n".join(output_lines), partial_stderr)
                        _try_extract_session_id(decoded)
                        if stream_callback:
                            if asyncio.iscoroutinefunction(stream_callback):
                                await stream_callback(decoded)
                            else:
                                stream_callback(decoded)

            async def read_stderr():
                stderr_lines = []
                while True:
                    line = await _safe_readline(stderr_pipe)
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if decoded:
                        stderr_lines.append(decoded)
                        if session is not None:
                            self._mark_session_activity(session)
                        _set_partial(partial_stdout, "\n".join(stderr_lines))
                        if stream_callback:
                            if asyncio.iscoroutinefunction(stream_callback):
                                await stream_callback(f"[stderr] {decoded}")
                            else:
                                stream_callback(f"[stderr] {decoded}")
                return "\n".join(stderr_lines)
                
            stdout_task = asyncio.create_task(read_stdout())
            stderr_task = asyncio.create_task(read_stderr())
            
            await asyncio.wait_for(
                asyncio.gather(proc.wait(), stdout_task, stderr_task),
                timeout=timeout
            )
            
            stderr_out = stderr_task.result()
            output = "\n".join(output_lines)
            
            if proc.returncode != 0 and stderr_out:
                if stderr_out:
                    logger.debug(f"[{container_name}] stderr: {stderr_out[:200]}")

            logger.info(
                f"[{container_name}] exec completed in {time.monotonic() - started_at:.1f}s "
                f"rc={proc.returncode} stdout_bytes={len(output)} stderr_bytes={len(stderr_out)} "
                f"player_id={session.player_id if session else 'unknown'} "
                f"session_id={session.session_id if session and session.session_id else 'unknown'} "
                f"message_kind={message_kind or 'unknown'} message_mode={message_mode or 'unknown'}"
            )
            
            return output
            
        except asyncio.TimeoutError:
            logger.error(
                f"[{container_name}] Command timed out after {timeout}s: cmd={command[:80]} "
                f"player_id={session.player_id if session else 'unknown'} "
                f"session_id={session.session_id if session and session.session_id else 'unknown'} "
                f"message_kind={message_kind or 'unknown'} message_mode={message_mode or 'unknown'} "
                f"command_age={time.monotonic() - started_at:.1f}s "
                f"stdout_preview={partial_stdout[:240]} stderr_preview={partial_stderr[:240]}"
            )
            if proc is not None:
                try:
                    logger.error(
                        f"[{container_name}] referee-engine outer kill: "
                        f"player_id={session.player_id if session else 'unknown'} "
                        f"session_id={session.session_id if session and session.session_id else 'unknown'} "
                        f"message_kind={message_kind or 'unknown'} message_mode={message_mode or 'unknown'}"
                    )
                    proc.kill()
                except ProcessLookupError:
                    pass
            raise
        except Exception as e:
            logger.error(f"[{container_name}] exec error: {e}")
            return ""
    
    async def _exec_as_root(
        self,
        container_name: str,
        command: str,
        timeout: int = 30,
    ) -> str:
        full_cmd = f"docker exec -u root {container_name} {command}"
        try:
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            return stdout.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.error(f"[{container_name}] exec_as_root error: {e}")
            return ""


class PromptRenderer:
    _PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

    _templates: Dict[str, str] = {}

    @classmethod
    def _load(cls, name: str) -> str:
        if name not in cls._templates:
            path = os.path.join(cls._PROMPTS_DIR, f"{name}.txt")
            with open(path, encoding="utf-8") as f:
                cls._templates[name] = f.read()
        return cls._templates[name]

    @classmethod
    def render_defense_init(
        cls,
        player_id: int,
        own_target_ip: str,
        target_port: int,
        maintenance_auth_mode: str,
        maintenance_helper_command: str,
        referee_api_url: str,
        scoring: Dict[str, int],
        flag_refresh_interval: int = 300,
        defense_duration: int = 600,
        attack_duration: int = 600,
    ) -> str:
        """Render the defense-phase initialization prompt."""
        return cls._load("defense_init").format(
            PLAYER_ID=player_id,
            OWN_TARGET_IP=own_target_ip,
            TARGET_PORT=target_port,
            MAINTENANCE_AUTH_MODE=maintenance_auth_mode,
            MAINTENANCE_HELPER_COMMAND=maintenance_helper_command,
            REFEREE_API_URL=referee_api_url,
            ATTACK_SCORE=scoring.get("attackSuccess", 100),
            DEFENSE_SCORE=scoring.get("defenseFailure", -50),
            SLA_SCORE=scoring.get("slaViolation", -50),
            FLAG_REFRESH_INTERVAL=flag_refresh_interval,
            DEFENSE_DURATION=defense_duration,
            ATTACK_DURATION=attack_duration,
        )

    @classmethod
    def render_attack_start(
        cls,
        player_id: int,
        enemy_targets: List[Dict[str, Any]],
        target_port: int,
        referee_api_url: str,
        player_status_url: str,
        player_read_token: str,
        scoring: Dict[str, int],
        flag_refresh_interval: int = 300,
        attack_duration: int = 600,
    ) -> str:
        """Render the attack-phase start prompt."""
        enemy_list = "\n".join(
            f"- Player {t.get('player_id', i + 1)}: {t['ip']}:{t.get('port', target_port)}"
            for i, t in enumerate(enemy_targets)
        )
        if not enemy_list:
            enemy_list = "- No enemies found"

        return cls._load("attack_start").format(
            PLAYER_ID=player_id,
            ENEMY_TARGET_LIST=enemy_list,
            REFEREE_API_URL=referee_api_url,
            PLAYER_STATUS_URL=player_status_url,
            PLAYER_READ_TOKEN=player_read_token,
            ATTACK_SCORE=scoring.get("attackSuccess", 100),
            DEFENSE_SCORE=scoring.get("defenseFailure", -50),
            SLA_SCORE=scoring.get("slaViolation", -50),
            FLAG_REFRESH_INTERVAL=flag_refresh_interval,
            ATTACK_DURATION=attack_duration,
        )

    @classmethod
    def render_solo_prompt(
        cls,
        player_id: int,
        target_ip: str,
        target_port: int,
        referee_api_url: str,
    ) -> str:
        """Render the solo CTF mode prompt."""
        return cls._load("solo_ctf").format(
            PLAYER_ID=player_id,
            TARGET_IP=target_ip,
            TARGET_PORT=target_port,
            REFEREE_API_URL=referee_api_url,
        )
