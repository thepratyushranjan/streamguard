#Vector
from datetime import datetime
from typing import Dict, Any, List, Optional


def _extract_detection_data(detections: List[Dict]) -> Dict[str, Any]:
    """Extract common detection fields (DRY)"""
    return {
        "detections_data": detections,
        "detections_count": len(detections)
    }

def extract_enriched_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract enriched data matching Vector's remap transform logic.
    Mimics the vector.toml transform behavior.
    """
    meta = event.get("meta", {})
    event_type = event.get("type")
    
    # Base enriched data
    enriched = {
        "cam_id": meta.get("cam_id"),
        "site": meta.get("site"),
        "status": meta.get("status"),
        "event_type": event_type,
        "timestamp": meta.get("ts"),
    }
    
    # Get event-specific data
    source = event.get("data") or event.get("event") or {}
    detections = source.get("detections", [])
    
    # Add common fields
    enriched.update({
        "people_count": source.get("people_count"),
        **_extract_detection_data(detections)
    })
    
    # Add optional fields from source regardless of event type
    enriched.update({
        "triggers": source.get("triggers", []),
        "capture_triggered": source.get("capture_triggered", False)
    })
    
    return enriched


class CameraDataTransformer:
    """Transforms camera detection events into normalized schema."""

    CAM_ID_START = 100

    def __init__(self, cam_id_mapping: Optional[Dict[str, int]] = None):
        """
        Args:
            cam_id_mapping: Optional predefined mapping {cam_name: cam_id}
        """
        self.cam_id_mapping: Dict[str, int] = cam_id_mapping or {}
        self._next_id: int = (
            max(self.cam_id_mapping.values(), default=self.CAM_ID_START - 1) + 1
        )

    # ---------- Internal Helpers ----------

    def _get_or_create_cam_id(self, cam_name: str) -> int:
        """Return integer cam_id, create if not exists."""
        cam_id = self.cam_id_mapping.get(cam_name)
        if cam_id is None:
            cam_id = self._next_id
            self.cam_id_mapping[cam_name] = cam_id
            self._next_id += 1
        return cam_id

    @staticmethod
    def _to_unix_timestamp(timestamp_str: str) -> int:
        """Convert ISO-8601 timestamp to Unix seconds (UTC)."""
        return int(
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
        )

    @staticmethod
    def _transform_detection(det: Dict[str, Any]) -> Dict[str, Any]:
        """Transform single detection object."""
        bbox = det["bbox"]
        return {
            "class_id": det["class_id"],
            "label": det["label"],
            "confidence": det["confidence"],
            "bbox": [bbox["left"], bbox["top"], bbox["width"], bbox["height"]],
        }

    # ---------- Public API ----------

    def transform(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform input camera events.

        Args:
            input_data: Raw input payload

        Returns:
            List of normalized events
        """
        transformed_events: List[Dict[str, Any]] = []

        for event in input_data.get("results", []):
            cam_name = event["cam_id"]
            cam_id = self._get_or_create_cam_id(cam_name)
            processed_at = self._to_unix_timestamp(event["timestamp"])

            transformed_events.append(
                {
                    "type": event["event_type"],
                    "processed_at": processed_at,
                    "meta": {
                        "cam_id": cam_id,
                        "cam_name": cam_name,
                        "site": event["site"],
                        "status": event["status"],
                        "ts": processed_at,
                    },
                    "data": {
                        "people_count": event["people_count"],
                        "triggers": event.get("triggers", []),
                        "capture_triggered": event.get("capture_triggered", False),
                        "detections": [
                            self._transform_detection(det)
                            for det in event.get("detections_data", [])
                        ],
                    },
                }
            )

        return transformed_events



transformer = CameraDataTransformer()