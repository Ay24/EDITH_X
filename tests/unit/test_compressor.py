import pytest
from edith_x.modules.optimization.compressor import InformationDensityCompressor

def test_compressor_keeps_under_budget():
    compressor = InformationDensityCompressor()
    text = (
        "Please note that it is important to remember that furthermore, in addition to this, "
        "as previously mentioned, our enterprise database requires SSL encryption on port 5432. "
        "Furthermore, you should make sure that the database user admin is configured properly. "
        "The api key is secret_9988 and the timeout is 30 seconds."
    )
    result = compressor.compress(text, budget=28)
    assert result.compressed_tokens <= 30
    assert result.compression_ratio < 1.0
    # Crucial technical facts must be preserved
    assert "5432" in result.compressed_text
    assert "ssl" in result.compressed_text.lower()

def test_compressor_preserves_short_prompt():
    compressor = InformationDensityCompressor()
    text = "Write a python function to reverse a string."
    result = compressor.compress(text, budget=100)
    assert result.compression_ratio == 1.0
    assert result.compressed_text == text
