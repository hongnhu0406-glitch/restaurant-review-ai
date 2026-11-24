
import os
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "vinai/phobert-base-v2"
NUM_ASPECTS = 12
MAX_LENGTH = 256

ASPECTS = [
    "AMBIENCE#GENERAL",
    "DRINKS#PRICES",
    "DRINKS#QUALITY",
    "DRINKS#STYLE&OPTIONS",
    "FOOD#PRICES",
    "FOOD#QUALITY",
    "FOOD#STYLE&OPTIONS",
    "LOCATION#GENERAL",
    "RESTAURANT#GENERAL",
    "RESTAURANT#MISCELLANEOUS",
    "RESTAURANT#PRICES",
    "SERVICE#GENERAL"
]

LABEL_MAP = {
    0: "Absent",
    1: "Positive",
    2: "Negative",
    3: "Neutral"
}


class PhoBERT_ABSA_V8(nn.Module):

    def __init__(self):
        super().__init__()

        self.phobert = AutoModel.from_pretrained(MODEL_NAME)
        self.dropout = nn.Dropout(0.1)

        self.detection_head = nn.Linear(
            768, NUM_ASPECTS * 2
        )

        self.sentiment_head = nn.Linear(
            768, NUM_ASPECTS * 3
        )

    def forward(self, input_ids, attention_mask):

        outputs = self.phobert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        cls_output = outputs.last_hidden_state[:, 0, :]
        x = self.dropout(cls_output)

        detection = self.detection_head(x).reshape(
            -1, NUM_ASPECTS, 2
        )

        sentiment = self.sentiment_head(x).reshape(
            -1, NUM_ASPECTS, 3
        )

        return detection, sentiment


class ABSAInference:

    def __init__(self, model_dir, device=None):

        self.model_dir = model_dir

        self.device = torch.device(
            device or (
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        )

        tokenizer_dir = os.path.join(
            model_dir, "tokenizer"
        )

        checkpoint_path = os.path.join(
            model_dir, "best_model_v8_from_v7.pt"
        )

        assert os.path.isdir(tokenizer_dir), (
            "Không tìm thấy thư mục tokenizer!"
        )

        assert os.path.isfile(checkpoint_path), (
            "Không tìm thấy checkpoint V8!"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_dir
        )

        self.model = PhoBERT_ABSA_V8()

        state_dict = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True
        )

        self.model.load_state_dict(
            state_dict,
            strict=True
        )

        self.model.to(self.device)
        self.model.eval()

    def predict(self, text):

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Review không được để trống.")

        # Giữ cách tokenization giống quá trình huấn luyện V8
        encoded = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        input_ids = encoded["input_ids"].to(self.device)
        attention_mask = encoded["attention_mask"].to(self.device)

        with torch.inference_mode():

            logits_det, logits_sent = self.model(
                input_ids,
                attention_mask
            )

            prob_det = torch.softmax(logits_det, dim=-1)
            prob_sent = torch.softmax(logits_sent, dim=-1)

            pred_det = logits_det.argmax(dim=-1)
            pred_sent = logits_sent.argmax(dim=-1) + 1

            predictions = torch.where(
                pred_det == 0,
                0,
                pred_sent
            )

        results = []

        for i, aspect in enumerate(ASPECTS):

            label_id = int(predictions[0, i].item())

            if label_id == 0:
                confidence = float(prob_det[0, i, 0].item())
            else:
                confidence = float(
                    prob_det[0, i, 1].item()
                    * prob_sent[0, i, label_id - 1].item()
                )

            results.append({
                "aspect": aspect,
                "label_id": label_id,
                "sentiment": LABEL_MAP[label_id],
                "confidence": round(confidence, 4)
            })

        return results
