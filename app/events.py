import json
import asyncio
from datetime import datetime
import aio_pika
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

async def publish_event(exchange_name: str, routing_key: str, data: dict):
    """Publish an event to RabbitMQ. Fire and forget — does not raise on failure."""
    try:
        logger.info("attempting_event_publish", event=routing_key)
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=5)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
            message = aio_pika.Message(
                body=json.dumps({
                    "event_type": routing_key,
                    "version": "1.0",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data
                }).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await exchange.publish(message, routing_key=routing_key)
            logger.info("event_published", routing_key=routing_key)
    except Exception as e:
        # Log but don't fail the request — events are best-effort
        logger.warning("event_publish_failed", error=str(e), routing_key=routing_key)

async def publish_user_registered(user_id: str, email: str, username: str):
    await publish_event("roadmap.events", "user.registered", {
        "user_id": user_id, "email": email, "username": username})
