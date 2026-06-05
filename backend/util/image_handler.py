import base64
import io
import os
from ..providers.base import ModelCapabilities


class ImageNormalizer:
    MAX_DIMENSION = 2000
    MAX_SIZE_BYTES = 5 * 1024 * 1024

    def normalize(self, image_data: bytes) -> dict:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))

            if img.mode != "RGB":
                img = img.convert("RGB")

            if max(img.size) > self.MAX_DIMENSION:
                ratio = self.MAX_DIMENSION / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            buf = io.BytesIO()
            quality = 85
            img.save(buf, format="JPEG", quality=quality)
            while buf.tell() > self.MAX_SIZE_BYTES and quality > 10:
                quality -= 10
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality)

            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return {
                "base64": b64,
                "mime_type": "image/jpeg",
                "width": img.width,
                "height": img.height,
                "size_bytes": buf.tell(),
            }
        except Exception as e:
            return {"error": str(e)}


class VisionFallback:
    def __init__(self, provider, model_id: str):
        self._provider = provider
        self._model_id = model_id

    def describe_image(self, image_base64: str) -> str:
        from ..providers.base import Message, ContentText, ContentImage
        messages = [
            Message(role="user", content=[
                ContentText("Describe this image in detail, focusing on what's visible."),
                ContentImage(base64=image_base64),
            ])
        ]
        result = []
        for event in self._provider.stream_chat(
            model=self._model_id,
            messages=messages,
            max_tokens=1024,
        ):
            from ..providers.base import StreamEventType
            if event.type == StreamEventType.TEXT_DELTA:
                result.append(event.text)
        return "".join(result)

    def handle_image_in_input(self, image_base64: str) -> str:
        description = self.describe_image(image_base64)
        return f"[User attached an image. Description: {description}]"


def should_use_vision_fallback(capabilities: ModelCapabilities) -> bool:
    return not capabilities.vision


def process_images_for_model(
    images: list[str],
    model_capabilities: ModelCapabilities,
    vision_provider,
    vision_model_id: str,
) -> list[dict]:
    normalizer = ImageNormalizer()
    processed = []

    for b64 in images:
        if model_capabilities.vision:
            processed.append({
                "type": "image",
                "base64": b64,
            })
        else:
            fallback = VisionFallback(vision_provider, vision_model_id)
            description = fallback.describe_image(b64)
            processed.append({
                "type": "description",
                "text": description,
            })

    return processed
