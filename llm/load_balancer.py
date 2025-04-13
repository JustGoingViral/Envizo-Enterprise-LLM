import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_async_db_ctx
from models import ServerNode, ServerLoadMetrics
from utils import check_server_health, update_server_health, get_server_load_metrics

logger = logging.getLogger(__name__)

class LLMLoadBalancer:
    """Load balancer for distributing requests across LLM servers"""

    def __init__(self):
        self.servers = []  # List of available servers
        self.server_metrics = {}  # Cache of server metrics
        self.last_server_index = -1  # For round-robin strategy
        self.initialized = False
        self.load_balancing_strategy = settings.LOAD_BALANCER_STRATEGY

    async def initialize(self):
        """Initialize the load balancer by loading servers and checking health"""
        if self.initialized:
            return

        logger.info("Initializing LLM Load Balancer")
        await self.refresh_servers()

        # Start background tasks
        asyncio.create_task(self.health_check_loop())
        asyncio.create_task(self.metrics_collection_loop())

        self.initialized = True
        logger.info(f"Load Balancer initialized with {len(self.servers)} servers")

    async def refresh_servers(self):
        """Refresh the list of available servers from the database"""
        from sqlalchemy import select

        async with get_async_db_ctx() as db:
            result = await db.execute(
                select(ServerNode).where(ServerNode.is_active == True)
            )
            self.servers = list(result.scalars().all())

            # Initialize server metrics
            for server in self.servers:
                if server.id not in self.server_metrics:
                    self.server_metrics[server.id] = {
                        "gpu_utilization": 0.0,
                        "gpu_memory_used": 0.0,
                        "gpu_memory_total": server.gpu_memory,
                        "cpu_utilization": 0.0,
                        "active_requests": 0,
                        "queue_depth": 0,
                        "last_updated": time.time()
                    }

            logger.info(f"Refreshed servers: {len(self.servers)} active servers")

    async def health_check_loop(self):
        """Background task to periodically check server health"""
        while True:
            try:
                await self._check_all_servers_health()
                # Wait before next health check
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                await asyncio.sleep(10)  # Shorter wait on error

    async def _check_all_servers_health(self):
        """Check health for all servers"""
        logger.debug("Checking health for all servers")
        async with get_async_db_ctx() as db:
            for server in self.servers:
                healthy, status = await check_server_health(server)
                await update_server_health(db, server.id, status)

                if not healthy and server.health_status != status:
                    logger.warning(f"Server {server.name} is unhealthy: {status}")

            # Refresh server list after health checks
            await self.refresh_servers()

    async def metrics_collection_loop(self):
        """Background task to periodically collect server metrics"""
        while True:
            try:
                await self._collect_all_server_metrics()
                # Wait before next metrics collection
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}")
                await asyncio.sleep(10)  # Shorter wait on error

    async def _collect_all_server_metrics(self):
        """Collect metrics from all servers"""
        logger.debug("Collecting metrics from all servers")
        async with get_async_db_ctx() as db:
            for server in self.servers:
                # Skip unhealthy servers
                if server.health_status != "healthy":
                    continue

                # Get metrics from server
                metrics = await get_server_load_metrics(server)

                # Update metrics cache
                self.server_metrics[server.id] = {
                    **metrics,
                    "last_updated": time.time()
                }

                # Store metrics in database
                from models import ServerLoadMetrics

                db_metrics = ServerLoadMetrics(
                    server_id=server.id,
                    gpu_utilization=metrics.get("gpu_utilization", 0.0),
                    gpu_memory_used=metrics.get("gpu_memory_used", 0.0),
                    gpu_memory_total=metrics.get("gpu_memory_total", server.gpu_memory),
                    cpu_utilization=metrics.get("cpu_utilization", 0.0),
                    active_requests=metrics.get("active_requests", 0),
                    queue_depth=metrics.get("queue_depth", 0)
                )

                db.add(db_metrics)

            await db.commit()

    async def get_server(self, model_name: str) -> Optional[ServerNode]:
        """
        Get the best server for a specific model based on the load balancing strategy

        Strategies:
        - round_robin: Simple round-robin distribution
        - least_load: Server with lowest load
        - gpu_memory: Server with most available GPU memory
        """
        # Ensure we have servers
        if not self.servers:
            await self.refresh_servers()

        # Filter servers by health status
        healthy_servers = [s for s in self.servers if s.health_status == "healthy"]

        if not healthy_servers:
            logger.error("No healthy servers available")
            return None

        # Use the selected load balancing strategy
        if self.load_balancing_strategy == "round_robin":
            return await self._round_robin_strategy(healthy_servers)
        elif self.load_balancing_strategy == "least_load":
            return await self._least_load_strategy(healthy_servers)
        elif self.load_balancing_strategy == "gpu_memory":
            return await self._gpu_memory_strategy(healthy_servers)
        else:
            # Default to round-robin
            return await self._round_robin_strategy(healthy_servers)

    async def _round_robin_strategy(self, servers: List[ServerNode]) -> ServerNode:
        """Simple round-robin server selection"""
        self.last_server_index = (self.last_server_index + 1) % len(servers)
        return servers[self.last_server_index]

    async def _least_load_strategy(self, servers: List[ServerNode]) -> ServerNode:
        """Select server with the least load (active requests + queue)"""
        min_load = float('inf')
        selected_server = None

        for server in servers:
            metrics = self.server_metrics.get(server.id, {})
            load = metrics.get("active_requests", 0) + metrics.get("queue_depth", 0)

            if load < min_load:
                min_load = load
                selected_server = server

        # Fallback to first server if no metrics available
        if selected_server is None:
            selected_server = servers[0]

        return selected_server

    async def _gpu_memory_strategy(self, servers: List[ServerNode]) -> ServerNode:
        """Select server with most available GPU memory"""
        max_available_memory = -1
        selected_server = None

        for server in servers:
            metrics = self.server_metrics.get(server.id, {})
            total_memory = metrics.get("gpu_memory_total", server.gpu_memory)
            used_memory = metrics.get("gpu_memory_used", 0)
            available_memory = total_memory - used_memory

            if available_memory > max_available_memory:
                max_available_memory = available_memory
                selected_server = server

        # Fallback to first server if no metrics available
        if selected_server is None:
            selected_server = servers[0]

        return selected_server

    async def get_all_servers_status(self) -> List[Dict[str, Any]]:
        """Get status of all servers for dashboard"""
        server_status = []

        for server in self.servers:
            metrics = self.server_metrics.get(server.id, {})

            server_status.append({
                "id": server.id,
                "name": server.name,
                "host": server.host,
                "port": server.port,
                "gpu_count": server.gpu_count,
                "gpu_memory": server.gpu_memory,
                "health_status": server.health_status,
                "last_health_check": server.last_health_check,
                "gpu_utilization": metrics.get("gpu_utilization", 0.0),
                "gpu_memory_used": metrics.get("gpu_memory_used", 0.0),
                "gpu_memory_total": metrics.get("gpu_memory_total", server.gpu_memory),
                "active_requests": metrics.get("active_requests", 0),
                "queue_depth": metrics.get("queue_depth", 0),
                "last_metrics_update": metrics.get("last_updated")
            })

        return server_status