from syrin_ext.oxdeai.http_server import create_pep_app

app = create_pep_app(
    expected_audience="pep-gateway.local",
    trusted_key_sets={},
    now=1712448500,
    upstream_executor=lambda action: {"status": "demo", "tool": action["tool"]},
)