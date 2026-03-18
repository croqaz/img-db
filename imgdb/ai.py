"""
AI-related utilities for image analysis and processing.
"""

import os
from base64 import b64encode
from typing import Any, Optional

import clip
import httpx
import numpy
from PIL import Image

from .log import log
from .util import img_to_b64

# You can serve local models using apps like LLama.cpp or LM-Studio
AI_API = os.environ.get('AI_API', 'http://127.0.0.1:1234/v1/chat/completions')


def obj_detect_llm(img: Image.Image) -> str:  # pragma: no cover
    """
    Describes the image using a large language model (LLM).
    It could be a local LLM server or an external API with vision capabilities.
    Thinking models are super slow, it's recommended to use a smaller non-thinking model.
    Tested models:
    - Gemma3-12B
    - Next2-Fast-4B
    - olmOCR-2-7B
    - Qwen3-VL-8B
    - Qwen3.5-35B-A3B
    """
    prompt = """
Analyze the image and list all visible objects, people, animals, text, and notable elements.
For people and animals, briefly describe what they are doing and any visible emotional expression.
Keep descriptions factual and concise.
Don't add speculation or interpretation beyond what is visible.
Don't include greetings, explanations, or questions.
Output only the description.
""".strip()
    messages = [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + img_to_b64(img, 'jpeg', 80)}},
            ],
        }
    ]
    result = httpx.post(
        AI_API,
        headers={'Content-Type': 'application/json'},
        json={'temperature': 0.1, 'messages': messages},
    ).json()
    if 'choices' in result and len(result['choices']) > 0:
        r = result['choices'][0]['message']['content']
        r = '. '.join(t.strip(' .') for t in r.split('\n') if t)
        print('LLM object detection result:', r)
        return r
    return ''


# Cache the model per process
_clip_model = None
_clip_preprocess = None


def image_embedding_clip(image: Image.Image) -> list[float]:  # pragma: no cover
    """
    Generates a compact embedding for the image using OpenAI's CLIP model.
    CLIP models can generate both image and text embeddings in the same vector space.
    ViT-B/32 model is a good balance of speed and accuracy for similarity search.
    > pip install git+https://github.com/openai/CLIP.git
    """
    global _clip_model, _clip_preprocess
    import torch

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if _clip_model is None or _clip_preprocess is None:
        _clip_model, _clip_preprocess = clip.load('ViT-B/32', device=device)

    img = image.convert('RGB')
    input_tensor = _clip_preprocess(img).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = _clip_model.encode_image(input_tensor)
        # L2 normalization on the embedding vector for cosine similarity comparison
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]  # remove batch dimension


def text_embedding_clip(text: str) -> list[float]:  # pragma: no cover
    """
    Generates a compact embedding for the text using OpenAI's CLIP model.
    This is used for similarity search based on text queries.
    """
    global _clip_model
    import torch

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if _clip_model is None:
        _clip_model, _ = clip.load('ViT-B/32', device=device)

    text_tokens = clip.tokenize(text).to(device)
    with torch.no_grad():
        embedding = _clip_model.encode_text(text_tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]  # remove batch dimension


# Cache the model per process
_torch_model = None


def image_embedding_effnet(image: Image.Image) -> str:  # pragma: no cover
    """
    Generates a compact embedding for the image using a pretrained EfficientNet model.
    EfficientNet B0 model is fastest and least accurate, but perfect for similarity search.
    """
    global _torch_model
    import torch
    import torchvision.models as models

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Load pretrained EfficientNet-B0
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1
    _torch_model = models.efficientnet_b0(weights=weights).to(device)
    # Remove classification head to get feature embeddings
    _torch_model.classifier = torch.nn.Identity()
    _torch_model.eval()

    img = image.convert('RGB')
    preprocess = weights.transforms()
    input_tensor = preprocess(img).unsqueeze(0).to(device)  # add batch dimension
    with torch.no_grad():
        embedding = _torch_model(input_tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]  # remove batch dimension


AI_OPS: dict[str, Any] = {
    'obj-detect-llm': obj_detect_llm,
    'embedding-clip': image_embedding_clip,
    'embedding-effnet': image_embedding_effnet,
}


def to_float16_bytes(embedding: numpy.ndarray) -> bytes:  # pragma: no cover
    embedding_float16 = embedding.astype('float16')
    return embedding_float16.tobytes()


def to_float16_ascii(embedding: numpy.ndarray) -> str:  # pragma: no cover
    return b64encode(to_float16_bytes(embedding)).decode('ascii')


def to_int8_bytes(embedding: numpy.ndarray) -> bytes:  # pragma: no cover
    embedding_int8 = (embedding * 127).astype('int8')
    return embedding_int8.tobytes()


def to_int8_ascii(embedding: numpy.ndarray) -> str:  # pragma: no cover
    return b64encode(to_int8_bytes(embedding)).decode('ascii')


def run_ai(images: dict, algo: str, postprocess=to_float16_ascii) -> Optional[str]:  # pragma: no cover
    if algo in AI_OPS:
        try:
            value = AI_OPS[algo](images['256px'])
        except Exception as err:
            log.error(f'Error running {algo}: {err}')
            return None
        if postprocess:
            value = postprocess(value)
        return value
