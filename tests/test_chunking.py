class FakeTokenizer:
    is_fast = True
    def __call__(self, text, **kwargs):
        return {"input_ids": [[0, 4, 5, 2], [0, 5, 6, 2]],
                "attention_mask": [[1]*4, [1]*4],
                "offset_mapping": [[(0,0),(0,3),(4,7),(0,0)],[(0,0),(4,7),(8,10),(0,0)]]}


from src.chunking import make_chunks


def test_chunks_have_global_offsets_and_overlap():
    chunks = make_chunks("abc def gh", FakeTokenizer(), 4, 1)
    assert chunks[0]["end_char"] == chunks[1]["start_char"] == 7 or chunks[1]["start_char"] == 4
    covered = {(a,b) for c in chunks for a,b in c["offset_mapping"] if b>a}
    assert (0,3) in covered and (8,10) in covered


class SlowTokenizer:
    is_fast = False
    unk_token_id = 99
    def tokenize(self, word): return [word[:1], word[1:]] if len(word)>1 else [word]
    def convert_tokens_to_ids(self, pieces): return list(range(10,10+len(pieces)))
    def num_special_tokens_to_add(self, pair=False): return 2
    def build_inputs_with_special_tokens(self, ids): return [0]+ids+[2]
    def get_special_tokens_mask(self, ids, already_has_special_tokens=False): return [1]+[0]*len(ids)+[1]


def test_slow_phobert_path_preserves_word_offsets():
    chunks=make_chunks("abc de f",SlowTokenizer(),6,2)
    assert chunks[0]["offset_mapping"][1:3] == [(0,3),(0,3)]
    assert chunks[-1]["end_char"] == 8
