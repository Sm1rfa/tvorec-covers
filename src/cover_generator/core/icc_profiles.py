"""Known CMYK ICC profile presets and lookup helpers.

The app now ships with the freely distributed ECI profile packs (ECI Offset
2009 and eciCMYK v2, from eci.org), bundled under
``cover_generator/resources/icc_profiles``. So the common European offset
profiles -- including ISO Coated v2, the FOGRA39 characterization behind
"Coated FOGRA39" -- work out of the box with no download or setup.

Users can still override or extend the set: drop a .icc file into
``profiles_dir()`` under the exact filename a preset expects (that copy wins
over the bundled one), or pick "Custom..." in the GUI and point at any file
on disk. US profiles (GRACoL, SWOP) and other vendor profiles are not
bundled -- add them yourself via either mechanism.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

# label -> filename (as bundled in resources/icc_profiles and/or dropped into
# profiles_dir()). Ordered with the coated FOGRA39 profiles first, since
# those are the usual default for book covers on coated stock.
KNOWN_CMYK_PROFILES: dict[str, str] = {
    "Coated FOGRA39 -- ISO Coated v2 (EU coated offset)": "ISOcoated_v2_eci.icc",
    "Coated FOGRA39 300% -- ISO Coated v2 (EU coated, TAC 300)": "ISOcoated_v2_300_eci.icc",
    "eciCMYK v2 -- FOGRA53 (EU, large gamut)": "eciCMYK_v2.icc",
    "PSO Coated NPscreen ISO 12647 (EU coated)": "PSO_Coated_NPscreen_ISO12647_eci.icc",
    "PSO Coated 300% NPscreen ISO 12647 (EU coated)": "PSO_Coated_300_NPscreen_ISO12647_eci.icc",
    "PSO Uncoated ISO 12647 (EU uncoated offset)": "PSO_Uncoated_ISO12647_eci.icc",
    "PSO Uncoated NPscreen ISO 12647 (EU uncoated)": "PSO_Uncoated_NPscreen_ISO12647_eci.icc",
    "ISO Uncoated Yellowish (EU uncoated)": "ISOuncoatedyellowish.icc",
    "PSO LWC Standard (web offset, LWC paper)": "PSO_LWC_Standard_eci.icc",
    "PSO LWC Improved (web offset, LWC paper)": "PSO_LWC_Improved_eci.icc",
    "PSO MFC Paper (web offset, MFC paper)": "PSO_MFC_Paper_eci.icc",
    "PSO SNP Paper (web offset, SNP paper)": "PSO_SNP_Paper_eci.icc",
    "SC Paper (web offset, SC paper)": "SC_paper_eci.icc",
}


def profiles_dir() -> Path:
    """Per-user directory for override / extra ICC files.

    A .icc file placed here under a preset's expected filename takes
    precedence over the bundled copy. Honors COVER_GENERATOR_ICC_DIR (used by
    tests) before falling back to a per-user directory under the home folder.
    """
    override = os.environ.get("COVER_GENERATOR_ICC_DIR")
    base = Path(override) if override else Path.home() / ".cover-generator" / "icc_profiles"
    base.mkdir(parents=True, exist_ok=True)
    return base


def bundled_profiles_dir() -> Path:
    """Directory of ICC profiles shipped inside the package."""
    return Path(str(resources.files("cover_generator") / "resources" / "icc_profiles"))


def expected_profile_path(label: str) -> Path | None:
    """The user-dir path a preset's .icc file would live at, whether or not it exists.

    This is the location the GUI tells users to drop a file into when they
    want to supply or override a profile themselves.
    """
    filename = KNOWN_CMYK_PROFILES.get(label)
    return profiles_dir() / filename if filename is not None else None


def known_profile_path(label: str) -> Path | None:
    """Resolve a preset label to an existing .icc file, or None if not available.

    A user-supplied copy in ``profiles_dir()`` wins; otherwise the bundled
    copy in ``bundled_profiles_dir()`` is used.
    """
    filename = KNOWN_CMYK_PROFILES.get(label)
    if filename is None:
        return None
    user_copy = profiles_dir() / filename
    if user_copy.exists():
        return user_copy
    bundled_copy = bundled_profiles_dir() / filename
    return bundled_copy if bundled_copy.exists() else None
