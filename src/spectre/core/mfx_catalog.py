"""Roland JUNO-DS 80 Multi-Effects (MFX) Catalog and Metadata.

Defines the complete set of 80 MFX algorithms with accurate hardware parameter specs,
ranges, units, and discrete option enumerations matching Roland JUNO-DS synthesizer RAM.
"""

from typing import Any, Dict, List, Optional

MFX_ALGORITHMS: List[Dict[str, Any]] = [
  {
    "id": 1,
    "name": "01 EQUALIZER",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "LOW FREQ",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "Hz",
        "options": [
          "200",
          "400"
        ]
      },
      {
        "idx": 1,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "MID1 FREQ",
        "val": 4,
        "min": 0,
        "max": 16,
        "unit": "Hz",
        "options": [
          "200",
          "250",
          "315",
          "400",
          "500",
          "630",
          "800",
          "1000",
          "1250",
          "1600",
          "2000",
          "2500",
          "3150",
          "4000",
          "5000",
          "6300",
          "8000"
        ]
      },
      {
        "idx": 3,
        "label": "MID1 GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "MID1 Q",
        "val": 0,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "0.5",
          "1.0",
          "2.0",
          "4.0",
          "8.0"
        ]
      },
      {
        "idx": 5,
        "label": "MID2 FREQ",
        "val": 10,
        "min": 0,
        "max": 16,
        "unit": "Hz",
        "options": [
          "200",
          "250",
          "315",
          "400",
          "500",
          "630",
          "800",
          "1000",
          "1250",
          "1600",
          "2000",
          "2500",
          "3150",
          "4000",
          "5000",
          "6300",
          "8000"
        ]
      },
      {
        "idx": 6,
        "label": "MID2 GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "MID2 Q",
        "val": 0,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "0.5",
          "1.0",
          "2.0",
          "4.0",
          "8.0"
        ]
      },
      {
        "idx": 8,
        "label": "HIGH FREQ",
        "val": 1,
        "min": 0,
        "max": 2,
        "unit": "Hz",
        "options": [
          "2000",
          "4000",
          "8000"
        ]
      },
      {
        "idx": 9,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 10,
        "label": "LEVEL",
        "val": 127,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 2,
    "name": "02 SPECTRUM",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "BAND 1 (250Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 1,
        "label": "BAND 2 (500Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "BAND 3 (1000Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "BAND 4 (1250Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "BAND 5 (2000Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "BAND 6 (3150Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "BAND 7 (4000Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "BAND 8 (8000Hz)",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 8,
        "label": "Q",
        "val": 1,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "0.5",
          "1.0",
          "2.0",
          "4.0",
          "8.0"
        ]
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 3,
    "name": "03 ISOLATOR",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "BOOST/CUT LOW",
        "val": 60,
        "min": 0,
        "max": 64,
        "unit": "dB"
      },
      {
        "idx": 1,
        "label": "BOOST/CUT MID",
        "val": 60,
        "min": 0,
        "max": 64,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "BOOST/CUT HIGH",
        "val": 60,
        "min": 0,
        "max": 64,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "ANTI PHASE LOW SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 4,
        "label": "ANTI PHASE LOW LVL",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "ANTI PHASE MID SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 6,
        "label": "ANTI PHASE MID LVL",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "LOW BOOST SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 8,
        "label": "LOW BOOST LEVEL",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 4,
    "name": "04 LOW BOOST",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "BOOST FREQ",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 1,
        "label": "BOOST GAIN",
        "val": 6,
        "min": 0,
        "max": 12,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "BOOST WIDTH",
        "val": 1,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "WIDE",
          "MID",
          "NARROW"
        ]
      },
      {
        "idx": 3,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 5,
    "name": "05 SUPER FILTER",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "LPF",
          "BPF",
          "HPF",
          "NOTCH"
        ]
      },
      {
        "idx": 1,
        "label": "FILTER SLOPE",
        "val": 1,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "-12dB",
          "-24dB",
          "-36dB"
        ]
      },
      {
        "idx": 2,
        "label": "CUTOFF",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "RESONANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "GAIN",
        "val": 0,
        "min": 0,
        "max": 12,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "MOD SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "RATE",
        "val": 40,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 7
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "idx": 9,
        "label": "MOD DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 6,
    "name": "06 STEP FILTER",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "STEP 01",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "STEP 02",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "STEP 03",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "STEP 04",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "STEP 05",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "STEP 06",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "STEP 07",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "STEP 08",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "STEP 09",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "STEP 10",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "STEP 11",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "STEP 12",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "STEP 13",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "STEP 14",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "STEP 15",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "STEP 16",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 16
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 17
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 18
      },
      {
        "idx": 19,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 20,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "LPF",
          "BPF",
          "HPF",
          "NOTCH"
        ]
      },
      {
        "idx": 21,
        "label": "FILTER SLOPE",
        "val": 1,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "-12dB",
          "-24dB",
          "-36dB"
        ]
      },
      {
        "idx": 22,
        "label": "RESONANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 23,
        "label": "GAIN",
        "val": 0,
        "min": 0,
        "max": 12,
        "unit": "dB"
      },
      {
        "idx": 24,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 7,
    "name": "07 ENHANCER",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "SENS",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "MIX",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 8,
    "name": "08 AUTO WAH",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "LPF",
          "BPF"
        ]
      },
      {
        "idx": 1,
        "label": "MANUAL",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "PEAK",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "SENS",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "POLARITY",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "DOWN",
          "UP"
        ]
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 5
      },
      {
        "label": "RATE",
        "val": 50,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 6
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 7
      },
      {
        "idx": 8,
        "label": "DEPTH",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "PHASE",
        "val": 0,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 10,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 11,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 12,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 9,
    "name": "09 HUMANIZER",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "DRIVE SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 1,
        "label": "DRIVE",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "VOWEL 1",
        "val": 0,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "a",
          "e",
          "i",
          "o",
          "u"
        ]
      },
      {
        "idx": 3,
        "label": "VOWEL 2",
        "val": 2,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "a",
          "e",
          "i",
          "o",
          "u"
        ]
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 4
      },
      {
        "label": "RATE",
        "val": 50,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 5
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 6
      },
      {
        "idx": 7,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "INPUT SYNC SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 9,
        "label": "THRESHOLD",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "MANUAL",
        "val": 50,
        "min": 0,
        "max": 100,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 12,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 13,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 10,
    "name": "10 SPEAKER SIMULATOR",
    "cat": "FILTER/EQ",
    "params": [
      {
        "idx": 0,
        "label": "SPEAKER TYPE",
        "val": 0,
        "min": 0,
        "max": 15,
        "unit": "",
        "options": [
          "SMALL 1",
          "SMALL 2",
          "MIDDLE",
          "JC-120",
          "BUILT-IN",
          "STACK",
          "OPEN 1",
          "OPEN 2",
          "SEALED 1",
          "SEALED 2",
          "METAL 1",
          "METAL 2",
          "BRIGHT 1",
          "BRIGHT 2",
          "DYNAMIC",
          "VINTAGE"
        ]
      },
      {
        "idx": 1,
        "label": "MIC SETTING",
        "val": 1,
        "min": 1,
        "max": 3,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "MIC LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "DIRECT LEVEL",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 11,
    "name": "11 PHASER",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MODE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "STAGES",
        "options": [
          "4-STAGE",
          "8-STAGE",
          "12-STAGE"
        ]
      },
      {
        "idx": 1,
        "label": "MANUAL",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "RATE",
        "val": 45,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "POLARITY",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "INVERSE",
          "SYNCHRO"
        ]
      },
      {
        "idx": 7,
        "label": "RESONANCE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "CROSS FEEDBACK",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "MIX",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 11,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 12,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 12,
    "name": "12 STEP PHASER",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MODE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "STAGES",
        "options": [
          "4-STAGE",
          "8-STAGE",
          "12-STAGE"
        ]
      },
      {
        "idx": 1,
        "label": "MANUAL",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "RATE",
        "val": 45,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "POLARITY",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "INVERSE",
          "SYNCHRO"
        ]
      },
      {
        "idx": 7,
        "label": "RESONANCE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "CROSS FEEDBACK",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "STEP RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "STEP RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 10
      },
      {
        "label": "STEP RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "idx": 12,
        "label": "MIX",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 13,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 14,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 15,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 13,
    "name": "13 MLT STAGE PHASER",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MODE",
        "val": 0,
        "min": 0,
        "max": 5,
        "unit": "STAGES",
        "options": [
          "4-STG",
          "8-STG",
          "12-STG",
          "16-STG",
          "20-STG",
          "24-STG"
        ]
      },
      {
        "idx": 1,
        "label": "MANUAL",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "RATE",
        "val": 45,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "RESONANCE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "MIX",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 10,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 11,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 14,
    "name": "14 INFINITE PHASER",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MODE",
        "val": 1,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "1",
          "2",
          "3",
          "4"
        ]
      },
      {
        "idx": 1,
        "label": "SPEED",
        "val": 100,
        "min": 0,
        "max": 200,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "RESONANCE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "MIX",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 4,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 15,
    "name": "15 RING MODULATOR",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "FREQUENCY",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "SENS",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "POLARITY",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "DOWN",
          "UP"
        ]
      },
      {
        "idx": 3,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 16,
    "name": "16 STEP RING MOD",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "STEP 01",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "STEP 02",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "STEP 03",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "STEP 04",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "STEP 05",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "STEP 06",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "STEP 07",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "STEP 08",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "STEP 09",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "STEP 10",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "STEP 11",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "STEP 12",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "STEP 13",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "STEP 14",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "STEP 15",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "STEP 16",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 16
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 17
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 18
      },
      {
        "idx": 19,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 20,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 21,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 22,
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 23,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 17,
    "name": "17 TREMOLO",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MOD WAVE",
        "val": 0,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "TRI",
          "SQR",
          "SIN",
          "SAW1",
          "SAW2"
        ]
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 18,
    "name": "18 AUTO PAN",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "MOD WAVE",
        "val": 0,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "TRI",
          "SQR",
          "SIN",
          "SAW1",
          "SAW2"
        ]
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "DEPTH",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 19,
    "name": "19 STEP PAN",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "STEP 01",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "STEP 02",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "STEP 03",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "STEP 04",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "STEP 05",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "STEP 06",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "STEP 07",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "STEP 08",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "STEP 09",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "STEP 10",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "STEP 11",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "STEP 12",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "STEP 13",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "STEP 14",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "STEP 15",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "STEP 16",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 16
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 17
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 18
      },
      {
        "idx": 19,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 20,
        "label": "INPUT SYNC SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 21,
        "label": "THRESHOLD",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 22,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 20,
    "name": "20 SLICER",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "STEP 01",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "STEP 02",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "STEP 03",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "STEP 04",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "STEP 05",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "STEP 06",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "STEP 07",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "STEP 08",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "STEP 09",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "STEP 10",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "STEP 11",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "STEP 12",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "STEP 13",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "STEP 14",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "STEP 15",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "STEP 16",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 16
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 17
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 18
      },
      {
        "idx": 19,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 20,
        "label": "INPUT SYNC SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 21,
        "label": "THRESHOLD",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 22,
        "label": "MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "LEGATO",
          "SLASH"
        ]
      },
      {
        "idx": 23,
        "label": "SHUFFLE",
        "val": 0,
        "min": 0,
        "max": 100,
        "unit": "%"
      },
      {
        "idx": 24,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 21,
    "name": "21 ROTARY",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "SPEED",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SLOW",
          "FAST"
        ]
      },
      {
        "idx": 1,
        "label": "WOOFER SLOW",
        "val": 20,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "WOOFER FAST",
        "val": 80,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 3,
        "label": "WOOFER ACCEL",
        "val": 5,
        "min": 0,
        "max": 15,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "WOOFER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "TWEETER SLOW",
        "val": 25,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 6,
        "label": "TWEETER FAST",
        "val": 90,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 7,
        "label": "TWEETER ACCEL",
        "val": 7,
        "min": 0,
        "max": 15,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "TWEETER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "SEPARATION",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 10,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 22,
    "name": "22 VK ROTARY",
    "cat": "MOD",
    "params": [
      {
        "idx": 0,
        "label": "SPEED",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SLOW",
          "FAST"
        ]
      },
      {
        "idx": 1,
        "label": "BRAKE SW",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 2,
        "label": "WOOFER SLOW",
        "val": 20,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 3,
        "label": "WOOFER FAST",
        "val": 80,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 4,
        "label": "WOOFER TRANS UP",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "WOOFER TRANS DN",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "WOOFER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "TWEETER SLOW",
        "val": 25,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 8,
        "label": "TWEETER FAST",
        "val": 90,
        "min": 0,
        "max": 200,
        "unit": "Hz"
      },
      {
        "idx": 9,
        "label": "TWEETER TRANS UP",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "TWEETER TRANS DN",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "TWEETER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "SPREAD",
        "val": 10,
        "min": 0,
        "max": 10,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 14,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 15,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 23,
    "name": "23 CHORUS",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 24,
    "name": "24 FLANGER",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 25,
    "name": "25 STEP FLANGER",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "STEP RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "STEP RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 10
      },
      {
        "label": "STEP RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "idx": 12,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 13,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 26,
    "name": "26 HEXA-CHORUS",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "PRE DELAY DEV",
        "val": 10,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "DEPTH DEV",
        "val": 10,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PAN DEV",
        "val": 10,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 27,
    "name": "27 TREMOLO CHORUS",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "TREMOLO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 5
      },
      {
        "label": "TREMOLO RATE",
        "val": 45,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 6
      },
      {
        "label": "TREMOLO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 7
      },
      {
        "idx": 8,
        "label": "TREMOLO DEPTH",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "TREMOLO PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 10,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 11,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 28,
    "name": "28 SPACE-D",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 125,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "RATE",
        "val": 30,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "DEPTH",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 6,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 29,
    "name": "29 3D CHORUS",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 125,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "OUTPUT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SPEAKER",
          "PHONES"
        ]
      },
      {
        "idx": 9,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 30,
    "name": "30 3D FLANGER",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "OUTPUT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SPEAKER",
          "PHONES"
        ]
      },
      {
        "idx": 10,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 11,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 31,
    "name": "31 3D STEP FLANGER",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 1,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 2,
        "label": "PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 8,
        "label": "FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "STEP RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "STEP RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 10
      },
      {
        "label": "STEP RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "idx": 12,
        "label": "OUTPUT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SPEAKER",
          "PHONES"
        ]
      },
      {
        "idx": 13,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 14,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 32,
    "name": "32 2BAND CHORUS",
    "cat": "CHORUS",
    "params": [
      {
        "label": "SPLIT FREQ",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": "Hz",
        "idx": 0
      },
      {
        "label": "LOW PRE DELAY",
        "val": 0,
        "min": 0,
        "max": 125,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "LOW RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "LOW RATE",
        "val": 10,
        "min": 0,
        "max": 199,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "LOW RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "label": "LOW DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 5
      },
      {
        "label": "LOW PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg",
        "idx": 6
      },
      {
        "label": "HIGH PRE DELAY",
        "val": 0,
        "min": 0,
        "max": 125,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "HIGH RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 8
      },
      {
        "label": "HIGH RATE",
        "val": 10,
        "min": 0,
        "max": 199,
        "unit": "Hz",
        "idx": 9
      },
      {
        "label": "HIGH RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 10
      },
      {
        "label": "HIGH DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 11
      },
      {
        "label": "HIGH PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg",
        "idx": 12
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 13
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 14
      }
    ]
  },
  {
    "id": 33,
    "name": "33 2BAND FLANGER",
    "cat": "CHORUS",
    "params": [
      {
        "label": "SPLIT FREQ",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": "Hz",
        "idx": 0
      },
      {
        "label": "LOW PRE DELAY",
        "val": 0,
        "min": 0,
        "max": 125,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "LOW RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "LOW RATE",
        "val": 10,
        "min": 0,
        "max": 199,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "LOW RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "label": "LOW DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 5
      },
      {
        "label": "LOW PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg",
        "idx": 6
      },
      {
        "label": "LOW FEEDBACK",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 7
      },
      {
        "label": "HIGH PRE DELAY",
        "val": 0,
        "min": 0,
        "max": 125,
        "unit": "ms",
        "idx": 8
      },
      {
        "label": "HIGH RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "HIGH RATE",
        "val": 10,
        "min": 0,
        "max": 199,
        "unit": "Hz",
        "idx": 10
      },
      {
        "label": "HIGH RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "label": "HIGH DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 12
      },
      {
        "label": "HIGH PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg",
        "idx": 13
      },
      {
        "label": "HIGH FEEDBACK",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 14
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 15
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 16
      }
    ]
  },
  {
    "id": 34,
    "name": "34 2BAND STEP FLNGER",
    "cat": "CHORUS",
    "params": [
      {
        "idx": 0,
        "label": "SPLIT FREQ",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 1,
        "label": "LOW PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "LOW RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "LOW RATE",
        "val": 30,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 3
      },
      {
        "label": "LOW RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "LOW DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "LOW PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 7,
        "label": "LOW FEEDBACK",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "LOW STEP RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 8
      },
      {
        "label": "LOW STEP RATE",
        "val": 50,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 9
      },
      {
        "label": "LOW STEP RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 10
      },
      {
        "idx": 11,
        "label": "LOW BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 12,
        "label": "HIGH PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "HIGH RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 13
      },
      {
        "label": "HIGH RATE",
        "val": 40,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 14
      },
      {
        "label": "HIGH RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 15
      },
      {
        "idx": 16,
        "label": "HIGH DEPTH",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 17,
        "label": "HIGH PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 18,
        "label": "HIGH FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "HIGH STEP RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 19
      },
      {
        "label": "HIGH STEP RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 20
      },
      {
        "label": "HIGH STEP RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 21
      },
      {
        "idx": 22,
        "label": "HIGH BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 23,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 35,
    "name": "35 OVERDRIVE",
    "cat": "DRIVE",
    "params": [
      {
        "idx": 0,
        "label": "DRIVE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "AMP TYPE",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "SMALL",
          "BUILT-IN",
          "2-STACK",
          "3-STACK"
        ]
      },
      {
        "idx": 2,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 36,
    "name": "36 DISTORTION",
    "cat": "DRIVE",
    "params": [
      {
        "idx": 0,
        "label": "DRIVE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "AMP TYPE",
        "val": 1,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "SMALL",
          "BUILT-IN",
          "2-STACK",
          "3-STACK"
        ]
      },
      {
        "idx": 2,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 37,
    "name": "37 VS OVERDRIVE",
    "cat": "DRIVE",
    "params": [
      {
        "idx": 0,
        "label": "DRIVE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "TONE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "AMP SW",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 3,
        "label": "AMP TYPE",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "SMALL",
          "BUILT-IN",
          "2-STACK",
          "3-STACK"
        ]
      },
      {
        "idx": 4,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 38,
    "name": "38 VS DISTORTION",
    "cat": "DRIVE",
    "params": [
      {
        "idx": 0,
        "label": "DRIVE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "TONE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "AMP SW",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 3,
        "label": "AMP TYPE",
        "val": 1,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "SMALL",
          "BUILT-IN",
          "2-STACK",
          "3-STACK"
        ]
      },
      {
        "idx": 4,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 39,
    "name": "39 GUITAR AMP SIM",
    "cat": "DRIVE",
    "params": [
      {
        "idx": 0,
        "label": "PRE AMP SW",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 1,
        "label": "PRE AMP TYPE",
        "val": 0,
        "min": 0,
        "max": 13,
        "unit": "",
        "options": [
          "JC-120",
          "CLEAN TWIN",
          "MATCH DRIVE",
          "BG LEAD",
          "MS1959I",
          "MS1959II",
          "MS1959I+II",
          "SLDN LEAD",
          "METAL 5150",
          "METAL LEAD",
          "OD-1",
          "OD-2 TURBO",
          "DISTORTION",
          "FUZZ"
        ]
      },
      {
        "idx": 2,
        "label": "PRE AMP VOLUME",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "PRE AMP MASTER",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "PRE AMP GAIN",
        "val": 1,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "LOW",
          "MIDDLE",
          "HIGH"
        ]
      },
      {
        "idx": 5,
        "label": "PRE AMP BASS",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "PRE AMP MIDDLE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PRE AMP TREBLE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "PRE AMP PRESENCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "PRE AMP BRIGHT",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 10,
        "label": "SPEAKER SW",
        "val": 1,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "OFF",
          "ON"
        ]
      },
      {
        "idx": 11,
        "label": "SPEAKER TYPE",
        "val": 3,
        "min": 0,
        "max": 15,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "MIC SETTING",
        "val": 1,
        "min": 1,
        "max": 3,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "MIC LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "DIRECT LEVEL",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 16,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 40,
    "name": "40 COMPRESSOR",
    "cat": "DYNAMICS",
    "params": [
      {
        "idx": 0,
        "label": "ATTACK",
        "val": 30,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "THRESHOLD",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "POST GAIN",
        "val": 3,
        "min": 0,
        "max": 18,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 41,
    "name": "41 LIMITER",
    "cat": "DYNAMICS",
    "params": [
      {
        "idx": 0,
        "label": "RELEASE",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "THRESHOLD",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "RATIO",
        "val": 2,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "1.5:1",
          "2:1",
          "4:1",
          "INF:1"
        ]
      },
      {
        "idx": 3,
        "label": "POST GAIN",
        "val": 3,
        "min": 0,
        "max": 18,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 42,
    "name": "42 GATE",
    "cat": "DYNAMICS",
    "params": [
      {
        "idx": 0,
        "label": "THRESHOLD",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "GATE",
          "DUCK"
        ]
      },
      {
        "idx": 2,
        "label": "ATTACK",
        "val": 10,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "HOLD",
        "val": 30,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "RELEASE",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "BALANCE",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 43,
    "name": "43 DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY LEFT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY LEFT",
        "val": 40,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY LEFT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY RIGHT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "DELAY RIGHT",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "DELAY RIGHT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "PHASE LEFT",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "NORMAL",
          "INVERT"
        ]
      },
      {
        "idx": 7,
        "label": "PHASE RIGHT",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "NORMAL",
          "INVERT"
        ]
      },
      {
        "idx": 8,
        "label": "FEEDBACK MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "NORMAL",
          "CROSS"
        ]
      },
      {
        "idx": 9,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 11,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 12,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 13,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 14,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 44,
    "name": "44 LONG DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY TIME",
        "val": 60,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "idx": 3,
        "label": "PHASE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "NORMAL",
          "INVERT"
        ]
      },
      {
        "idx": 4,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 5,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 6,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 45,
    "name": "45 SERIAL DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY 1 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY 1 TIME",
        "val": 250,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY 1 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY 1 FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 3
      },
      {
        "label": "DELAY 1 HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 4
      },
      {
        "label": "DELAY 2 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 5
      },
      {
        "label": "DELAY 2 TIME",
        "val": 500,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 6
      },
      {
        "label": "DELAY 2 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 7
      },
      {
        "label": "DELAY 2 FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 8
      },
      {
        "label": "DELAY 2 HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 9
      },
      {
        "label": "PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 10
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 11
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 12
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 13
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 14
      }
    ]
  },
  {
    "id": 46,
    "name": "46 MODULATION DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY LEFT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY LEFT",
        "val": 40,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY LEFT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY RIGHT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "DELAY RIGHT",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "DELAY RIGHT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "FEEDBACK MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "NORMAL",
          "CROSS"
        ]
      },
      {
        "idx": 7,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "RATE",
        "val": 40,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 10
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "idx": 12,
        "label": "DEPTH",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "PHASE",
        "val": 90,
        "min": 0,
        "max": 180,
        "unit": "deg"
      },
      {
        "idx": 14,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 15,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 16,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 17,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 47,
    "name": "47 3TAP PAN DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY LEFT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY LEFT",
        "val": 200,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY LEFT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY RIGHT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "DELAY RIGHT",
        "val": 400,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "DELAY RIGHT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "label": "DELAY CENTER MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "DELAY CENTER",
        "val": 500,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "DELAY CENTER NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "label": "CENTER FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 9
      },
      {
        "label": "HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 10
      },
      {
        "label": "LEFT LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 11
      },
      {
        "label": "RIGHT LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 12
      },
      {
        "label": "CENTER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 13
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 14
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 15
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 16
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 17
      }
    ]
  },
  {
    "id": 48,
    "name": "48 4TAP PAN DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY 1 TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY 1 TIME",
        "val": 30,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY 1 TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY 2 TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "DELAY 2 TIME",
        "val": 50,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "DELAY 2 TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "label": "DELAY 3 TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "DELAY 3 TIME",
        "val": 70,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "DELAY 3 TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "label": "DELAY 4 TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "DELAY 4 TIME",
        "val": 90,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 10
      },
      {
        "label": "DELAY 4 TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "idx": 12,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 13,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 14,
        "label": "DELAY 1 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "DELAY 2 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 16,
        "label": "DELAY 3 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 17,
        "label": "DELAY 4 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 18,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 19,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 20,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 21,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 49,
    "name": "49 MULTI TAP DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "TAP 1 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "TAP 1 TIME",
        "val": 250,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "TAP 1 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "TAP 2 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "TAP 2 TIME",
        "val": 500,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "TAP 2 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "label": "TAP 3 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "TAP 3 TIME",
        "val": 750,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "TAP 3 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "label": "TAP 4 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 9
      },
      {
        "label": "TAP 4 TIME",
        "val": 1000,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 10
      },
      {
        "label": "TAP 4 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 11
      },
      {
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 12
      },
      {
        "label": "HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 13
      },
      {
        "label": "TAP 1 PAN",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 14
      },
      {
        "label": "TAP 2 PAN",
        "val": 32,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 15
      },
      {
        "label": "TAP 3 PAN",
        "val": 96,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 16
      },
      {
        "label": "TAP 4 PAN",
        "val": 127,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 17
      },
      {
        "label": "TAP 1 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 18
      },
      {
        "label": "TAP 2 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 19
      },
      {
        "label": "TAP 3 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 20
      },
      {
        "label": "TAP 4 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 21
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 22
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 23
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 24
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 25
      }
    ]
  },
  {
    "id": 50,
    "name": "50 REVERSE DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "THRESHOLD",
        "val": 30,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 0
      },
      {
        "label": "REV DELAY MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "REV DELAY TIME",
        "val": 500,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 2
      },
      {
        "label": "REV DELAY NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "label": "REV FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 4
      },
      {
        "label": "REV HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 5
      },
      {
        "label": "REV PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 6
      },
      {
        "label": "REV LEVEL",
        "val": 127,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 7
      },
      {
        "label": "DELAY 1 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 8
      },
      {
        "label": "DELAY 1 TIME",
        "val": 250,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 9
      },
      {
        "label": "DELAY 1 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 10
      },
      {
        "label": "DELAY 2 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 11
      },
      {
        "label": "DELAY 2 TIME",
        "val": 500,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 12
      },
      {
        "label": "DELAY 2 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 13
      },
      {
        "label": "DELAY 3 MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 14
      },
      {
        "label": "DELAY 3 TIME",
        "val": 750,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 15
      },
      {
        "label": "DELAY 3 NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 16
      },
      {
        "label": "DELAY 3 FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 17
      },
      {
        "label": "DELAY HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 18
      },
      {
        "label": "DELAY 1 PAN",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 19
      },
      {
        "label": "DELAY 2 PAN",
        "val": 127,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 20
      },
      {
        "label": "DELAY 1 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 21
      },
      {
        "label": "DELAY 2 LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 22
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 23
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 24
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 25
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 26
      }
    ]
  },
  {
    "id": 51,
    "name": "51 SHUFFLE DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY TIME",
        "val": 60,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "idx": 3,
        "label": "SHUFFLE RATE",
        "val": 50,
        "min": 0,
        "max": 100,
        "unit": "%"
      },
      {
        "idx": 4,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 5,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 6,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 52,
    "name": "52 3D DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY LEFT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY LEFT",
        "val": 200,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY LEFT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "DELAY RIGHT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "DELAY RIGHT",
        "val": 400,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 4
      },
      {
        "label": "DELAY RIGHT NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "label": "DELAY CENTER MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "DELAY CENTER",
        "val": 500,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "DELAY CENTER NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "label": "CENTER FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 9
      },
      {
        "label": "HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 10
      },
      {
        "label": "LEFT LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 11
      },
      {
        "label": "RIGHT LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 12
      },
      {
        "label": "CENTER LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 13
      },
      {
        "label": "OUTPUT MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "SPEAKER",
          "PHONES"
        ],
        "idx": 14
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 15
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 16
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 17
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 18
      }
    ]
  },
  {
    "id": 53,
    "name": "53 ANALOG DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY TIME",
        "val": 250,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "label": "ACCELERATION",
        "val": 8,
        "min": 0,
        "max": 15,
        "unit": "",
        "idx": 3
      },
      {
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 4
      },
      {
        "label": "HF DAMP",
        "val": 17,
        "min": 0,
        "max": 17,
        "unit": "",
        "idx": 5
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 6
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 7
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 8
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 9
      }
    ]
  },
  {
    "id": 54,
    "name": "54 ANALOG LONG DELAY",
    "cat": "DELAY",
    "params": [
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 0
      },
      {
        "label": "DELAY TIME",
        "val": 70,
        "min": 0,
        "max": 2600,
        "unit": "ms",
        "idx": 1
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 2
      },
      {
        "idx": 3,
        "label": "FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 4,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 5,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 55,
    "name": "55 TAPE ECHO",
    "cat": "DELAY",
    "params": [
      {
        "idx": 0,
        "label": "MODE",
        "val": 3,
        "min": 0,
        "max": 6,
        "unit": "",
        "options": [
          "S",
          "M",
          "L",
          "S+M",
          "S+L",
          "M+L",
          "S+M+L"
        ]
      },
      {
        "idx": 1,
        "label": "REPEAT RATE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "INTENSITY",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "BASS",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "TREBLE",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "HEAD S PAN",
        "val": 32,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "HEAD M PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "HEAD L PAN",
        "val": 96,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "TAPE DIST",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 56,
    "name": "56 LOFI NOISE",
    "cat": "LO-FI",
    "params": [
      {
        "idx": 0,
        "label": "LOFI TYPE",
        "val": 0,
        "min": 0,
        "max": 8,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "FILTER TYPE",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ]
      },
      {
        "idx": 2,
        "label": "CUTOFF FREQ",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 3,
        "label": "RADIO DETUNE",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "W/F DEPTH",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "POST GAIN",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 7,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 8,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 57,
    "name": "57 LOFI COMPRESS",
    "cat": "LO-FI",
    "params": [
      {
        "idx": 0,
        "label": "LOFI TYPE",
        "val": 0,
        "min": 0,
        "max": 8,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "POST GAIN",
        "val": 0,
        "min": 0,
        "max": 18,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 3,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 5,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 58,
    "name": "58 LOFI RADIO",
    "cat": "LO-FI",
    "params": [
      {
        "label": "LOFI TYPE",
        "val": 0,
        "min": 0,
        "max": 8,
        "unit": "",
        "options": [
          "1",
          "2",
          "3",
          "4",
          "5",
          "6",
          "7",
          "8",
          "9"
        ],
        "idx": 0
      },
      {
        "label": "POST FILTER",
        "val": 0,
        "min": 0,
        "max": 2,
        "unit": "",
        "options": [
          "OFF",
          "LPF",
          "HPF"
        ],
        "idx": 1
      },
      {
        "label": "FILTER CUTOFF",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "RADIO DETUNE",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 3
      },
      {
        "label": "NOISE LEVEL",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 4
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 5
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 6
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 7
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 8
      }
    ]
  },
  {
    "id": 59,
    "name": "59 TELEPHONE",
    "cat": "LO-FI",
    "params": [
      {
        "idx": 0,
        "label": "VOICE QUALITY",
        "val": 7,
        "min": 0,
        "max": 15,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "TREBLE",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 2,
        "label": "BALANCE",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 3,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 60,
    "name": "60 PHONOGRAPH",
    "cat": "LO-FI",
    "params": [
      {
        "idx": 0,
        "label": "SIGNAL DIST",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "DISC NOISE",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "WOW/FLUTTER",
        "val": 30,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "BALANCE",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 4,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 61,
    "name": "61 PITCH SHIFTER",
    "cat": "PITCH",
    "params": [
      {
        "label": "COARSE",
        "val": 24,
        "min": 0,
        "max": 36,
        "unit": "st",
        "idx": 0
      },
      {
        "label": "FINE",
        "val": 100,
        "min": 0,
        "max": 200,
        "unit": "cent",
        "idx": 1
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "DELAY TIME",
        "val": 0,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 3
      },
      {
        "label": "DELAY NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "label": "FEEDBACK",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "%",
        "idx": 5
      },
      {
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 6
      },
      {
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB",
        "idx": 7
      },
      {
        "label": "BALANCE",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 8
      },
      {
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": "",
        "idx": 9
      }
    ]
  },
  {
    "id": 62,
    "name": "62 2VOI PCH SHIFTER",
    "cat": "PITCH",
    "params": [
      {
        "idx": 0,
        "label": "PCH 1 COARSE",
        "val": 24,
        "min": 0,
        "max": 36,
        "unit": "semi"
      },
      {
        "idx": 1,
        "label": "PCH 1 FINE",
        "val": 50,
        "min": 0,
        "max": 100,
        "unit": "cent"
      },
      {
        "label": "PCH 1 DELAY MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "PCH 1 DELAY",
        "val": 20,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 3
      },
      {
        "label": "PCH 1 DELAY NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "PCH 1 FEEDBACK",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "PCH 1 PAN",
        "val": 32,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "PCH 1 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "PCH 2 COARSE",
        "val": 24,
        "min": 0,
        "max": 36,
        "unit": "semi"
      },
      {
        "idx": 9,
        "label": "PCH 2 FINE",
        "val": 50,
        "min": 0,
        "max": 100,
        "unit": "cent"
      },
      {
        "label": "PCH 2 DELAY MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 10
      },
      {
        "label": "PCH 2 DELAY",
        "val": 40,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 11
      },
      {
        "label": "PCH 2 DELAY NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 12
      },
      {
        "idx": 13,
        "label": "PCH 2 FEEDBACK",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 14,
        "label": "PCH 2 PAN",
        "val": 96,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "PCH 2 LEVEL",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 16,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 17,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 18,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 19,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 63,
    "name": "63 STEP PCH SHIFTER",
    "cat": "PITCH",
    "params": [
      {
        "idx": 0,
        "label": "STEP 01",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "STEP 02",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "STEP 03",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "STEP 04",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 4,
        "label": "STEP 05",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "STEP 06",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 6,
        "label": "STEP 07",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "STEP 08",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 8,
        "label": "STEP 09",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 9,
        "label": "STEP 10",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 10,
        "label": "STEP 11",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "STEP 12",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 12,
        "label": "STEP 13",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 13,
        "label": "STEP 14",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 14,
        "label": "STEP 15",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 15,
        "label": "STEP 16",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 16
      },
      {
        "label": "RATE",
        "val": 60,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 17
      },
      {
        "label": "RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 18
      },
      {
        "idx": 19,
        "label": "ATTACK",
        "val": 20,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 20,
        "label": "FEEDBACK",
        "val": 30,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 21,
        "label": "BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 22,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 64,
    "name": "64 REVERB",
    "cat": "REVERB",
    "params": [
      {
        "idx": 0,
        "label": "REVERB TYPE",
        "val": 4,
        "min": 0,
        "max": 5,
        "unit": "",
        "options": [
          "ROOM 1",
          "ROOM 2",
          "STAGE 1",
          "STAGE 2",
          "HALL 1",
          "HALL 2"
        ]
      },
      {
        "idx": 1,
        "label": "PRE DELAY",
        "val": 20,
        "min": 0,
        "max": 125,
        "unit": "ms"
      },
      {
        "idx": 2,
        "label": "TIME",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 4,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "BALANCE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 65,
    "name": "65 GATED REVERB",
    "cat": "REVERB",
    "params": [
      {
        "idx": 0,
        "label": "TYPE",
        "val": 0,
        "min": 0,
        "max": 3,
        "unit": "",
        "options": [
          "NORMAL",
          "REVERSE",
          "SWEEP 1",
          "SWEEP 2"
        ]
      },
      {
        "idx": 1,
        "label": "PRE DELAY",
        "val": 10,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "idx": 2,
        "label": "GATE TIME",
        "val": 40,
        "min": 0,
        "max": 127,
        "unit": "ms"
      },
      {
        "idx": 3,
        "label": "LOW GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 4,
        "label": "HIGH GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 5,
        "label": "BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 66,
    "name": "66 OD -> CHORUS",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "OD DRIVE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "OD PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "CHO PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "CHO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "CHO RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "CHO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "CHO DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "CHO BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 67,
    "name": "67 OD -> FLANGER",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "OD DRIVE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "OD PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "FLG PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "FLG RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "FLG RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "FLG RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "FLG DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "FLG FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "FLG BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 68,
    "name": "68 OD -> DELAY",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "OD DRIVE",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "OD PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "DELAY TIME",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 3
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DELAY FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "DELAY HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 7,
        "label": "DELAY BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 69,
    "name": "69 DST -> CHORUS",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "DST DRIVE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "DST PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "CHO PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "CHO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "CHO RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "CHO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "CHO DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "CHO BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 70,
    "name": "70 DST -> FLANGER",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "DST DRIVE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "DST PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "FLG PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "FLG RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "FLG RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "FLG RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "FLG DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "FLG FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "FLG BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 71,
    "name": "71 DST -> DELAY",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "DST DRIVE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "DST PAN",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "DELAY TIME",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 3
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DELAY FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "DELAY HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 7,
        "label": "DELAY BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 72,
    "name": "72 ENH -> CHORUS",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "ENH SENS",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "ENH MIX",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "CHO PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "CHO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "CHO RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "CHO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "CHO DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "CHO BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 73,
    "name": "73 ENH -> FLANGER",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "ENH SENS",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "ENH MIX",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "FLG PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "FLG RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 3
      },
      {
        "label": "FLG RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 4
      },
      {
        "label": "FLG RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 5
      },
      {
        "idx": 6,
        "label": "FLG DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 7,
        "label": "FLG FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "FLG BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 9,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 74,
    "name": "74 ENH -> DELAY",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "ENH SENS",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "ENH MIX",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 2
      },
      {
        "label": "DELAY TIME",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 3
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 4
      },
      {
        "idx": 5,
        "label": "DELAY FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "DELAY HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 7,
        "label": "DELAY BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 8,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 75,
    "name": "75 CHORUS -> DELAY",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "CHO PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "CHO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "CHO RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "CHO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "CHO DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "CHO BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 6
      },
      {
        "label": "DELAY TIME",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 7
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 8
      },
      {
        "idx": 9,
        "label": "DELAY FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 10,
        "label": "DELAY HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 11,
        "label": "DELAY BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 12,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 76,
    "name": "76 FLANGER -> DELAY",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "FLG PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "FLG RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "FLG RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "FLG RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "FLG DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "FLG FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "FLG BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "label": "DELAY TIME MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "ms",
          "NOTE"
        ],
        "idx": 7
      },
      {
        "label": "DELAY TIME",
        "val": 50,
        "min": 0,
        "max": 1300,
        "unit": "ms",
        "idx": 8
      },
      {
        "label": "DELAY TIME NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 9
      },
      {
        "idx": 10,
        "label": "DELAY FEEDBACK",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 11,
        "label": "DELAY HF DAMP",
        "val": 16,
        "min": 0,
        "max": 17,
        "unit": "Hz"
      },
      {
        "idx": 12,
        "label": "DELAY BALANCE",
        "val": 70,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 13,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 77,
    "name": "77 CHORUS -> FLANGER",
    "cat": "COMBINATION",
    "params": [
      {
        "idx": 0,
        "label": "CHO PRE DELAY",
        "val": 15,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "CHO RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 1
      },
      {
        "label": "CHO RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 2
      },
      {
        "label": "CHO RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 3
      },
      {
        "idx": 4,
        "label": "CHO DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 5,
        "label": "CHO BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 6,
        "label": "FLG PRE DELAY",
        "val": 5,
        "min": 0,
        "max": 100,
        "unit": "ms"
      },
      {
        "label": "FLG RATE MODE",
        "val": 0,
        "min": 0,
        "max": 1,
        "unit": "",
        "options": [
          "Hz",
          "NOTE"
        ],
        "idx": 7
      },
      {
        "label": "FLG RATE",
        "val": 35,
        "min": 0,
        "max": 200,
        "unit": "Hz",
        "idx": 8
      },
      {
        "label": "FLG RATE NOTE",
        "val": 12,
        "min": 0,
        "max": 21,
        "unit": "",
        "options": [
          "1/64T",
          "1/64",
          "1/32T",
          "1/32",
          "1/16T",
          "1/32.",
          "1/16",
          "1/8T",
          "1/16.",
          "1/8",
          "1/4T",
          "1/8.",
          "1/4",
          "1/2T",
          "1/4.",
          "1/2",
          "1/1T",
          "1/2.",
          "1/1",
          "2/1T",
          "1/1.",
          "2/1"
        ],
        "idx": 9
      },
      {
        "idx": 10,
        "label": "FLG DEPTH",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 11,
        "label": "FLG FEEDBACK",
        "val": 65,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 12,
        "label": "FLG BALANCE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": "%"
      },
      {
        "idx": 13,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 78,
    "name": "78 SYMPATHETIC RESO",
    "cat": "SPECIAL",
    "params": [
      {
        "idx": 0,
        "label": "DEPTH",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "DAMPER",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "PRE LPF",
        "val": 16,
        "min": 0,
        "max": 30,
        "unit": "Hz"
      },
      {
        "idx": 3,
        "label": "PRE HPF",
        "val": 0,
        "min": 0,
        "max": 30,
        "unit": "Hz"
      },
      {
        "idx": 4,
        "label": "PEAKING FREQ",
        "val": 50,
        "min": 0,
        "max": 127,
        "unit": "Hz"
      },
      {
        "idx": 5,
        "label": "PEAKING GAIN",
        "val": 15,
        "min": 0,
        "max": 30,
        "unit": "dB"
      },
      {
        "idx": 6,
        "label": "PEAKING Q",
        "val": 1,
        "min": 0,
        "max": 4,
        "unit": "",
        "options": [
          "0.5",
          "1.0",
          "2.0",
          "4.0",
          "8.0"
        ]
      },
      {
        "idx": 7,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 79,
    "name": "79 Di VOCODER",
    "cat": "SPECIAL",
    "params": [
      {
        "idx": 0,
        "label": "MIC SENS",
        "val": 64,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "SYNTH LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 2,
        "label": "MIC MIX",
        "val": 0,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  },
  {
    "id": 80,
    "name": "80 BIT CRUSHER",
    "cat": "SPECIAL",
    "params": [
      {
        "idx": 0,
        "label": "SAMPLE RATE",
        "val": 80,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 1,
        "label": "BIT DOWN",
        "val": 4,
        "min": 0,
        "max": 20,
        "unit": "bits"
      },
      {
        "idx": 2,
        "label": "FILTER",
        "val": 60,
        "min": 0,
        "max": 127,
        "unit": ""
      },
      {
        "idx": 3,
        "label": "LEVEL",
        "val": 100,
        "min": 0,
        "max": 127,
        "unit": ""
      }
    ]
  }
]


MFX_CATEGORIES = [
    "ALL",
    "FILTER/EQ",
    "MOD",
    "CHORUS",
    "DRIVE",
    "DYNAMICS",
    "DELAY",
    "LO-FI",
    "PITCH",
    "REVERB",
    "COMBINATION",
    "SPECIAL"
]

_ALGO_BY_ID = {a["id"]: a for a in MFX_ALGORITHMS}

# Precomputed lightweight lists by category for instant UI switching (0ms latency)
_LIGHT_CATALOG = [{"id": a["id"], "name": a["name"], "cat": a["cat"]} for a in MFX_ALGORITHMS]
_LIGHT_BY_CAT = {"ALL": _LIGHT_CATALOG}
for _cat in MFX_CATEGORIES[1:]:
    _LIGHT_BY_CAT[_cat] = [a for a in _LIGHT_CATALOG if a["cat"] == _cat]

def get_mfx_catalog() -> List[Dict[str, Any]]:
    """Return all 80 MFX algorithms with full parameter definitions."""
    return MFX_ALGORITHMS

def get_mfx_light_catalog(category: str = "ALL") -> List[Dict[str, Any]]:
    """Return lightweight algorithm list (id, name, cat only) precomputed by category."""
    return _LIGHT_BY_CAT.get(category, _LIGHT_CATALOG)

def get_mfx_algo(algo_id: int) -> Optional[Dict[str, Any]]:
    """Lookup an MFX algorithm by 1-based ID."""
    return _ALGO_BY_ID.get(algo_id)

def get_mfx_categories() -> List[str]:
    """Return list of MFX categories."""
    return MFX_CATEGORIES
