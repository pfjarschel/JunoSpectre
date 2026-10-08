"""Unit tests for hardware profiles and ProfileManager."""

from src.spectre.control.models import HardwareProfile
from src.spectre.control.profiles import ProfileManager


def test_bundled_profiles_exist_and_validate():
    """Verify that all 8 default bundled profiles exist and load without schema error."""
    mgr = ProfileManager()
    profiles = mgr.list_profiles()

    assert len(profiles) >= 8
    names = {p.profile_name for p in profiles}

    expected_names = {
        "Novation Launch Control XL",
        "Akai MIDImix",
        "Korg nanoKONTROL2",
        "Korg nanoKONTROL Studio",
        "Behringer X-Touch Mini",
        "Arturia BeatStep",
        "Novation Launchkey",
        "Default Generic Controller",
    }
    assert expected_names.issubset(names)

    for p in profiles:
        assert len(p.controls) > 0
        assert len(p.default_bindings) > 0
        assert len(p.device_match_keywords) > 0


def test_profile_auto_detection():
    """Test auto-matching ALSA port names against installed profile keywords."""
    mgr = ProfileManager()

    # Launch Control XL
    p1 = mgr.match_profile_for_device("Launch Control XL:Launch Control XL MIDI 1 20:0")
    assert p1 is not None
    assert "Launch Control" in p1.profile_name

    # Launch Control XL3
    p1_alt = mgr.match_profile_for_device("LCXL3 MIDI Out")
    assert p1_alt is not None
    assert "Launch Control" in p1_alt.profile_name

    # Akai MIDImix
    p2 = mgr.match_profile_for_device("MIDImix:MIDImix MIDI 1 24:0")
    assert p2 is not None
    assert p2.profile_name == "Akai MIDImix"

    # Behringer X-Touch Mini
    p3 = mgr.match_profile_for_device("X-TOUCH MINI 28:0")
    assert p3 is not None
    assert p3.profile_name == "Behringer X-Touch Mini"

    # Non-existent device
    p_none = mgr.match_profile_for_device("SomeRandomSynth 1:0")
    assert p_none is None


def test_load_profile_by_slug_or_name():
    """Test loading profile by short filename or exact name."""
    mgr = ProfileManager()
    prof_by_slug = mgr.load_profile("novation_lc_xl")
    assert prof_by_slug.profile_name == "Novation Launch Control XL"

    prof_by_name = mgr.load_profile("Novation Launch Control XL")
    assert prof_by_name.model == prof_by_slug.model


def test_save_custom_profile(tmp_path):
    """Test serializing and saving a custom user profile."""
    mgr = ProfileManager(profile_dir=tmp_path)
    custom = HardwareProfile(
        profile_name="My Custom Rig",
        manufacturer="DIY",
        model="Prototype 1",
        device_match_keywords=["DIY_RIG"],
        controls={},
        default_bindings=[],
    )
    saved_path = mgr.save_profile(custom)
    assert saved_path.is_file()

    loaded = mgr.load_profile(saved_path)
    assert loaded.profile_name == "My Custom Rig"
    assert loaded.device_match_keywords == ["DIY_RIG"]
