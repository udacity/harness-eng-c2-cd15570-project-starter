"""Application paths and Azure defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_API_VERSION = "2025-03-01-preview"
HARNESS_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = HARNESS_DIR.parent


@dataclass(frozen=True)
class AppConfig:
    vault_url: str
    inventory_file: Path
    history_file: Path
    sales_reviews_file: Path
    skills_dir: Path
    output_dir: Path
    plot_dir: Path

    @classmethod
    def from_environment(cls) -> "AppConfig":
        output_dir = BASE_DIR / "outputs"
        return cls(
            vault_url=os.environ.get(
                "AZURE_KEY_VAULT_URL",
                "https://secrets-pk.vault.azure.net/",
            ),
            inventory_file=Path(
                os.environ.get(
                    "INVENTORY_FILE",
                    str(BASE_DIR / "data" / "synthetic_dealer_inventory.csv"),
                )
            ),
            history_file=Path(
                os.environ.get(
                    "HISTORY_FILE",
                    str(BASE_DIR / "data" / "synthetic_vehicle_history.csv"),
                )
            ),
            sales_reviews_file=Path(
                os.environ.get(
                    "SALES_REVIEWS_FILE",
                    str(BASE_DIR / "data" / "vehicle_sales_reviews.csv"),
                )
            ),
            skills_dir=HARNESS_DIR / "stage_02_skills",
            output_dir=output_dir,
            plot_dir=output_dir / "plots",
        )
