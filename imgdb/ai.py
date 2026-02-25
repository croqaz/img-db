"""
AI-related utilities for image analysis and processing.
"""

import os
from base64 import b64encode

import httpx
from PIL import Image

from .util import img_to_b64

AI_API = os.environ.get('AI_API', 'http://127.0.0.1:1234/v1/chat/completions')


def obj_detect_llm(img: Image.Image) -> str:  # pragma: no cover
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


def image_embedding(image: Image.Image) -> str:  # pragma: no cover
    """
    Generate a compact embedding for the image using a pretrained EfficientNet model.
    EfficientNet B0 is fastest but least accurate.
    """
    import numpy
    import torch
    import torchvision.models as models

    img = image.convert('RGB')
    # Load pretrained EfficientNet-B0
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1
    model = models.efficientnet_b0(weights=weights)
    # Remove classification head to get feature embeddings
    model.classifier = torch.nn.Identity()
    model.eval()

    preprocess = weights.transforms()
    input_tensor = preprocess(img).unsqueeze(0)  # add batch dimension

    with torch.no_grad():
        embedding = model(input_tensor)

    embedding = embedding / numpy.linalg.norm(embedding)
    embedding_int8 = (embedding * 127).numpy().astype('int8')
    return b64encode(embedding_int8.tobytes()).decode('ascii')


AI_OPS = {
    'obj-detect-llm': obj_detect_llm,
    'image-embedding': image_embedding,
}


def run_ai(images: dict, algo: str):
    if algo in AI_OPS:
        return AI_OPS[algo](images['256px'])
