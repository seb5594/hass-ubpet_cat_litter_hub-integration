"""Load entity metadata separately from platform behaviour and wire projections."""

import json
from pathlib import Path

from homeassistant.helpers.entity import EntityCategory

METRICS = json.loads(Path(__file__).with_name("metrics.json").read_text(encoding="utf-8"))


def metric_descriptions(platform, description_type):
    for row in METRICS:
        if row["platform"] == platform:
            metadata = {key: value for key, value in row.items() if key not in {"subject", "platform"}}
            if "entity_category" in metadata:
                metadata["entity_category"] = EntityCategory(metadata["entity_category"])
            yield row["subject"], description_type(translation_key=row["key"], **metadata)
