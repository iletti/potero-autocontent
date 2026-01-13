Reference assets live here.

Recommended structure:

assets/references/
  manifest.json
  m05/
    m05_swatch.png
  hoodies/
    hoodie_013_ranger_green_front.png
    hoodie_013_ranger_green_macro.png
  anchors/
    optional_manual_anchor.png

Manifest format (example):

{
  "global_references": [],
  "m05_swatches": ["m05/m05_swatch.png"],
  "designs": {
    "hoodie_013_ranger_green": {
      "front": "hoodies/hoodie_013_ranger_green_front.png",
      "macro": "hoodies/hoodie_013_ranger_green_macro.png"
    }
  }
}

Only list files that exist on disk. The registry validates missing files
on startup and can fail fast when required.
