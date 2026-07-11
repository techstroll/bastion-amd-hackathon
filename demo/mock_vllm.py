"""Mock vLLM server for local end-to-end testing WITHOUT the GPU.

Speaks just enough of the OpenAI dialect for the router. Answers are canned
per model/adapter so the multi-LoRA story is visible even in the mock.

Run: uvicorn demo.mock_vllm:app --port 8000
"""

from fastapi import FastAPI, Request

app = FastAPI(title="mock-vllm")

VOICES = {
    "legal-lora": "LEGAL ANALYSIS — [mock] Reviewed under attorney-client privilege framework. "
                  "RECOMMENDATION: route to counsel. This does not constitute legal advice.",
    "finance-lora": "FINANCE MEMO — [mock] 📊 NPV positive at 9% WACC. 💡 Bottom line: proceed. "
                    "Next step: full model in the board pack.",
    "hr-lora": "HR GUIDANCE — [mock] 👥 Handled per the Employee Handbook. Partner with HR "
               "on specifics. This is general guidance, not legal advice.",
}
DEFAULT = "[mock base-8B] Here is a helpful general answer."

# adapters loaded at runtime via /v1/load_lora_adapter (mocks the hot-load)
_LOADED = ["Qwen/Qwen2.5-7B-Instruct", "legal-lora", "finance-lora"]


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [
        {"id": m, "object": "model"} for m in _LOADED
    ]}


@app.post("/v1/load_lora_adapter")
async def load_lora_adapter(request: Request):
    body = await request.json()
    name = body.get("lora_name", "")
    if name and name not in _LOADED:
        _LOADED.append(name)
    return {"status": "success", "loaded": name}


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    model = body.get("model", "")
    prompt_len = sum(len(m.get("content", "").split()) for m in body.get("messages", []))
    content = VOICES.get(model, DEFAULT)
    return {
        "id": "mock", "object": "chat.completion", "model": model,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": prompt_len, "completion_tokens": len(content.split()),
                  "total_tokens": prompt_len + len(content.split())},
    }
