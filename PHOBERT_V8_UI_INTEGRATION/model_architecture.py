import torch
from torch import nn
from transformers import AutoModel


class PhoBERT_ABSA_V6(nn.Module):
    def __init__(self, base_model="vinai/phobert-base-v2"):
        super().__init__()
        self.phobert = AutoModel.from_pretrained(base_model)
        self.dropout = nn.Dropout(0.1)
        self.detection_head = nn.Linear(768, 12 * 2)
        self.sentiment_head = nn.Linear(768, 12 * 3)

    def forward(self, input_ids, attention_mask):
        outputs = self.phobert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        cls = outputs.last_hidden_state[:, 0, :]
        cls = self.dropout(cls)

        detection = self.detection_head(cls).view(-1, 12, 2)
        sentiment = self.sentiment_head(cls).view(-1, 12, 3)

        return detection, sentiment
