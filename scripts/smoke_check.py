import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.asset_registry import AssetRegistry, AssetRegistryError
from src.config import load_config
from src.logging_utils import configure_logging


def main() -> int:
    config = load_config()
    configure_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("smoke_check_start", extra={"run_id": config.run_id})

    config.ensure_output_dir()

    try:
        registry = AssetRegistry.load(
            references_dir=config.references_dir,
            manifest_path=config.asset_manifest_path,
        )
        missing = registry.validate()
        if missing:
            logger.warning(
                "smoke_missing_assets",
                extra={"missing_assets": missing},
            )
            if config.require_assets:
                return 1
        else:
            logger.info(
                "smoke_assets_ok",
                extra={"asset_count": registry.asset_count()},
            )
    except AssetRegistryError as exc:
        logger.error("smoke_asset_registry_error", extra={"error": str(exc)})
        if config.require_assets:
            return 1

    logger.info("smoke_check_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
