import io
import tarfile

import pytest

from ugi.eval_identity_public import evaluate, sample


def test_external_sampler_keeps_gold_uris_out_of_input_records():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, text in [("a.csv", '"http://dbpedia.org/resource/HiddenGoldA","Alpha","1"\n'
                           '"http://dbpedia.org/resource/HiddenGoldB","Beta","2"\n'),
                           ("b.csv", '"http://dbpedia.org/resource/HiddenGoldA","Alfa","1"\n'
                           '"http://dbpedia.org/resource/HiddenGoldB","Béta","2"\n')]:
            content = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    result = sample(stream.getvalue(), count=2)
    assert len(result) == 4 and sum(label for _, _, label in result) == 2
    for left, right, label in result:
        assert set(left) == set(right) == {"id", "text", "table"}
        assert "HiddenGold" not in str(left) + str(right)
    assert result == sample(stream.getvalue(), count=2)


def test_changed_external_archive_fails_before_graph_access(tmp_path):
    path = tmp_path/"changed.tar.gz"
    path.write_bytes(b"not the frozen public archive")
    with pytest.raises(ValueError, match="archive hash changed"):
        evaluate(path)
