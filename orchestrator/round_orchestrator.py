"""
Docker round orchestrator — container lifecycle for matches.

Validated OpenClaw container assumptions:
- Agent: openclaw/awd-openclaw-agent:latest (see ../agent-image/Dockerfile); OpenRouter uses the `openai` provider slot with a custom `baseUrl`.
- Target: openclaw/ctf-target:v1
- Custom provider must be set in openclaw.json with `"api": "openai-completions"` or requests may fail
- Containers need HTTPS_PROXY to reach external LLM APIs
- Gateway starts with the container; it reloads after config writes
"""
import docker
import json
import time
import logging
import os
import secrets
import hashlib
import asyncio
import base64
from typing import Dict, List, Optional, Any, Tuple, cast
from dataclasses import dataclass, field
from datetime import datetime
from docker.errors import APIError, NotFound
from docker.types import IPAMConfig, IPAMPool


CONTAINER_RESTART_POLICY = cast(Any, {"Name": "always"})


def _require_container_id(container_id: Optional[str], container_name: str) -> str:
    if container_id is None:
        raise RuntimeError(f"Container {container_name} returned no container id")
    return container_id


logger = logging.getLogger(__name__)

CONTAINER_TIMEZONE = "Asia/Shanghai"


@dataclass
class ContainerInfo:
    """Metadata for one container."""
    name: str
    container_id: str
    ip_address: str
    role: str           # "agent" or "target"
    player_id: int
    status: str = "created"


@dataclass
class ArenaTopology:
    """Arena network + container map."""
    match_id: str
    network_name: str
    containers: Dict[str, ContainerInfo] = field(default_factory=dict)
    created_at: Optional[datetime] = None


class RoundOrchestrator:
    """
    Manages all containers for one match.

    Two styles:
    1. Sync: create_round() / destroy_round() (legacy)
    2. Async: async_create_arena() / async_destroy_arena() (preferred)
    """

    # Default images used when config omits overrides
    DEFAULT_AGENT_IMAGE = "openclaw/awd-openclaw-agent:latest"
    DEFAULT_TARGET_IMAGE = "openclaw/ctf-target:v1"
    
    # OpenClaw config path inside agent containers
    OPENCLAW_CONFIG_PATH = "/home/node/.openclaw/openclaw.json"
    
    def __init__(self, match_id: str, config: dict):
        self.match_id = match_id
        self.config = config
        self.client = docker.from_env()
        self.topology = ArenaTopology(match_id=match_id, network_name=f"awd_{match_id}")
        self.logger = logging.getLogger(f"Orchestrator-{match_id}")
    
    # ==================== Async API (preferred) ====================
    
    async def async_create_arena(self) -> ArenaTopology:
        """
        Create the full arena asynchronously.

        For each player:
        - One OpenClaw agent container
        - One CTF target container

        Returns:
            ArenaTopology with container metadata
        """
        # Create Docker network
        network = self._create_network()
        
        players = self.config.get("players", [])
        llm_config = self.config.get("llm", {})
        proxy_url = llm_config.get("proxy", "http://host.docker.internal:7897")
        
        for player in players:
            pid = player["id"]
            
            # Target VM
            target_info = self._create_target_container(pid, network)
            self.topology.containers[target_info.name] = target_info
            
            # Player agent container
            agent_info = self._create_agent_container(pid, player, llm_config, proxy_url, network)
            self.topology.containers[agent_info.name] = agent_info
        
        # Wait for containers to boot
        await asyncio.sleep(5)
        
        # Refresh container IPs
        self._refresh_ips()
        
        # Wait for target HTTP health
        await self._async_wait_for_targets()
        
        self.topology.created_at = datetime.now()
        self.logger.info(
            f"Arena created: {len(players)} players, "
            f"{len(self.topology.containers)} containers"
        )
        
        return self.topology
    
    async def async_destroy_arena(self, archive_logs: bool = True):
        """Tear down the arena asynchronously."""
        if archive_logs:
            await self._async_archive_logs()
        
        # Stop and remove containers
        for name, info in self.topology.containers.items():
            try:
                container = self.client.containers.get(name)
                container.stop(timeout=10)
                container.remove()
                self.logger.info(f"Removed: {name}")
            except NotFound:
                pass
            except Exception as e:
                self.logger.warning(f"Failed to remove {name}: {e}")
        
        # Remove Docker network
        try:
            network = self.client.networks.get(self.topology.network_name)
            network.remove()
            self.logger.info(f"Removed network: {self.topology.network_name}")
        except NotFound:
            pass
    
    async def async_configure_agent(
        self,
        container_name: str,
        llm_api_key: str,
        llm_base_url: str = "",
        llm_model: str = "claude-sonnet-4-6",
    ) -> bool:
        """
        Configure the OpenClaw agent LLM provider.

        Writes openclaw.json. Critical fields:
        - `"api": "openai-completions"` (required; otherwise WAF/403 issues)
        - Preserve existing gateway.auth.token
        """
        # Wait for Gateway to materialize config
        for _ in range(15):
            proc = await asyncio.create_subprocess_shell(
                f"docker exec {container_name} test -f {self.OPENCLAW_CONFIG_PATH} && echo ok",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if stdout.decode().strip() == "ok":
                break
            await asyncio.sleep(2)
        else:
            self.logger.error(f"[{container_name}] Config file not created")
            return False
        
        # Read existing config
        proc = await asyncio.create_subprocess_shell(
            f"docker exec {container_name} cat {self.OPENCLAW_CONFIG_PATH}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        
        try:
            existing = json.loads(stdout.decode())
        except json.JSONDecodeError:
            existing = {}
        
        # Preserve gateway token
        gateway_token = existing.get("gateway", {}).get("auth", {}).get("token", "")
        
        new_config = {
            "gateway": existing.get("gateway", {}),
            "agents": {"defaults": {"model": llm_model}},
            "models": {
                "mode": "merge",
                "providers": {
                    "routerss": {
                        "apiKey": llm_api_key,
                        "api": "openai-completions",
                        "models": [{"id": llm_model, "name": llm_model}],
                    }
                }
            }
        }

        if llm_base_url:
            new_config["models"]["providers"]["routerss"]["baseUrl"] = llm_base_url
        
        if gateway_token:
            new_config.setdefault("gateway", {}).setdefault("auth", {})["token"] = gateway_token
        
        import tempfile
        config_json = json.dumps(new_config, indent=2)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(config_json)
            tmp_path = f.name
        
        try:
            proc = await asyncio.create_subprocess_shell(
                f"docker cp {tmp_path} {container_name}:{self.OPENCLAW_CONFIG_PATH}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        finally:
            os.unlink(tmp_path)
        
        await asyncio.sleep(5)
        
        # Verify write
        proc = await asyncio.create_subprocess_shell(
            f"docker exec {container_name} cat {self.OPENCLAW_CONFIG_PATH}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        verify = stdout.decode()
        
        if llm_model in verify and "openai-completions" in verify:
            self.logger.info(f"[{container_name}] Configured: model={llm_model}")
            return True
        
        self.logger.error(f"[{container_name}] Config verification failed")
        return False
    
    # ==================== Sync API (legacy) ====================
    
    def create_round(self) -> None:
        """Create arena synchronously (legacy API)."""
        network = self._create_network()
        
        players = self.config.get("players", [])
        llm_config = self.config.get("llm", {})
        proxy_url = llm_config.get("proxy", "http://host.docker.internal:7897")
        
        for player in players:
            pid = player["id"]
            self._create_target_container(pid, network)
            self._create_agent_container(pid, player, llm_config, proxy_url, network)
        
        self._refresh_ips()
        self._sync_wait_for_targets()
        
        self.topology.created_at = datetime.now()
        self.logger.info(f"Round created with {len(players)} players")
    
    def destroy_round(self) -> None:
        """Destroy arena synchronously."""
        self._sync_archive_logs()
        
        for name in list(self.topology.containers.keys()):
            try:
                container = self.client.containers.get(name)
                container.stop(timeout=10)
                container.remove()
            except Exception as e:
                self.logger.warning(f"Failed to remove {name}: {e}")
        
        try:
            network = self.client.networks.get(self.topology.network_name)
            network.remove()
        except NotFound:
            pass
    
    # ==================== Internal helpers ====================
    
    def _create_network(self):
        """Create the Docker network."""
        try:
            match_hash = int(hashlib.md5(self.match_id.encode()).hexdigest()[:4], 16) % 256
            subnet = f"10.201.{match_hash}.0/24"
            gateway = f"10.201.{match_hash}.1"
            
            ipam_pool = IPAMPool(subnet=subnet, gateway=gateway)
            ipam_config = IPAMConfig(pool_configs=[ipam_pool])
            
            network = self.client.networks.create(
                self.topology.network_name,
                driver="bridge",
                check_duplicate=True,
                ipam=ipam_config
            )
            self.logger.info(f"Created network: {self.topology.network_name} with subnet {subnet}")
            return network
        except APIError as e:
            if "already exists" in str(e):
                return self.client.networks.get(self.topology.network_name)
            raise
    
    def _create_target_container(self, player_id: int, network) -> ContainerInfo:
        """Create the target container."""
        name = f"target_{self.match_id}_{player_id}"
        maintenance_password = secrets.token_urlsafe(12)
        
        # Per-vuln placeholder flags in env
        flags = {
            f"FLAG_{i}": f"FLAG{{{secrets.token_hex(16)}}}"
            for i in range(1, 6)
        }
        flags["TZ"] = CONTAINER_TIMEZONE
        flags["MAINTENANCE_USERNAME"] = "defender"
        flags["MAINTENANCE_PASSWORD"] = maintenance_password
        
        container = self.client.containers.run(
            self.config.get("target_image", self.DEFAULT_TARGET_IMAGE),
            name=name,
            hostname=f"target_{player_id}",
            network=network.name,
            environment=flags,
            detach=True,
            mem_limit="1g",
            restart_policy=CONTAINER_RESTART_POLICY,
            labels={
                "awd.match_id": self.match_id,
                "awd.player_id": str(player_id),
                "awd.role": "target",
            },
        )
        
        info = ContainerInfo(
            name=name,
            container_id=_require_container_id(container.id, name),
            ip_address="",  # filled after refresh
            role="target",
            player_id=player_id,
        )
        
        self.logger.info(f"Created target: {name}")
        return info
    
    def _create_agent_container(
        self,
        player_id: int,
        player_config: dict,
        llm_config: dict,
        proxy_url: str,
        network,
    ) -> ContainerInfo:
        """Create the agent container."""
        name = f"claw_{self.match_id}_{player_id}"
        
        env = {
            "OPENAI_API_KEY": player_config.get("apiKey") or llm_config.get("apiKey", ""),
            "HTTPS_PROXY": proxy_url,
            "HTTP_PROXY": proxy_url,
            "NO_PROXY": "localhost,127.0.0.1,172.16.0.0/12,10.0.0.0/8,host.docker.internal,.local",
            "TZ": CONTAINER_TIMEZONE,
        }
        
        container = self.client.containers.run(
            self.config.get("agent_image", self.DEFAULT_AGENT_IMAGE),
            name=name,
            hostname=f"claw_{player_id}",
            network=network.name,
            environment=env,
            detach=True,
            mem_limit="2g",
            restart_policy=CONTAINER_RESTART_POLICY,
            labels={
                "awd.match_id": self.match_id,
                "awd.player_id": str(player_id),
                "awd.role": "agent",
            },
        )
        
        info = ContainerInfo(
            name=name,
            container_id=_require_container_id(container.id, name),
            ip_address="",
            role="agent",
            player_id=player_id,
        )
        
        self.logger.info(f"Created agent: {name}")
        return info
    
    def _refresh_ips(self):
        """Refresh cached IPs for all containers."""
        for name, info in self.topology.containers.items():
            try:
                container = self.client.containers.get(name)
                container.reload()
                networks = container.attrs["NetworkSettings"]["Networks"]
                
                if self.topology.network_name in networks:
                    info.ip_address = networks[self.topology.network_name]["IPAddress"]
                    info.status = "running"
                    
            except Exception as e:
                self.logger.warning(f"Failed to get IP for {name}: {e}")
    
    def _sync_wait_for_targets(self, timeout: int = 60):
        """Block until targets answer HTTP /health (sync)."""
        import subprocess
        
        targets = [
            info for info in self.topology.containers.values()
            if info.role == "target"
        ]
        
        start = time.time()
        for target in targets:
            while time.time() - start < timeout:
                try:
                    result = subprocess.run(
                        f"docker exec {target.name} curl -sf http://localhost:3000/health",
                        shell=True, capture_output=True, timeout=5,
                    )
                    if result.returncode == 0:
                        self.logger.info(f"Target {target.name} ready")
                        break
                except Exception:
                    pass
                time.sleep(2)
    
    async def _async_wait_for_targets(self, timeout: int = 60):
        """Block until targets answer HTTP /health (async)."""
        targets = [
            info for info in self.topology.containers.values()
            if info.role == "target"
        ]
        
        for target in targets:
            for _ in range(timeout // 2):
                try:
                    proc = await asyncio.create_subprocess_shell(
                        f"docker exec {target.name} curl -sf http://localhost:3000/health",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=5)
                    if proc.returncode == 0:
                        self.logger.info(f"Target {target.name} ready")
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)
    
    def _sync_archive_logs(self):
        """Archive container logs to disk (sync)."""
        archive_dir = f"./logs/{self.match_id}"
        os.makedirs(archive_dir, exist_ok=True)
        
        for name, info in self.topology.containers.items():
            try:
                container = self.client.containers.get(name)
                logs = container.logs(stdout=True, stderr=True, timestamps=True)
                
                with open(f"{archive_dir}/{name}.log", "wb") as f:
                    f.write(logs)
                    
            except Exception as e:
                self.logger.warning(f"Failed to archive logs for {name}: {e}")
    
    async def _async_archive_logs(self):
        """Archive container logs to disk (async)."""
        archive_dir = f"./logs/{self.match_id}"
        os.makedirs(archive_dir, exist_ok=True)
        
        for name, info in self.topology.containers.items():
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"docker logs {name} 2>&1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                
                with open(f"{archive_dir}/{name}.log", "wb") as f:
                    f.write(stdout)
                    
            except Exception as e:
                self.logger.warning(f"Failed to archive logs for {name}: {e}")
    
    # ==================== Query helpers ====================
    
    def get_container_stats(self) -> Dict[int, dict]:
        """CPU/memory stats for all agent containers."""
        stats = {}
        
        for name, info in self.topology.containers.items():
            if info.role != "agent":
                continue
            
            try:
                container = self.client.containers.get(name)
                container.reload()
                
                raw_stats = cast(dict[str, Any], container.stats(stream=False))
                
                cpu_delta = (
                    raw_stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    - raw_stats["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                system_delta = (
                    raw_stats["cpu_stats"]["system_cpu_usage"]
                    - raw_stats["precpu_stats"]["system_cpu_usage"]
                )
                cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
                
                mem = raw_stats["memory_stats"]
                
                stats[info.player_id] = {
                    "status": container.status,
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_mb": round(mem["usage"] / (1024 * 1024), 1),
                    "memory_limit_mb": round(mem["limit"] / (1024 * 1024), 1),
                    "ip_address": info.ip_address,
                }
                
            except Exception as e:
                stats[info.player_id] = {"error": str(e)}
        
        return stats
    
    def get_target_info(self) -> Dict[int, dict]:
        """Basic info for all target containers."""
        targets = {}
        for name, info in self.topology.containers.items():
            if info.role == "target":
                targets[info.player_id] = {
                    "container_name": info.name,
                    "ip_address": info.ip_address,
                    "status": info.status,
                }
        return targets
