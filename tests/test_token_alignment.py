from src.token_alignment import align_bio


def test_token_entity_alignment():
    label_map={"O":0,"B-X":1,"I-X":2}
    labels=align_bio([(0,0),(0,3),(4,6),(7,9)], [{"start_char":0,"end_char":6,"label":"X"}], label_map)
    assert labels == [-100,1,2,0]
