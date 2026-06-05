import json
import time
from pathlib import Path
from .base import ModelInfo

CACHE_PATH = Path.home() / ".nokton" / "cache" / "model_catalog.json"
CACHE_TTL = 300  # 5 minutes


class ModelCatalog:
    def __init__(self):
        self._models: dict[str, list[ModelInfo]] = {}
        self._loaded_at: float = 0

    def get_all(self) -> dict[str, list[ModelInfo]]:
        return self._models

    def get_provider_models(self, provider_id: str) -> list[ModelInfo]:
        return self._models.get(provider_id, [])

    def find_model(self, model_id: str) -> ModelInfo | None:
        for models in self._models.values():
            for m in models:
                if m.id == model_id:
                    return m
        return None

    def update(self, provider_id: str, models: list[ModelInfo]):
        self._models[provider_id] = models
        self._loaded_at = time.time()
        self._save_cache()

    def is_stale(self) -> bool:
        return (time.time() - self._loaded_at) > CACHE_TTL

    def load_cache(self) -> bool:
        try:
            if CACHE_PATH.exists():
                with open(CACHE_PATH) as f:
                    data = json.load(f)
                for provider_id, models_data in data.items():
                    self._models[provider_id] = [ModelInfo(**m) for m in models_data]
                self._loaded_at = time.time()
                return True
        except Exception:
            pass
        return False

    def _save_cache(self):
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                pid: [m.__dict__ for m in models]
                for pid, models in self._models.items()
            }
            with open(CACHE_PATH, "w") as f:
                json.dump(data, f)
        except Exception:
            pass
