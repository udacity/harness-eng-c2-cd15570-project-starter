"""Application paths and Vocareum OpenAI client setup."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HARNESS_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = HARNESS_DIR.parent


# =============================================================================
# Load LLM settings from .env and create the Vocareum OpenAI client
# =============================================================================
def create_llm_client() -> tuple[OpenAI, str, str]:
    load_dotenv(BASE_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            f"Set OPENAI_API_KEY in {BASE_DIR / '.env'} before running the harness."
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    base_url = "https://openai.vocareum.com/v1"
    client = OpenAI(base_url=base_url, api_key=api_key)
    return client, model, base_url


@dataclass(frozen=True)
class AppConfig:
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
