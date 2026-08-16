from cover_generator.core.icc_profiles import (
    KNOWN_CMYK_PROFILES,
    bundled_profiles_dir,
    expected_profile_path,
    known_profile_path,
    profiles_dir,
)


def test_profiles_dir_honors_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("COVER_GENERATOR_ICC_DIR", str(tmp_path / "icc"))

    result = profiles_dir()

    assert result == tmp_path / "icc"
    assert result.is_dir()


def test_expected_profile_path_for_known_label(tmp_path, monkeypatch):
    monkeypatch.setenv("COVER_GENERATOR_ICC_DIR", str(tmp_path))
    label = next(iter(KNOWN_CMYK_PROFILES))

    path = expected_profile_path(label)

    assert path == tmp_path / KNOWN_CMYK_PROFILES[label]


def test_expected_profile_path_for_unknown_label_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("COVER_GENERATOR_ICC_DIR", str(tmp_path))

    assert expected_profile_path("Not a real profile") is None


def test_every_known_profile_is_bundled():
    # Guards the preset table against drifting from the shipped files.
    bundled = bundled_profiles_dir()
    for filename in KNOWN_CMYK_PROFILES.values():
        assert (bundled / filename).exists(), f"missing bundled profile: {filename}"


def test_known_profile_path_uses_bundled_when_user_dir_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("COVER_GENERATOR_ICC_DIR", str(tmp_path))  # empty user dir
    label = next(iter(KNOWN_CMYK_PROFILES))

    result = known_profile_path(label)

    assert result == bundled_profiles_dir() / KNOWN_CMYK_PROFILES[label]
    assert result.exists()


def test_known_profile_path_prefers_user_override(tmp_path, monkeypatch):
    monkeypatch.setenv("COVER_GENERATOR_ICC_DIR", str(tmp_path))
    label = next(iter(KNOWN_CMYK_PROFILES))
    override = tmp_path / KNOWN_CMYK_PROFILES[label]
    override.write_bytes(b"not a real icc file")

    result = known_profile_path(label)

    assert result == override
