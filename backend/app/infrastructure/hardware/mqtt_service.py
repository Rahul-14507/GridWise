"""MQTT telemetry subscriber service for GridWise.

Listens to MQTT messages on configured broker (default: broker.hivemq.com:1883),
parses incoming ESP32 JSON payloads, adapts them into HardwareTelemetry domain models,
and records them into the HardwareTelemetryService for real-time state synthesis.
"""

import json
import logging
from typing import Optional
import paho.mqtt.client as mqtt

from app.config.settings import Settings, get_settings
from app.domain.models.hardware import HardwareTelemetry
from app.infrastructure.hardware.telemetry_service import (
    HardwareTelemetryService,
    get_hardware_telemetry_service,
)

logger = logging.getLogger(__name__)


class MQTTTelemetrySubscriber:
    """Background MQTT client subscribing to ESP32 hardware telemetry topics."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        telemetry_service: Optional[HardwareTelemetryService] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._telemetry_service = (
            telemetry_service or get_hardware_telemetry_service()
        )
        self._client: Optional[mqtt.Client] = None
        self._is_running: bool = False

    def _on_connect(self, client: mqtt.Client, userdata: any, flags: dict, rc: int, *args: any) -> None:
        """Callback triggered when client connects to MQTT broker."""
        if rc == 0:
            logger.info(
                f"[MQTT] Connected successfully to broker '{self._settings.mqtt_broker_host}:{self._settings.mqtt_broker_port}'"
            )
            topic = self._settings.mqtt_topic
            client.subscribe(topic)
            logger.info(f"[MQTT] Subscribed to telemetry topic: '{topic}'")
        else:
            logger.warning(
                f"[MQTT] Connection to broker '{self._settings.mqtt_broker_host}' failed with return code {rc}"
            )

    def _on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage) -> None:
        """Callback triggered when a telemetry payload arrives on subscribed topic."""
        try:
            raw_payload = msg.payload.decode("utf-8")
            logger.debug(f"[MQTT] Message received on '{msg.topic}': {raw_payload}")
            json_data = json.loads(raw_payload)

            telemetry = HardwareTelemetry.model_validate(json_data)
            receipt = self._telemetry_service.record_telemetry(telemetry)

            logger.info(
                f"[MQTT] Ingested telemetry from '{telemetry.device_id}' "
                f"(Temp={telemetry.temperature_c}°C, Solar={telemetry.solar_voltage_v}V [{telemetry.solar_status or 'N/A'}], "
                f"Rain={telemetry.rain_status or 'DRY'}): {receipt.message}"
            )
        except Exception as err:
            logger.error(
                f"[MQTT] Failed to process telemetry message on '{msg.topic}': {err}",
                exc_info=True,
            )

    def start(self) -> None:
        """Start the background MQTT client network loop."""
        if not self._settings.mqtt_enabled:
            logger.info("[MQTT] MQTT subscriber is disabled in settings.")
            return

        if self._is_running:
            logger.warning("[MQTT] Subscriber is already running.")
            return

        try:
            # paho-mqtt v2.0+ compatibility (CallbackAPIVersion.VERSION1 or fallback)
            client_kwargs = {}
            if hasattr(mqtt, "CallbackAPIVersion"):
                try:
                    client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION1
                except Exception:
                    pass

            self._client = mqtt.Client(
                client_id=self._settings.mqtt_client_id,
                clean_session=True,
                **client_kwargs,
            )
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message

            logger.info(
                f"[MQTT] Connecting to broker '{self._settings.mqtt_broker_host}:{self._settings.mqtt_broker_port}'..."
            )
            self._client.connect_async(
                host=self._settings.mqtt_broker_host,
                port=self._settings.mqtt_broker_port,
                keepalive=self._settings.mqtt_keepalive,
            )
            self._client.loop_start()
            self._is_running = True
            logger.info("[MQTT] Background subscriber network loop started.")
        except Exception as err:
            logger.error(f"[MQTT] Failed to start MQTT subscriber: {err}", exc_info=True)

    def stop(self) -> None:
        """Stop the background MQTT client network loop."""
        if not self._is_running or self._client is None:
            return

        try:
            logger.info("[MQTT] Stopping MQTT subscriber background loop...")
            self._client.loop_stop()
            self._client.disconnect()
            self._is_running = False
            logger.info("[MQTT] MQTT subscriber stopped cleanly.")
        except Exception as err:
            logger.error(f"[MQTT] Error while stopping MQTT subscriber: {err}", exc_info=True)


_mqtt_subscriber_instance: Optional[MQTTTelemetrySubscriber] = None


def get_mqtt_subscriber() -> MQTTTelemetrySubscriber:
    """Retrieve global MQTT subscriber singleton."""
    global _mqtt_subscriber_instance
    if _mqtt_subscriber_instance is None:
        _mqtt_subscriber_instance = MQTTTelemetrySubscriber()
    return _mqtt_subscriber_instance
