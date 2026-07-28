from src.postprocess import decode_bio, merge_entities


def test_decode_and_merge_duplicate_chunks():
    tokens=[{"start_char":0,"end_char":3,"label":"B-X","confidence":.8,"chunk_id":"a"},
            {"start_char":4,"end_char":6,"label":"I-X","confidence":.9,"chunk_id":"a"}]
    entity=decode_bio(tokens)[0]
    assert (entity["start_char"],entity["end_char"],entity["label"]) == (0,6,"X")
    merged=merge_entities([entity, {**entity,"chunk_ids":["b"],"confidences":[.7]}])
    assert len(merged)==1 and set(merged[0]["chunk_ids"])=={"a","b"}
