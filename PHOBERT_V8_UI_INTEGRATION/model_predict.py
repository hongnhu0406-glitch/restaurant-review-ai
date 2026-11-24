import json
import math
from pathlib import Path

import torch
from transformers import AutoTokenizer
from model_architecture import PhoBERT_ABSA_V6


ROOT = Path(__file__).resolve().parent

with open(ROOT / "config.json", encoding="utf-8") as f:
    CONFIG = json.load(f)


class PhoBERTPredictor:
    def __init__(self, device=None):
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            str(ROOT / "tokenizer"),
            local_files_only=True
        )

        self.model = PhoBERT_ABSA_V6(
            CONFIG["base_model"]
        )

        state = torch.load(
            ROOT / "model" / "best_model.pt",
            map_location="cpu",
            weights_only=True
        )

        self.model.load_state_dict(state, strict=True)
        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def predict_review(self, review):
        if not isinstance(review, str):
            raise TypeError("Review phải là chuỗi văn bản.")

        review = review.strip()

        if not review:
            raise ValueError("Review không được để trống.")

        inputs = self.tokenizer(
            review,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=CONFIG["max_length"]
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        det_logits, sent_logits = self.model(
            inputs["input_ids"],
            inputs["attention_mask"]
        )

        det_probs = torch.softmax(det_logits[0], dim=-1)
        sent_probs = torch.softmax(sent_logits[0], dim=-1)

        results = []

        for i, aspect in enumerate(CONFIG["aspects"]):
            det_label = int(det_probs[i].argmax().item())

            if det_label == 0:
                label = 0
                confidence = float(det_probs[i, 0].item())
            else:
                sent_idx = int(sent_probs[i].argmax().item())
                label = sent_idx + 1
                confidence = float(
                    det_probs[i, 1].item()
                    * sent_probs[i, sent_idx].item()
                )

            if not math.isfinite(confidence):
                raise ValueError("Confidence không hợp lệ.")

            if not 0.0 <= confidence <= 1.0:
                raise ValueError("Confidence ngoài khoảng 0-1.")

            results.append({
                "Aspect": aspect.upper(),
                "Sentiment": label,
                "Confidence": round(confidence, 6)
            })

        if len(results) != 12:
            raise RuntimeError("Model không trả đủ 12 khía cạnh.")

        return results


_predictor = None


def get_predictor():
    global _predictor

    if _predictor is None:
        _predictor = PhoBERTPredictor()

    return _predictor


def predict_review(review):
    return get_predictor().predict_review(review)


def predict_reviews(reviews):
    if not isinstance(reviews, list):
        raise TypeError("reviews phải là list.")

    return [predict_review(review) for review in reviews]


def format_for_display(results, show_absent=False):
    rows = []

    for item in results:
        label = int(item["Sentiment"])

        if label == 0 and not show_absent:
            continue

        aspect = item["Aspect"].lower()
        confidence = float(item["Confidence"])

        rows.append({
            "STT": len(rows) + 1,
            "Aspect": item["Aspect"],
            "Tên khía cạnh": CONFIG["display_names"][aspect],
            "Mã cảm xúc": label,
            "Cảm xúc": CONFIG["sentiment_labels"][str(label)],
            "Độ tin cậy (%)": round(confidence * 100, 2)
        })

    return rows
