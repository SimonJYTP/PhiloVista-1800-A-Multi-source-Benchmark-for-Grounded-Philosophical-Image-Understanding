from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

import requests


WORKFLOW = Path(__file__).resolve().parents[1]
ENV_FILE = WORKFLOW / ".env.local"
IMAGE = WORKFLOW / "blind_pool" / "pilot" / "F0019.png"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("DASHSCOPE_API_KEY", "ZHIPUAI_API_KEY"):
        if len(values.get(key, "")) < 10:
            raise RuntimeError(f"{key} is missing or invalid")
    return values


def image_data_url(path: Path) -> str:
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def call(url: str, api_key: str, model: str, image_url: str, provider: str) -> dict[str, object]:
    body: dict[str, object] = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": "Connectivity test. Look at the image and return only the dominant color of the large dome in the distance, in one lowercase English word."},
            ],
        }],
        "temperature": 0,
        "max_tokens": 16,
        "stream": False,
    }
    if provider == "qwen":
        body["enable_thinking"] = False
    elif provider == "glm":
        body["thinking"] = {"type": "disabled"}
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=(20, 120),
    )
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:500]}
    if response.status_code != 200:
        message = payload.get("error", payload) if isinstance(payload, dict) else payload
        raise RuntimeError(f"HTTP {response.status_code}: {message}")
    content = payload["choices"][0]["message"]["content"]
    return {
        "provider": provider,
        "model": payload.get("model", model),
        "http_status": response.status_code,
        "vision_answer": str(content).strip(),
        "request_id_present": bool(payload.get("id") or response.headers.get("x-request-id")),
    }


def main() -> None:
    keys = load_env()
    data_url = image_data_url(IMAGE)
    results = [
        call(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            keys["DASHSCOPE_API_KEY"],
            "qwen3-vl-plus",
            data_url,
            "qwen",
        ),
        call(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            keys["ZHIPUAI_API_KEY"],
            "glm-4.6v",
            data_url,
            "glm",
        ),
    ]
    print(json.dumps({"image": IMAGE.name, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
