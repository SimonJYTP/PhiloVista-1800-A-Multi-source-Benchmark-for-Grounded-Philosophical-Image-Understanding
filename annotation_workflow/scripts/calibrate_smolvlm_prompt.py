from __future__ import annotations

import json
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor


WORKFLOW = Path(__file__).resolve().parents[1]
MODEL = WORKFLOW / "runtime" / "models" / "SmolVLM-500M-Instruct"
IMAGE = WORKFLOW / "blind_pool" / "pilot" / "F0019.png"

PROMPTS = [
    """Look carefully at the image. Return ONLY one compact valid JSON object, no prose and no markdown. Use English. Required keys and exact array sizes: {"subject":"...","scene":["...","...","..."],"action":["...","...","..."],"reason":["...","...","..."],"objects":["...","...","...","...","..."]}. Describe only visible evidence. If a reason is uncertain, say so.""",
    """Inspect the image and answer in English. Write exactly five numbered factual observations. Mention the setting, visible people, actions, important objects, weather or lighting, and readable text. Do not guess identities or unseen events.""",
    """Inspect the image. Return ONLY JSON: {"anchors":["three concrete visible details"],"interpretations":[{"concept":"one of ethics, mortality, society, identity, knowledge, power, choice, labor, freedom, faith","claim":"grounded philosophical reading","limit":"what the image cannot prove"},{"concept":"...","claim":"...","limit":"..."},{"concept":"...","claim":"...","limit":"..."}]}. Use English and no markdown.""",
]


def main() -> None:
    dtype = torch.bfloat16
    processor = AutoProcessor.from_pretrained(MODEL)
    model = AutoModelForImageTextToText.from_pretrained(MODEL, dtype=dtype, attn_implementation="sdpa").to("cuda").eval()
    with Image.open(IMAGE) as source:
        image = source.convert("RGB")
    for index, instruction in enumerate(PROMPTS, 1):
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": instruction}]}]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[image], return_tensors="pt")
        inputs = {key: value.to("cuda", dtype=dtype) if value.is_floating_point() else value.to("cuda") for key, value in inputs.items()}
        input_length = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            result = model.generate(**inputs, do_sample=False, max_new_tokens=500)
        output = processor.decode(result[0][input_length:], skip_special_tokens=True)
        print(json.dumps({"prompt": index, "output": output}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
