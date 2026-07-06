import json
import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from config import NER_MAX_LENGTH, NER_MODEL_NAME

LABEL_MAP = {
    0: "O",
    1: "B-ORG",
    2: "I-ORG",
    3: "B-PER",
    4: "I-PER",
    5: "B-LOC",
    6: "I-LOC",
    7: "B-LAW",
    8: "I-LAW",
    9: "B-DATE",
    10: "I-DATE",
    11: "B-NUM",
    12: "I-NUM",
}


@dataclass
class NEREntity:
    text: str
    label: str
    start_char: int
    end_char: int
    tokens: list[str]
    bio_tags: list[str]


class ViLegalBERTNER:
    def __init__(self, model_name: str = NER_MODEL_NAME):
        try:
            import torch
            from transformers import AutoModelForTokenClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Missing NER dependencies. Install: pip install torch transformers") from exc

        self.torch = torch
        logger.info(f"Loading NER model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"NER model ready on {self.device}")

    def _predict_chunk(self, text: str) -> list[dict]:
        encoding = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=NER_MAX_LENGTH,
            truncation=True,
            padding=True,
            return_offsets_mapping=True,
        )
        offset_mapping = encoding.pop("offset_mapping").squeeze(0)
        encoding = {key: value.to(self.device) for key, value in encoding.items()}

        with self.torch.no_grad():
            outputs = self.model(**encoding)

        predictions = self.torch.argmax(outputs.logits.squeeze(0), dim=-1).cpu().tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(encoding["input_ids"].squeeze(0).cpu().tolist())

        results = []
        for token, pred, offset in zip(tokens, predictions, offset_mapping):
            if token in ("[CLS]", "[SEP]", "<s>", "</s>", "[PAD]"):
                continue
            start, end = offset.tolist()
            results.append({"token": token, "tag": LABEL_MAP.get(pred, "O"), "start": start, "end": end})
        return results

    def predict(self, text: str) -> list[NEREntity]:
        return self._merge_bio(self.predict_tokens(text), text)

    def predict_tokens(self, text: str) -> list[dict]:
        sentences = re.split(r"(?<=[.!?;])\s+", text)
        all_tokens = []
        offset = 0
        for sentence in sentences:
            for item in self._predict_chunk(sentence):
                item["start"] += offset
                item["end"] += offset
                all_tokens.append(item)
            offset += len(sentence) + 1
        return all_tokens

    @staticmethod
    def _merge_bio(tokens: list[dict], original_text: str) -> list[NEREntity]:
        entities = []
        current = None

        for token in tokens:
            tag = token["tag"]
            if tag == "O":
                if current:
                    entities.append(current)
                    current = None
                continue

            bio, label = tag.split("-", 1)
            if bio == "B" or not current or current["label"] != label:
                if current:
                    entities.append(current)
                current = {
                    "label": label,
                    "start_char": token["start"],
                    "end_char": token["end"],
                    "tokens": [token["token"]],
                    "bio_tags": [tag],
                }
            else:
                current["end_char"] = token["end"]
                current["tokens"].append(token["token"])
                current["bio_tags"].append(tag)

        if current:
            entities.append(current)

        return [
            NEREntity(
                text=original_text[item["start_char"] : item["end_char"]],
                label=item["label"],
                start_char=item["start_char"],
                end_char=item["end_char"],
                tokens=item["tokens"],
                bio_tags=item["bio_tags"],
            )
            for item in entities
        ]


def annotate_document(json_path: Path, ner_model: ViLegalBERTNER, output_dir: str) -> Path:
    out_dir = Path(output_dir) / "ner"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    annotations = []
    for article in data.get("articles", []):
        content = article.get("content", "")
        if not content.strip():
            continue
        token_annotations = ner_model.predict_tokens(content)
        entities = ner_model._merge_bio(token_annotations, content)
        annotations.append(
            {
                "article_number": article.get("article_number", ""),
                "article_title": article.get("title", ""),
                "token_annotations": [
                    {
                        "token": item["token"],
                        "tag": item["tag"],
                        "start_char": item["start"],
                        "end_char": item["end"],
                    }
                    for item in token_annotations
                ],
                "entities": [
                    {
                        "text": entity.text,
                        "label": entity.label,
                        "start_char": entity.start_char,
                        "end_char": entity.end_char,
                        "tokens": entity.tokens,
                        "bio_tags": entity.bio_tags,
                    }
                    for entity in entities
                ],
            }
        )

    result_path = out_dir / Path(json_path).name.replace(".json", "_ner.json")
    result_path.write_text(
        json.dumps({"metadata": data.get("metadata", {}), "annotations": annotations}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"NER JSON saved: {result_path}")
    return result_path
