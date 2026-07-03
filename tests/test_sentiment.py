from core.sentiment import Sentiment


def test_classify_extreme_fear():
    s = Sentiment()
    assert s._classify(5) == "Extreme Fear"
    assert s._classify(10) == "Extreme Fear"


def test_classify_fear():
    s = Sentiment()
    assert s._classify(20) == "Fear"
    assert s._classify(30) == "Fear"


def test_classify_neutral():
    s = Sentiment()
    assert s._classify(40) == "Neutral"
    assert s._classify(50) == "Neutral"
    assert s._classify(60) == "Neutral"
    assert s._classify(70) == "Neutral"


def test_classify_greed():
    s = Sentiment()
    assert s._classify(80) == "Greed"
    assert s._classify(90) == "Greed"


def test_classify_extreme_greed():
    s = Sentiment()
    assert s._classify(95) == "Extreme Greed"
    assert s._classify(100) == "Extreme Greed"


def test_init_with_defaults():
    s = Sentiment()
    assert 0 <= s.value <= 100
    assert isinstance(s.classification, str)


def test_get_raw_value():
    s = Sentiment()
    assert isinstance(s.get_raw_value(), int)
    assert 0 <= s.get_raw_value() <= 100


def test_score_normalized():
    s = Sentiment()
    score = s.score()
    assert 0.0 <= score <= 1.0
    assert score == s.value / 100.0


def test_classification_method():
    s = Sentiment()
    assert isinstance(s.classification, str)


def test_repr():
    s = Sentiment()
    assert "Sentiment" in repr(s)


def test_init_from_cache(tmp_path):
    import json
    cache_dir = tmp_path / "storage"
    cache_dir.mkdir()
    cache_file = cache_dir / "sentiment_cache.json"
    cache_data = {"value": 25, "classification": "Fear", "timestamp": "2026-06-01T00:00:00"}
    cache_file.write_text(json.dumps(cache_data))

    # Temporarily replace CACHE_FILE
    import core.sentiment as sm
    orig = sm.Sentiment.CACHE_FILE
    sm.Sentiment.CACHE_FILE = str(cache_file)
    s = Sentiment()
    sm.Sentiment.CACHE_FILE = orig

    assert s.value == 25
    assert s.classification == "Fear"
