from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
import whisper
import shutil, os, time
import torch

app = FastAPI()

# ✅ 自動檢測並使用最佳設備
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cuda":
    print("✅ CUDA available. Using:", torch.cuda.get_device_name(0))
    model = whisper.load_model("medium").to("cuda")
else:
    print("⚠️ CUDA not available. Using CPU (slower but functional)")
    model = whisper.load_model("base")  # 使用較小的模型在 CPU 上運行


@app.post("/transcribe")
async def transcribe(file: UploadFile):
    filename = f"/tmp/{file.filename}"
    with open(filename, "wb") as f:
        shutil.copyfileobj(file.file, f)

    print(f"📥 Received file: {file.filename}")
    start = time.time()

    result = model.transcribe(filename)
    os.remove(filename)
    end = time.time()

    return {
        "text": result["text"].strip(),
        "device": str(next(model.parameters()).device),
        "duration_seconds": round(end - start, 2)
    }




