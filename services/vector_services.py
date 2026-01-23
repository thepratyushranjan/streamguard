#Vector
from datetime import datetime
from typing import Dict, Any, List, Optional, Union


def _extract_detection_data(detections: List[Dict]) -> Dict[str, Any]:
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
    data = event.get("data", {})
    event_type = event.get("type")
    
    # Base enriched data
    enriched = {
        "company_id": meta.get("company_id", 0),
        "device_id": meta.get("device_id", 0),
        "cam_id": meta.get("cam_id"),
        "cam_name": meta.get("cam_name"),
        "site_name": meta.get("site_name") or meta.get("site", ""),
        "site_id": meta.get("site_id", ""),
        "zone_name": meta.get("zone_name"),  # Required field
        "latitude": meta.get("latitude", 0.0),
        "longitude": meta.get("longitude", 0.0),
        "country": meta.get("country", ""),
        "state": meta.get("state", ""),
        "district": meta.get("district", ""),
        "status": data.get("status") or meta.get("status", "safe"),
        "event_type": event_type,
        "timestamp": meta.get("ts"),
    }
    
    # Get event-specific data
    source = event.get("data") or event.get("event") or {}
    raw_detections = source.get("detections", [])
    
    detections = []
    recognitions_data = []
    
    for item in raw_detections:
        if "recognition" in item:
            rec = item.get("recognition", {})
            recognitions_data.append({
                "display_label": item.get("display_label", ""),
                "identity": rec.get("identity", ""),
                "confidence": rec.get("confidence", 0.0),
                "identity_id": rec.get("identity_id", 0)
            })
        
        detections.append(item)
    
    # Add common fields
    enriched.update({
        "video_count": source.get("video_count", 0),
        "image_count": source.get("image_count", 0),
        **_extract_detection_data(detections),
        "recognitions_data": recognitions_data
    })
    
    # Add optional fields from source regardless of event type
    enriched.update({
        "triggers": source.get("triggers", []),
        "capture_triggered": source.get("capture_triggered", False),
        "triaged_by": source.get("triaged_by", ""),
        "triage_notes": source.get("triage_notes", ""),
        "triage_timestamp": source.get("triage_timestamp", 0.0),
        "ai_insights": source.get("ai_insights", ""),
        "evidence_path": source.get("evidence_path", "")
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
    def _to_unix_timestamp(value: Union[str, int, float]) -> int:
        """Convert ISO-8601 timestamp or raw timestamp to Unix seconds (UTC)."""
        if isinstance(value, (int, float)):
            return int(value)
        return int(
            datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        )

    @staticmethod
    def _transform_detection(det: Dict[str, Any]) -> Dict[str, Any]:
        """Transform single detection object."""
        bbox = det["bbox"]
        
        # Handle both list [x, y, w, h] and dict {left, top, width, height} formats
        if isinstance(bbox, list):
            final_bbox = bbox
        else:
            final_bbox = [bbox["left"], bbox["top"], bbox["width"], bbox["height"]]
        
        # Extract recognition data if present
        recognition = det.get("recognition", {})
            
        return {
            "class_id": det["class_id"],
            "label": det["label"],
            "confidence": det["confidence"],
            "bbox": final_bbox,
            "object_id": det.get("object_id", ""),
            "display_label": det.get("display_label", ""),
            "recognition": recognition,
            # Optional detection metadata
            "model_id": det.get("model_id", 0),
            "track_id": det.get("track_id", 0),
            "parent_track_id": det.get("parent_track_id", 0),
            # Optional LPR data
            "lpr": det.get("lpr", {}),
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
            # Prefer explicit cam_name, fallback to stringified cam_id
            cam_name = event.get("cam_name") or str(event["cam_id"])
            cam_id = self._get_or_create_cam_id(cam_name)
            processed_at = self._to_unix_timestamp(event["timestamp"])

            transformed_events.append(
                {
                    "type": event["event_type"],
                    "processed_at": processed_at,
                    "meta": {
                        "company_id": event.get("company_id", 0),
                        "device_id": event.get("device_id", 0),
                        "cam_id": cam_id,
                        "cam_name": cam_name,
                        "site_name": event.get("site_name", ""),
                        "site_id": event.get("site_id", ""),
                        "zone_name": event.get("zone_name"),  # Required field
                        "latitude": event.get("latitude", 0.0),
                        "longitude": event.get("longitude", 0.0),
                        "country": event.get("country", ""),
                        "state": event.get("state", ""),
                        "district": event.get("district", ""),
                        "status": event.get("status", "safe"),
                        "ts": processed_at,
                    },
                    "data": {
                        "video_count": event.get("video_count", 0),
                        "image_count": event.get("image_count", 0),
                        "triggers": event.get("triggers", []),
                        "capture_triggered": event.get("capture_triggered", False),
                        "status": event.get("status", "safe"),
                        "triaged_by": event.get("triaged_by", ""),
                        "triage_notes": event.get("triage_notes", ""),
                        "triage_timestamp": event.get("triage_timestamp", 0.0),
                        "ai_insights": event.get("ai_insights", ""),
                        "evidence_path": event.get("evidence_path", ""),
                        "detections": [
                            self._transform_detection(det)
                            for det in event.get("detections_data", [])
                        ],
                        "recognitions": event.get("recognitions_data") or [],
                    },
                }
            )

        return transformed_events

transformer = CameraDataTransformer()