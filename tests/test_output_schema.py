import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_output_schema_accepts_minimal_document():
    schema=json.loads(Path("configs/output_schema.json").read_text())
    value={"schema_version":"1.0","document_id":"1","source_file":"x","source_sha256":"0"*64,
           "text_length":0,"model":{},"processing":{},"entities":[],"warnings":[],"errors":[]}
    assert not list(Draft202012Validator(schema).iter_errors(value))
