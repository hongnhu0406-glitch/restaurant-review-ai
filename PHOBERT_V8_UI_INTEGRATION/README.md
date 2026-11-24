# PhoBERT-ABSA V8 - UI Integration

## Model
- Base: vinai/phobert-base-v2
- Architecture: Detection Head + Sentiment Head
- Best checkpoint: Epoch 24
- Validation Macro-F1: 0.589550
- Max sequence length: 256 tokens
- 12 aspects, 4 output labels

## Run
Install dependencies:
    pip install -r requirements.txt

Example:
    python examples/test_predict.py

Run the example from the package root.

## Python API
    from model_predict import predict_review
    results = predict_review("Đồ ăn ngon nhưng phục vụ chậm.")

Returns exactly 12 items:
    [
      {
        "Aspect": "FOOD#QUALITY",
        "Sentiment": 1,
        "Confidence": 0.95
      },
      ...
    ]

The above values are illustrative, not actual predictions.

## Sentiment IDs
0 = Absent
1 = Positive
2 = Negative
3 = Neutral

## Confidence
Absent:
    P(detection = absent)

Present:
    P(detection = present)
    * P(predicted sentiment | present)

Confidence is a model-derived score, NOT a calibrated
guarantee of correctness.

## Backend responsibilities
- Create a unique batch_id per analysis request.
- Assign or validate review_id within each batch.
- Keep all 12 aspect results per review.
- Add batch_id, review_id, Review to saved result rows.
- Validate 12 unique aspects and valid labels/confidence.
- Mark batch Completed only after all rows succeed.
- Use only Completed batches in the dashboard.
- Handle CSV parsing, errors, upload size and history.
- Do not create batch IDs inside model_predict.py.

## Display
    from model_predict import format_for_display
    rows = format_for_display(results, show_absent=False)

Columns include:
- STT
- Aspect
- Tên khía cạnh
- Mã cảm xúc
- Cảm xúc
- Độ tin cậy (%)

## Important
The tokenizer uses truncation at 256 tokens to match
training. The backend should define and enforce its
long-review policy before calling this module.

The base encoder may be downloaded on first load.
For fully offline deployment, bundle a local copy of
the PhoBERT base encoder and adjust base_model.
