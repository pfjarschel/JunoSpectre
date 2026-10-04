"""Unit tests for Roland waveform catalogs and WaveCatalogManager."""

import pytest
from src.spectre.core.waves import WaveCatalogManager
from src.spectre.vector.engine import VectorEngine
from src.spectre.ui.bridge import SpectreBridge


def test_wave_catalog_manager_singleton():
    mgr1 = WaveCatalogManager.get_instance()
    mgr2 = WaveCatalogManager.get_instance()
    assert mgr1 is mgr2


def test_wave_catalog_acoustic_classification():
    mgr = WaveCatalogManager.get_instance()
    
    # Wave 1: Grand Piano
    w1 = mgr.get_wave("INTA", 1)
    assert w1["category"] == "piano"
    assert w1["icon"] == "piano"
    
    # Wave 242: Nasty Gtr
    w242 = mgr.get_wave("INTA", 242)
    assert w242["category"] == "guitar"
    assert w242["icon"] == "guitar"

    # Wave 1816: Open Triangl (Percussion)
    w1816 = mgr.get_wave("INTA", 1816)
    assert w1816["category"] == "drums"
    assert w1816["icon"] == "drum"


def test_wave_catalog_synth_wave_classification():
    mgr = WaveCatalogManager.get_instance()
    
    # Wave 579: Juno Saw HD
    w579 = mgr.get_wave("INTA", 579)
    assert w579["name"] == "Juno Saw HD"
    assert w579["category"] == "synth_wave"
    assert w579["icon"] == "wave"
    assert w579["is_single_cycle"] is True
    
    # Wave 600: Juno Sqr HD
    w600 = mgr.get_wave("INTA", 600)
    assert w600["name"] == "Juno Sqr HD"
    assert w600["is_single_cycle"] is True

    # Wave 625: Sine
    w625 = mgr.get_wave("INTA", 625)
    assert w625["name"] == "Sine"
    assert w625["is_single_cycle"] is True


def test_wave_catalog_fallback():
    mgr = WaveCatalogManager.get_instance()
    w_invalid = mgr.get_wave("INTA", 99999)
    assert w_invalid["id"] == 99999
    assert w_invalid["is_single_cycle"] is False


def test_basic_synth_waves_priority():
    """Verify that classic bread-and-butter synth waveforms are prioritized at the top of ALL and synth_wave."""
    mgr = WaveCatalogManager.get_instance()

    # Category ALL
    waves_all = mgr.get_filtered_waves(category="ALL", bank="ALL", search="")
    assert waves_all[0]["name"] == "ARP Sine HD"
    assert waves_all[1]["name"] == "Sine"
    assert waves_all[2]["name"] == "JD Triangle"
    assert waves_all[3]["name"] == "VS-Triangle"
    assert waves_all[4]["name"] == "Juno Saw HD"
    assert waves_all[5]["name"] == "JP-8 Saw"
    assert waves_all[6]["name"] == "MG Saw HD"
    assert waves_all[7]["name"] == "P5 Saw HD"
    assert waves_all[8]["name"] == "Juno Sqr HD"
    assert waves_all[9]["name"] == "JP-8 Square"
    assert waves_all[10]["name"] == "MG Sqr HD"
    assert waves_all[11]["name"] == "P5 Sqr HD"
    assert waves_all[12]["name"] == "JP8 Pls 10HD"

    # Category synth_wave
    waves_osc = mgr.get_filtered_waves(category="synth_wave", bank="ALL", search="")
    assert waves_osc[0]["name"] == "ARP Sine HD"
    assert waves_osc[1]["name"] == "Sine"
    assert waves_osc[2]["name"] == "JD Triangle"
    assert waves_osc[3]["name"] == "VS-Triangle"
    assert waves_osc[4]["name"] == "Juno Saw HD"
    assert waves_osc[5]["name"] == "JP-8 Saw"
    assert waves_osc[6]["name"] == "MG Saw HD"
    assert waves_osc[7]["name"] == "P5 Saw HD"
    assert waves_osc[8]["name"] == "Juno Sqr HD"
    assert waves_osc[9]["name"] == "JP-8 Square"
    assert waves_osc[10]["name"] == "MG Sqr HD"
    assert waves_osc[11]["name"] == "P5 Sqr HD"
    assert waves_osc[12]["name"] == "JP8 Pls 10HD"

    # Priority should NOT override non-synth categories
    waves_piano = mgr.get_filtered_waves(category="piano", bank="ALL", search="")
    assert waves_piano[0]["name"] != "ARP Sine HD"


def test_bridge_tone_wave_integration():
    engine = VectorEngine()
    bridge = SpectreBridge(engine)
    
    waves = bridge.toneWaveData
    assert len(waves) == 4
    assert waves[0]["name"] == "Juno Saw HD"
    assert waves[1]["name"] == "Juno Sqr HD"
    assert waves[2]["name"] == "700 Triangle"
    assert waves[3]["name"] == "Sine"
    
    # Switch Tone 1 to Piano
    bridge.setToneWave(1, "INTA", 1)
    updated = bridge.toneWaveData
    assert updated[0]["name"] == "Ult.P*mp A L"
    assert updated[0]["category"] == "piano"
    assert updated[0]["samples_64"] is not None


def test_extract_single_cycle_synthetic_periodic():
    np = pytest.importorskip("numpy")
    signal = pytest.importorskip("scipy.signal")
    from scripts.dump_waveforms import extract_single_cycle

    sr = 48000
    t = np.linspace(0, 0.15, int(sr * 0.15))
    # 261.63 Hz saw wave
    saw = signal.sawtooth(2 * np.pi * 261.63 * t)
    audio_int32 = (saw * (2**31 - 100)).astype(np.int32)

    cycle, freq, peak, is_sc, score, cycle_sim, peak_corr, preview_64 = extract_single_cycle(
        audio_int32, sample_rate=sr, target_samples=1024
    )
    assert is_sc is True
    assert cycle is not None
    assert len(cycle) == 1024
    assert preview_64 is not None
    assert len(preview_64) == 64
    assert 255.0 <= freq <= 265.0
    assert cycle_sim > 0.90
    assert peak_corr > 0.80
    assert score > 0.85


def test_extract_single_cycle_noise():
    np = pytest.importorskip("numpy")
    from scripts.dump_waveforms import extract_single_cycle

    sr = 48000
    noise = np.random.uniform(-0.5, 0.5, int(sr * 0.15))
    audio_int32 = (noise * (2**31 - 100)).astype(np.int32)

    cycle, freq, peak, is_sc, score, cycle_sim, peak_corr, preview_64 = extract_single_cycle(
        audio_int32, sample_rate=sr, target_samples=1024
    )
    assert is_sc is True
    assert cycle is not None
    assert len(cycle) == 1024
    assert preview_64 is not None
    assert len(preview_64) == 64
    # Noise has very low periodicity metrics
    assert cycle_sim < 0.30
    assert peak_corr < 0.30
    assert score < 0.30


def test_extract_single_cycle_silence():
    np = pytest.importorskip("numpy")
    from scripts.dump_waveforms import extract_single_cycle

    silence = np.zeros(7200, dtype=np.int32)
    cycle, freq, peak, is_sc, score, cycle_sim, peak_corr, preview_64 = extract_single_cycle(
        silence, sample_rate=48000
    )
    assert is_sc is False
    assert cycle is None
    assert preview_64 is None
    assert peak < 0.005
