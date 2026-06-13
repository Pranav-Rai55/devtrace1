from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from groq import Groq
import json
import os

app = FastAPI(title="DevTrace AI Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Groq-supported model — fast and capable
GROQ_MODEL = "llama-3.3-70b-versatile"  # Or: "mixtral-8x7b-32768", "gemma2-9b-it"

SYSTEM_PROMPT = """You are DevTrace AI — a smart, concise assistant embedded inside the DevTrace developer tool. 
DevTrace helps developers trace, debug, and monitor their applications.

Your role:
- Help developers debug issues, trace errors, and understand logs
- Answer questions about code, architecture, and DevTrace features
- Be precise, technical, and developer-friendly
- Keep responses concise but complete
- Use markdown formatting for code snippets (use triple backticks with language)
- When analyzing errors or stack traces, be specific about root causes

You have deep knowledge of:
- Debugging strategies and error tracing
- Common runtime errors across Python, JS/TS, Go, Java, etc.
- DevTrace concepts: spans, traces, logs, metrics, and alerts
- Performance profiling and optimization
- API debugging and network tracing

Always be helpful, direct, and technically accurate."""


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    response: str
    usage: Optional[dict] = None


@app.get("/")
async def root():
    return {"status": "DevTrace AI API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")

    groq_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in request.messages
    ]

    # Prepend the system prompt as the first message
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + groq_messages

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=1024,
            messages=full_messages,
        )

        return ChatResponse(
            response=response.choices[0].message.content,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")

    groq_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in request.messages
    ]

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + groq_messages

    def generate():
        try:
            stream = client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=1024,
                messages=full_messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield f"data: {json.dumps({'text': delta.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)