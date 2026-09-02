import json
import logging
import threading

import paho.mqtt.client as mqtt

from ..config import settings

logger = logging.getLogger("mqtt")


class MQTTService:
    """Fire-and-forget MQTT publisher (paho background thread).

    Never blocks the API request path: failures are logged and skipped.
    """

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        if self._client is None:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=30)
            client.loop_start()
            self._client = client
        return self._client

    def publish(self, topic: str, payload: dict):
        try:
            with self._lock:
                client = self._get_client()
            client.publish(topic, json.dumps(payload, default=str), qos=0)
        except Exception as exc:
            logger.warning("MQTT publish to %s failed: %s", topic, exc)


mqtt_service = MQTTService()