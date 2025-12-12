from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from models.intent_classifier import IntentClassifier
from nlp.entity_extractor import EntityExtractor

MODEL_PATH = Path("models/intent_classifier.joblib")

classifier = IntentClassifier(MODEL_PATH)
entity_extractor = EntityExtractor()

app = FastAPI(title="ISP Chatbot Intent API")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    confidence: float
    entity: str | None


@app.post("/predict", response_model=ChatResponse)
def predict_intent(payload: ChatRequest) -> ChatResponse:
    result = classifier.predict(payload.message)
    entity = entity_extractor.extract(payload.message)
    return ChatResponse(
        intent=result["intent"],
        confidence=result["confidence"],
        entity=entity,
    )
