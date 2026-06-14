import re
from typing import Tuple, Optional


class ModelVersionService:
    SEMVER_PATTERN = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    @classmethod
    def is_valid_semver(cls, version_str: str) -> bool:
        """Checks if a string is a valid Semantic Version."""
        return bool(cls.SEMVER_PATTERN.match(version_str))

    @classmethod
    def parse_semver(cls, version_str: str) -> Tuple[int, int, int]:
        """Parses a semver string into (major, minor, patch). Raises ValueError if invalid."""
        match = cls.SEMVER_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid semantic version string: '{version_str}'")
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        return major, minor, patch

    @classmethod
    def increment_version(cls, current_version: str, increment_type: str = "patch") -> str:
        """
        Increments a semantic version string.
        increment_type can be 'major', 'minor', or 'patch'.
        """
        major, minor, patch = cls.parse_semver(current_version)
        inc = increment_type.lower().strip()
        if inc == "major":
            return f"{major + 1}.0.0"
        elif inc == "minor":
            return f"{major}.{minor + 1}.0"
        elif inc == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid version increment type: '{increment_type}'. Use major, minor, or patch.")


model_version_service = ModelVersionService()
