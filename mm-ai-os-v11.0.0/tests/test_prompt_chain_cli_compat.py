from mmos.cli import build_parser


def _parse(args):
    return build_parser().parse_args(args)


def test_v11_prompt_chain_aliases_parse():
    assert _parse(['problem-parse-v3', 'case_a']).cmd == 'problem-parse-v3'
    assert _parse(['ingest-documents', 'case_a', '--unpack-archives']).unpack_archives is True
    assert _parse(['solver-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['contract-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['validator-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['negative-test-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['mutation-test-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['model-fidelity-plan-build', 'case_a', '--all', '--from', 'compiled-protocol']).from_source == 'compiled-protocol'
    assert _parse(['experiment-record', 'case_a', '--all']).all is True
    assert _parse(['output-build', 'case_a', '--all-required', '--accept-draft']).accept_draft is True
    assert _parse(['output-validate', 'case_a', '--semantic', '--freshness', '--all-required']).all_required is True
