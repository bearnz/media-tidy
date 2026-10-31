"""Where everything lives under the library root."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path(r"N:\.plex")


@dataclass(frozen=True)
class Library:
    root: Path

    @property
    def tv(self) -> Path:
        return self.root / "TV"

    @property
    def movies(self) -> Path:
        return self.root / "Movies"

    @property
    def incoming(self) -> Path:
        """Drop folder for new downloads; sorted into TV or Movies."""
        return self.root / "_incoming"

    @property
    def quarantine(self) -> Path:
        """Junk and losing duplicates go here. Nothing is ever deleted."""
        return self.root / "_quarantine"

    @property
    def state(self) -> Path:
        """Plans and undo logs."""
        return self.root / "_media-tidy"

    @property
    def plan_file(self) -> Path:
        return self.state / "plan.csv"
