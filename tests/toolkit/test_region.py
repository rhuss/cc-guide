import pytest

import region


def test_parse_balanced_splits_prefix_content_suffix():
    text = ("author intro\n"
            "<!-- guide:region -->\n"
            "guide line\n"
            "<!-- /guide:region -->\n"
            "author outro\n")
    r = region.parse(text)
    assert r.marked
    assert r.begin_line == 2
    assert r.end_line == 4
    assert r.author_prefix == "author intro\n"
    assert r.content == "guide line\n"
    assert r.author_suffix == "author outro\n"


def test_parse_without_markers_takes_the_whole_file():
    text = "# Just a README\n\nAll mine.\n"
    r = region.parse(text)
    assert not r.marked
    assert r.begin_line == 0 and r.end_line == 0
    assert r.author_prefix == "" and r.author_suffix == ""
    assert r.content == text


def test_parse_empty_region():
    text = "above\n<!-- guide:region -->\n<!-- /guide:region -->\nbelow\n"
    r = region.parse(text)
    assert r.marked
    assert r.content == ""
    assert r.author_prefix == "above\n"
    assert r.author_suffix == "below\n"


def test_parse_unbalanced_begin_without_end():
    text = "intro\n<!-- guide:region -->\nguide\n"
    with pytest.raises(region.RegionError) as err:
        region.parse(text)
    assert err.value.rule == "region-unbalanced"
    assert err.value.line == 2


def test_parse_unbalanced_end_without_begin():
    text = "guide\n<!-- /guide:region -->\noutro\n"
    with pytest.raises(region.RegionError) as err:
        region.parse(text)
    assert err.value.rule == "region-unbalanced"
    assert err.value.line == 2


def test_parse_unbalanced_end_before_begin():
    text = "<!-- /guide:region -->\nlater\n<!-- guide:region -->\n"
    with pytest.raises(region.RegionError) as err:
        region.parse(text)
    assert err.value.rule == "region-unbalanced"


def test_parse_duplicate_pairs():
    text = ("a\n<!-- guide:region -->\ng\n<!-- /guide:region -->\n"
            "b\n<!-- guide:region -->\nh\n<!-- /guide:region -->\n")
    with pytest.raises(region.RegionError) as err:
        region.parse(text)
    assert err.value.rule == "region-duplicate"
    assert "2 begin" in str(err.value)


def test_markers_inside_fenced_code_blocks_are_text():
    text = ("intro\n"
            "```md\n"
            "<!-- guide:region -->\n"
            "```\n"
            "<!-- guide:region -->\n"
            "real guide content\n"
            "<!-- /guide:region -->\n"
            "```md\n"
            "<!-- /guide:region -->\n"
            "```\n"
            "outro\n")
    r = region.parse(text)
    assert r.begin_line == 5
    assert r.end_line == 7
    assert r.content == "real guide content\n"
    assert r.author_prefix == "intro\n```md\n<!-- guide:region -->\n```\n"
    assert r.author_suffix == "```md\n<!-- /guide:region -->\n```\noutro\n"


def test_tilde_fences_mask_markers_too():
    text = "~~~\n<!-- guide:region -->\n~~~\n<!-- guide:region -->\nx\n<!-- /guide:region -->\n"
    r = region.parse(text)
    assert r.begin_line == 4 and r.end_line == 6


def test_splice_preserves_author_text_byte_for_byte():
    prefix = "author bytes \r\n weird   spacing\n\n"
    suffix = "\ntrailing author text without newline at end"
    text = prefix + "<!-- guide:region -->\nold guide content\n<!-- /guide:region -->\n" + suffix
    out = region.splice(text, "new guide content\n")
    assert out.startswith(prefix)
    assert out.endswith(suffix)
    assert "new guide content" in out
    assert "old guide content" not in out
    # a second splice with the same content is the identity (idempotent writer)
    assert region.splice(out, "new guide content\n") == out


def test_splice_without_markers_replaces_the_whole_file():
    assert region.splice("# all mine\n", "# all guide\n") == "# all guide\n"


def test_splice_empty_region_content():
    text = "a\n<!-- guide:region -->\n<!-- /guide:region -->\nb\n"
    assert region.splice(text, "filled\n") == "a\n<!-- guide:region -->\nfilled\n<!-- /guide:region -->\nb\n"


def test_normalized_empties_attr_values_inside_the_region_only():
    text = ("<!-- guide:attr x -->typed<!-- /guide:attr -->\n"
            "<!-- guide:region -->\n"
            "v<!-- guide:attr y -->1.2.3<!-- /guide:attr -->\n"
            "<!-- /guide:region -->\n"
            "a<!-- guide:attr z -->9<!-- /guide:attr -->\n")
    assert region.normalized(text) == "v<!-- guide:attr y --><!-- /guide:attr -->\n"


def test_normalized_whole_file_without_markers():
    text = "x<!-- guide:attr y -->1.2.3<!-- /guide:attr -->\n"
    assert region.normalized(text) == "x<!-- guide:attr y --><!-- /guide:attr -->\n"
