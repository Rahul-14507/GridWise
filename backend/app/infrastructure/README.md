# Infrastructure Layer

This package is reserved for external adapters, hardware integrations, persistence, and external communication protocols.

## Intended Responsibilities (Future Milestones)

- **Database Adapters**: PostgreSQL/TimescaleDB or SQLite repository implementations.
- **Hardware Telemetry Ingestion**: MQTT brokers or direct ESP32 HTTP ingestion adapters.
- **Computer Vision Connector**: OpenCV camera feed integrations for physical slot occupancy detection.
- **External WebSockets**: Real-time push clients for live dashboard telemetry updates.

## Design Boundary Rules

- The domain layer (`app/domain/`) MUST NEVER import from or depend on this infrastructure layer.
- Infrastructure components implement abstract interfaces defined by domain contracts.
