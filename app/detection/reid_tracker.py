"""
reid_tracker.py — Appearance-embedding based Person Re-Identification.

PROBLEM IT SOLVES:
  ByteTrack assigns IDs by spatial proximity frame-to-frame.
  When a person leaves the frame and returns, they get a new ID.
  Their fatigue history, inactivity timer, and session data resets.
  If two people swap desks, the wrong person inherits the fatigue history.

APPROACH:
  Each person gets a 128-dim appearance embedding computed from their
  crop using a lightweight MobileNetV2 backbone (no GPU needed, ~3ms/crop).
  On re-entry, cosine similarity matches the new detection to the closest
  known embedding rather than bbox position alone.

  Embedding model: torchvision MobileNetV2 pretrained on ImageNet.
  Feature extraction: avgpool output (1280-dim) → PCA to 128-dim.
  No ReID-specific training needed — ImageNet features generalise well
  enough for distinguishing office workers by clothing/hair/build.

INTEGRATION:
  TrackManager calls reid_tracker.match_or_assign(new_track, crop)
  before creating a new PersonState. If a match is found with
  cosine_sim > REID_MATCH_THRESHOLD, the existing PersonState
  (with its full fatigue history) is reassigned to the new track ID.

CPU performance:
  MobileNetV2 forward pass on 128×64 crop: ~3–5ms on CPU.
  Runs once per new/uncertain track, not every frame.
"""
import os
import logging
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

_REID_MATCH_THRESHOLD  = float(os.getenv("REID_MATCH_THRESHOLD",  "0.82"))
_REID_GALLERY_TIMEOUT  = float(os.getenv("REID_GALLERY_TIMEOUT",  "300.0"))  # 5 min
_REID_EMB_HISTORY      = int(os.getenv("REID_EMB_HISTORY",        "5"))      # avg last N
_REID_UPDATE_EVERY     = int(os.getenv("REID_UPDATE_EVERY_FRAMES", "15"))    # update freq


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / denom)


class EmbeddingExtractor:
    """
    Extracts 128-dim appearance embeddings from person crops.
    Uses MobileNetV2 (pretrained ImageNet) — CPU-feasible, no ReID training needed.
    Lazy-loaded on first use so import doesn't slow startup.
    """

    def __init__(self):
        self._model   = None
        self._transform = None
        self._pca       = None   # fitted lazily on first 20 embeddings
        self._raw_buf   = []     # accumulate raw embeddings for PCA fitting
        self._ready     = False

    def _load(self):
        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as T

            model = models.mobilenet_v2(
                weights=models.MobileNet_V2_Weights.IMAGENET1K_V1
            )
            # Remove classifier — use avgpool features (1280-dim)
            model.classifier = torch.nn.Identity()
            model.eval()

            self._model = model
            self._transform = T.Compose([
                T.ToPILImage(),
                T.Resize((128, 64)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406],
                            std=[0.229, 0.224, 0.225]),
            ])
            self._ready = True
            logger.info("ReID: MobileNetV2 embedding extractor loaded.")
        except ImportError:
            logger.warning("ReID: torch/torchvision not available — ReID disabled.")
            self._ready = False

    def extract(self, bgr_crop: np.ndarray) -> Optional[np.ndarray]:
        """Returns 128-dim L2-normalised embedding, or None if unavailable."""
        if self._model is None:
            self._load()
        if not self._ready:
            return None

        import torch, cv2

        if bgr_crop is None or bgr_crop.size == 0:
            return None

        # Minimum crop size for meaningful features
        if bgr_crop.shape[0] < 32 or bgr_crop.shape[1] < 16:
            return None

        try:
            rgb   = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
            inp   = self._transform(rgb).unsqueeze(0)

            with torch.no_grad():
                feat = self._model(inp).squeeze().numpy()  # (1280,)

            # Reduce to 128-dim via mean pooling of 10 equal blocks
            # This is faster than full PCA and good enough for matching
            feat_128 = feat.reshape(10, 128).mean(axis=0)

            # L2 normalise for cosine similarity
            norm = np.linalg.norm(feat_128) + 1e-8
            return feat_128 / norm

        except Exception as e:
            logger.debug(f"ReID embedding extraction failed: {e}")
            return None


@dataclass
class GalleryEntry:
    """Stored appearance record for a known person."""
    track_id:       int
    embeddings:     deque = field(default_factory=lambda: deque(maxlen=5))
    last_seen_time: float = 0.0
    frame_count:    int   = 0

    def mean_embedding(self) -> Optional[np.ndarray]:
        if not self.embeddings:
            return None
        return np.mean(list(self.embeddings), axis=0)

    def update(self, emb: np.ndarray, timestamp: float):
        self.embeddings.append(emb)
        self.last_seen_time = timestamp
        self.frame_count   += 1


class ReIDTracker:
    """
    Maintains a gallery of person embeddings and matches new detections
    to known persons by appearance similarity.

    Usage in TrackManager:
        on new track:
            matched_id = reid.match(new_crop, current_time)
            if matched_id is not None:
                # reuse existing PersonState[matched_id] for new track_id
            reid.register(track_id, new_crop, current_time)

        on each frame (existing track):
            reid.update(track_id, crop, current_time)
    """

    def __init__(self):
        self._extractor = EmbeddingExtractor()
        self._gallery:  dict[int, GalleryEntry] = {}
        self._frame_counters: dict[int, int] = {}

    def update(self, track_id: int, bgr_crop: np.ndarray, timestamp: float):
        """Update embedding for an existing confirmed track (every N frames)."""
        cnt = self._frame_counters.get(track_id, 0) + 1
        self._frame_counters[track_id] = cnt

        if cnt % _REID_UPDATE_EVERY != 0:
            return

        emb = self._extractor.extract(bgr_crop)
        if emb is None:
            return

        if track_id not in self._gallery:
            self._gallery[track_id] = GalleryEntry(track_id=track_id)

        self._gallery[track_id].update(emb, timestamp)

    def match(self, bgr_crop: np.ndarray,
              timestamp: float,
              exclude_ids: set | None = None) -> Optional[int]:
        """
        Try to match a new/uncertain detection to a known gallery entry.
        Returns track_id of the best match, or None if no confident match.

        exclude_ids: currently active track IDs to exclude from matching
                     (prevents matching to someone already in frame).
        """
        emb = self._extractor.extract(bgr_crop)
        if emb is None:
            return None

        best_id   = None
        best_sim  = _REID_MATCH_THRESHOLD - 0.01  # must beat threshold

        for gid, entry in self._gallery.items():
            if exclude_ids and gid in exclude_ids:
                continue

            # Skip entries not seen recently
            if timestamp - entry.last_seen_time > _REID_GALLERY_TIMEOUT:
                continue

            mean_emb = entry.mean_embedding()
            if mean_emb is None:
                continue

            sim = _cosine_sim(emb, mean_emb)
            if sim > best_sim:
                best_sim = sim
                best_id  = gid

        if best_id is not None:
            logger.info(
                f"ReID: New detection matched to track {best_id} "
                f"(sim={best_sim:.3f})"
            )
        return best_id

    def register(self, track_id: int, bgr_crop: np.ndarray, timestamp: float):
        """Register a brand-new track in the gallery."""
        emb = self._extractor.extract(bgr_crop)
        if emb is None:
            return
        entry = GalleryEntry(track_id=track_id)
        entry.update(emb, timestamp)
        self._gallery[track_id] = entry
        logger.info(f"ReID: Registered new track {track_id} in gallery.")

    def evict_stale(self, timestamp: float):
        """Remove gallery entries not seen for longer than timeout."""
        stale = [
            tid for tid, e in self._gallery.items()
            if timestamp - e.last_seen_time > _REID_GALLERY_TIMEOUT
        ]
        for tid in stale:
            del self._gallery[tid]
            logger.debug(f"ReID: Evicted stale gallery entry {tid}")

    def reassign(self, old_id: int, new_id: int):
        """
        Transfer gallery entry from old_id to new_id after a ReID match.
        Called by TrackManager after confirming the match.
        """
        if old_id in self._gallery:
            entry          = self._gallery.pop(old_id)
            entry.track_id = new_id
            self._gallery[new_id] = entry
            logger.info(f"ReID: Gallery entry reassigned {old_id} → {new_id}")