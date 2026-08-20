import io

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import pipeline
from app.database import Base, engine, get_db
from app.models import Prompt
from app.schemas import PromptCreateResponse, PromptListItem, WeeksResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARE MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_csv(file: UploadFile) -> pd.DataFrame:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="只接受 .csv 檔案")
    try:
        df = pd.read_csv(io.BytesIO(file.file.read()))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV 無法解析：{exc}") from exc
    try:
        pipeline.validate_columns(df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return df


@app.post("/csv/weeks", response_model=WeeksResponse)
def get_weeks(file: UploadFile = File(...)):
    """上傳 CSV，純記憶體計算，回傳可產生 prompt 的週次清單。不寫入 DB。"""
    df = _read_csv(file)
    weeks = pipeline.list_valid_weeks(df)
    return {"filename": file.filename, "weeks": weeks}


@app.post("/prompts", response_model=PromptCreateResponse)
def create_prompt(
    week_index: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """重新解析同一份 CSV，跑完整 pipeline 產生指定週次的 prompt，存進 DB。"""
    df = _read_csv(file)
    try:
        evidence_package = pipeline.build_week_evidence_package(df, week_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt_text = pipeline.build_prompt(evidence_package)
    week_date = str(df.loc[week_index, "date"])

    record = Prompt(
        filename=file.filename,
        week_index=week_index,
        week_date=week_date,
        evidence_package=evidence_package,
        prompt_text=prompt_text,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/prompts", response_model=list[PromptListItem])
def list_prompts(db: Session = Depends(get_db)):
    return db.query(Prompt).order_by(Prompt.created_at.desc()).all()


@app.get("/prompts/{prompt_id}", response_model=PromptCreateResponse)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    record = db.get(Prompt, prompt_id)
    if record is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    return record
