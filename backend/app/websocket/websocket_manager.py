import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.core.logging import get_logger
from app.models.schemas import ProcessingUpdate, WebSocketMessage


class MessageType(str, Enum):
    """WebSocket message types"""

    # Connection management
    CONNECTION_ACK = "connection_ack"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

    # Processing updates
    PROCESSING_START = "processing_start"
    PROCESSING_UPDATE = "processing_update"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_ERROR = "processing_error"

    # Agent responses
    AGENT_RESPONSE = "agent_response"
    AGENT_THINKING = "agent_thinking"
    AGENT_ERROR = "agent_error"

    # Graph updates
    GRAPH_UPDATE = "graph_update"
    GRAPH_NODE_ADDED = "graph_node_added"
    GRAPH_EDGE_ADDED = "graph_edge_added"

    # General notifications
    NOTIFICATION = "notification"


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.topic_subscriptions: Dict[str, Set[str]] = {}
        self.logger = get_logger("websocket_manager")

        # Start heartbeat task
        self.heartbeat_task = None
        self.heartbeat_interval = 30  # seconds

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": datetime.utcnow(),
            "subscriptions": set(),
            "user_id": None,
        }

        # Send connection acknowledgment
        await self.send_message(
            connection_id,
            MessageType.CONNECTION_ACK,
            {
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat(),
            },
        )

        self.logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            total_connections=len(self.active_connections),
        )

        # Start heartbeat if this is the first connection
        if len(self.active_connections) == 1 and not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return connection_id

    async def disconnect(self, connection_id: str):
        """Handle connection disconnect"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]

            # Close websocket if still open
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    self.logger.warning("Error closing WebSocket", error=str(e))

            # Clean up subscriptions
            metadata = self.connection_metadata.get(connection_id, {})
            for topic in metadata.get("subscriptions", []):
                if topic in self.topic_subscriptions:
                    self.topic_subscriptions[topic].discard(connection_id)
                    if not self.topic_subscriptions[topic]:
                        del self.topic_subscriptions[topic]

            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_metadata[connection_id]

            self.logger.info(
                "WebSocket connection closed",
                connection_id=connection_id,
                total_connections=len(self.active_connections),
            )

            # Stop heartbeat if no connections remain
            if not self.active_connections and self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None

    async def send_message(
        self, connection_id: str, message_type: MessageType, data: Dict[str, Any]
    ) -> bool:
        """Send message to specific connection"""
        if connection_id not in self.active_connections:
            self.logger.warning(
                "Attempted to send message to non-existent connection",
                connection_id=connection_id,
            )
            return False

        websocket = self.active_connections[connection_id]

        if websocket.client_state != WebSocketState.CONNECTED:
            self.logger.warning(
                "Attempted to send message to disconnected WebSocket",
                connection_id=connection_id,
            )
            await self.disconnect(connection_id)
            return False

        try:
            message = WebSocketMessage(type=message_type.value, data=data)

            await websocket.send_text(
                json.dumps(
                    {
                        "type": message.type,
                        "data": message.data,
                        "timestamp": message.timestamp.isoformat(),
                    }
                )
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to send WebSocket message",
                connection_id=connection_id,
                error=str(e),
            )
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message_type: MessageType, data: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected_connections = []

        for connection_id in list(self.active_connections.keys()):
            success = await self.send_message(connection_id, message_type, data)
            if not success:
                disconnected_connections.append(connection_id)

        # Clean up failed connections
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)

        self.logger.debug(
            "Broadcasted message",
            message_type=message_type.value,
            recipients=len(self.active_connections),
            failed=len(disconnected_connections),
        )

    async def send_to_topic(
        self, topic: str, message_type: MessageType, data: Dict[str, Any]
    ):
        """Send message to all connections subscribed to a topic"""
        if topic not in self.topic_subscriptions:
            return

        subscribers = list(self.topic_subscriptions[topic])
        successful_sends = 0

        for connection_id in subscribers:
            success = await self.send_message(connection_id, message_type, data)
            if success:
                successful_sends += 1

        self.logger.debug(
            "Sent message to topic",
            topic=topic,
            subscribers=len(subscribers),
            successful=successful_sends,
        )

    async def subscribe_to_topic(self, connection_id: str, topic: str):
        """Subscribe a connection to a topic"""
        if connection_id not in self.active_connections:
            return False

        if topic not in self.topic_subscriptions:
            self.topic_subscriptions[topic] = set()

        self.topic_subscriptions[topic].add(connection_id)
        self.connection_metadata[connection_id]["subscriptions"].add(topic)

        self.logger.debug(
            "Connection subscribed to topic", connection_id=connection_id, topic=topic
        )
        return True

    async def unsubscribe_from_topic(self, connection_id: str, topic: str):
        """Unsubscribe a connection from a topic"""
        if topic in self.topic_subscriptions:
            self.topic_subscriptions[topic].discard(connection_id)
            if not self.topic_subscriptions[topic]:
                del self.topic_subscriptions[topic]

        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].discard(topic)

        self.logger.debug(
            "Connection unsubscribed from topic",
            connection_id=connection_id,
            topic=topic,
        )

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to all connections"""
        while self.active_connections:
            try:
                await self.broadcast(
                    MessageType.HEARTBEAT,
                    {
                        "server_time": datetime.utcnow().isoformat(),
                        "active_connections": len(self.active_connections),
                    },
                )

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Heartbeat loop error", error=str(e))
                await asyncio.sleep(5)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        now = datetime.utcnow()

        connection_ages = []
        for metadata in self.connection_metadata.values():
            age = (now - metadata["connected_at"]).total_seconds()
            connection_ages.append(age)

        return {
            "total_connections": len(self.active_connections),
            "total_topics": len(self.topic_subscriptions),
            "average_connection_age": (
                sum(connection_ages) / len(connection_ages) if connection_ages else 0
            ),
            "topics": {
                topic: len(subscribers)
                for topic, subscribers in self.topic_subscriptions.items()
            },
        }


# Global connection manager instance
connection_manager = ConnectionManager()


class ProcessingNotifier:
    """Handles processing-related WebSocket notifications"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.logger = get_logger("processing_notifier")
        self.active_processes: Dict[str, Dict[str, Any]] = {}

    async def start_processing(
        self,
        processing_id: str,
        process_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Notify start of processing"""
        self.active_processes[processing_id] = {
            "type": process_type,
            "started_at": datetime.utcnow(),
            "metadata": metadata or {},
        }

        await self.manager.send_to_topic(
            f"processing:{processing_id}",
            MessageType.PROCESSING_START,
            {
                "processing_id": processing_id,
                "process_type": process_type,
                "metadata": metadata or {},
            },
        )

        self.logger.info(
            "Processing started notification sent",
            processing_id=processing_id,
            process_type=process_type,
        )

    async def update_progress(
        self,
        processing_id: str,
        progress: float,
        message: str,
        step: Optional[str] = None,
    ):
        """Send processing progress update"""
        if processing_id not in self.active_processes:
            self.logger.warning(
                "Progress update for unknown process", processing_id=processing_id
            )
            return

        update = ProcessingUpdate(
            processing_id=processing_id,
            status="processing",
            progress=progress,
            message=message,
        )

        await self.manager.send_to_topic(
            f"processing:{processing_id}",
            MessageType.PROCESSING_UPDATE,
            {
                "processing_id": processing_id,
                "progress": progress,
                "message": message,
                "step": step,
                "timestamp": update.timestamp.isoformat(),
            },
        )

        self.logger.debug(
            "Processing progress updated",
            processing_id=processing_id,
            progress=progress,
            step=step,
        )

    async def complete_processing(
        self, processing_id: str, result: Optional[Dict[str, Any]] = None
    ):
        """Notify processing completion"""
        if processing_id in self.active_processes:
            process_info = self.active_processes[processing_id]
            duration = (datetime.utcnow() - process_info["started_at"]).total_seconds()
            del self.active_processes[processing_id]
        else:
            duration = None

        await self.manager.send_to_topic(
            f"processing:{processing_id}",
            MessageType.PROCESSING_COMPLETE,
            {
                "processing_id": processing_id,
                "result": result or {},
                "duration": duration,
            },
        )

        self.logger.info(
            "Processing completed notification sent",
            processing_id=processing_id,
            duration=duration,
        )

    async def error_processing(
        self, processing_id: str, error: str, error_type: Optional[str] = None
    ):
        """Notify processing error"""
        if processing_id in self.active_processes:
            del self.active_processes[processing_id]

        await self.manager.send_to_topic(
            f"processing:{processing_id}",
            MessageType.PROCESSING_ERROR,
            {
                "processing_id": processing_id,
                "error": error,
                "error_type": error_type or "unknown",
            },
        )

        self.logger.error(
            "Processing error notification sent",
            processing_id=processing_id,
            error=error,
        )


class AgentNotifier:
    """Handles agent-related WebSocket notifications"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.logger = get_logger("agent_notifier")

    async def agent_thinking(
        self, session_id: str, agent_type: str, thinking_message: str
    ):
        """Notify that agent is thinking/processing"""
        await self.manager.send_to_topic(
            f"agent:{session_id}",
            MessageType.AGENT_THINKING,
            {
                "session_id": session_id,
                "agent_type": agent_type,
                "message": thinking_message,
            },
        )

    async def agent_response(
        self,
        session_id: str,
        agent_type: str,
        response: str,
        confidence: float,
        sources: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Send agent response"""
        await self.manager.send_to_topic(
            f"agent:{session_id}",
            MessageType.AGENT_RESPONSE,
            {
                "session_id": session_id,
                "agent_type": agent_type,
                "response": response,
                "confidence": confidence,
                "sources": sources,
                "metadata": metadata or {},
            },
        )

        self.logger.info(
            "Agent response sent",
            session_id=session_id,
            agent_type=agent_type,
            confidence=confidence,
        )

    async def agent_error(self, session_id: str, agent_type: str, error: str):
        """Send agent error notification"""
        await self.manager.send_to_topic(
            f"agent:{session_id}",
            MessageType.AGENT_ERROR,
            {"session_id": session_id, "agent_type": agent_type, "error": error},
        )

        self.logger.error(
            "Agent error sent",
            session_id=session_id,
            agent_type=agent_type,
            error=error,
        )


# Global notifier instances
processing_notifier = ProcessingNotifier(connection_manager)
agent_notifier = AgentNotifier(connection_manager)


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    connection_id = None
    logger = get_logger("websocket_endpoint")

    try:
        # Accept connection
        connection_id = await connection_manager.connect(websocket)

        # Handle incoming messages
        while True:
            try:
                # Wait for message
                data = await websocket.receive_text()
                message = json.loads(data)

                await handle_websocket_message(connection_id, message)

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", connection_id=connection_id)
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received", connection_id=connection_id)
                await connection_manager.send_message(
                    connection_id, MessageType.ERROR, {"error": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection_id,
                    error=str(e),
                )
                await connection_manager.send_message(
                    connection_id, MessageType.ERROR, {"error": "Internal server error"}
                )

    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))

    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)


async def handle_websocket_message(connection_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    logger = get_logger("websocket_handler")

    message_type = message.get("type")
    data = message.get("data", {})

    try:
        if message_type == "subscribe":
            # Subscribe to topic
            topic = data.get("topic")
            if topic:
                await connection_manager.subscribe_to_topic(connection_id, topic)
                await connection_manager.send_message(
                    connection_id,
                    MessageType.NOTIFICATION,
                    {"message": f"Subscribed to {topic}"},
                )

        elif message_type == "unsubscribe":
            # Unsubscribe from topic
            topic = data.get("topic")
            if topic:
                await connection_manager.unsubscribe_from_topic(connection_id, topic)
                await connection_manager.send_message(
                    connection_id,
                    MessageType.NOTIFICATION,
                    {"message": f"Unsubscribed from {topic}"},
                )

        elif message_type == "ping":
            # Respond to ping
            await connection_manager.send_message(
                connection_id,
                MessageType.HEARTBEAT,
                {"pong": True, "server_time": datetime.utcnow().isoformat()},
            )

        else:
            logger.warning(
                "Unknown message type",
                connection_id=connection_id,
                message_type=message_type,
            )

    except Exception as e:
        logger.error(
            "Error handling WebSocket message",
            connection_id=connection_id,
            error=str(e),
        )
        await connection_manager.send_message(
            connection_id, MessageType.ERROR, {"error": "Failed to process message"}
        )
