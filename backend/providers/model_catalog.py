import json
import time
from dataclasses import asdict, fields
from pathlib import Path
from .base import ModelInfo, ModelCapabilities, ModelPricing

CACHE_PATH = Path.home() / ".nokton" / "cache" / "model_catalog.json"
CACHE_TTL = 300  # 5 minutes


def _model_from_dict(d: dict) -> ModelInfo:
    info_kwargs = {f.name for f in fields(ModelInfo)}
    filtered = {k: v for k, v in d.items() if k in info_kwargs}
    if "capabilities" in d and isinstance(d["capabilities"], dict):
        cap_fields = {f.name for f in fields(ModelCapabilities)}
        cap = {k: v for k, v in d["capabilities"].items() if k in cap_fields}
        filtered["capabilities"] = ModelCapabilities(**cap)
    if "pricing" in d and isinstance(d["pricing"], dict):
        price_fields = {f.name for f in fields(ModelPricing)}
        price = {k: v for k, v in d["pricing"].items() if k in price_fields}
        filtered["pricing"] = ModelPricing(**price)
    return ModelInfo(**filtered)


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
                    self._models[provider_id] = [
                        _model_from_dict(m) for m in models_data
                    ]
                self._loaded_at = time.time()
                return True
        except Exception:
            pass
        return False

    def _save_cache(self):
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                pid: [asdict(m) for m in models]
                for pid, models in self._models.items()
            }
            with open(CACHE_PATH, "w") as f:
                json.dump(data, f, default=str)
        except Exception:
            pass
