# Potero Autocontent - User Guide

This guide describes how to provide inputs and references so the system stays Potero Standard, technically credible, and consistent across slides.

---

## 1) Your job in one sentence

Provide high-quality reference images in the correct roles (folders/tags) so the AI can assemble Finnish reservist realism instead of inventing generic tactical gear.

---

## 2) What you must provide (minimum reliable kit)

### A) Mandatory references (every project)

1) Environment vibe (choose at least one preset)
- Finnish taiga (summer)
- Finnish taiga (winter / kaamos)
- CQB training house (OSB walls)
- Finnish industrial hall / yard (concrete, metal)
- Civil defense shelter (brutalist concrete)

Provide 3-8 photos per environment you want to use.

2) Potero lighting exemplars (lo-fi flash)
Provide 3-6 photos that clearly show:
- direct on-axis flash
- harsh shadows behind subject
- background falloff into darkness
- high ISO noise / "bad jpeg" feel

3) M05 camo texture
Provide 2-4 high-res fabric close-ups/scans:
- M05 woodland (organic blotches, not pixel)
- M05 snow (if winter themes)

### B) If you want people in the images (recommended pack)

Provide:
- gloves (Mechanix) close-ups and worn-in-use photos
- helmet + headset refs (PGD high cut + Comtac style)
- boots refs (black combat boots)
- face anonymization style refs (balaclava, shadows, head cropped)

### C) If weapons appear (required)

Provide RK95 TP reference set:
- left profile
- right profile
- muzzle close-up (critical)
- stock/receiver area close-up

If you do not provide these, the model drifts into generic AK/M4.

### D) If load-bearing gear appears (required)

Provide:
- plate carrier refs (ResTac / Finnish setup)
  - full front layout
  - pouch layout close-up
- belt setup refs (M05/OD belt + dump pouch)
  - full belt
  - dump pouch close-up
- Savotta refs
  - backpack 3/4 view
  - PALS grid close-up (critical)
  - straps/connection close-up

---

## 3) How to organize references (roles / folders)

Place images into folders by role. Do not mix roles.

Use this structure:

```
assets/references/
  ENV_TAIGA_SUMMER_NIGHT/
  ENV_TAIGA_WINTER_KAAMOS/
  ENV_CQB_OSB/
  ENV_INDUSTRIAL_HALL/
  ENV_SHELTER/

  LIGHTING_LOFI_FLASH/

  TEXTURE_M05_WOODLAND/
  TEXTURE_M05_SNOW/

  WEAPON_RK95_LEFT/
  WEAPON_RK95_RIGHT/
  WEAPON_RK95_MUZZLE_CLOSE/
  WEAPON_RK95_RECEIVER_STOCK/

  GEAR_PLATE_CARRIER_LAYOUT/
  GEAR_POUCHES_DETAIL/
  GEAR_BELT_DUMP_POUCH/

  GEAR_BACKPACK_JAAKARI_34/
  GEAR_PALS_CLOSE/
  GEAR_STRAPS_CONNECT/

  GEAR_HELMET_HIGH_CUT/
  GEAR_HEADSET_COMTAC/
  GEAR_GLOVES_MECHANIX/
  GEAR_BOOTS_BLACK/

  PROPS_KUKSA/
  PROPS_NOKIPANNU/
  PROPS_WATER_CAN/
  PROPS_MAINTENANCE/
```

If you are using Shopify MCP instead, the system can fetch product images automatically, but you still should provide:
- environment refs
- lo-fi flash refs
- M05 texture refs

---

## 4) Reference quality rules (do not ignore these)

Must-haves
- resolution: preferably 1500px+ on the long edge
- sharp enough to see real material behavior (Cordura stiffness, stitching)
- no heavy filters, no AI upscales, no watercolor noise reduction

Avoid
- tiny images (screenshots)
- strong color grading / cinematic teal-orange
- watermarked images
- images with big readable text or logos

Critical close-ups (do not skip)
- RK95 muzzle close
- Savotta PALS close
- backpack strap connections
- M05 texture close

---

## 5) What you should write as input (themes that work)

When you create a theme or run prompt, keep it short and structured.

Always include:
- environment preset (one of the five)
- season (summer/winter)
- time-of-day (night/afternoon/evening)
- slide intent (continuum phase)

Example theme input:
- "Winter kaamos, Finnish taiga, reservist waiting at fire, coffee ritual, anonymous, lo-fi flash."

Good continuum intents (pick one per slide)
- domestic front (home preparedness)
- mobilization (call / packing)
- transition (civilian -> soldier moment)
- field wait (maintenance / fatigue)
- artifact detail (macro gear detail with flash)

---

## 6) What you must not ask for (will break Potero)

Avoid:
- "cinematic", "epic", "hero shot", "movie poster"
- "golden hour", "sunset glow"
- "high fashion tactical", "operator", "SEAL"
- "add text/logo/patch/name tape"
- "smiling", "perfect skin"

If you want emotion, ask for:
- "stoic", "tired", "waiting", "maintenance", "documentary snapshot"

---

## 7) How to keep OPSEC/PERSEC safe (required user behavior)

- Do not upload photos of real identifiable people unless you have permission.
- Prefer refs where faces are:
  - cropped out
  - covered (balaclava)
  - in shadow
- Do not request readable unit markings, names, license plates, or signage.

If you need a gaze look, use:
- "de-identified gaze: face overexposed by flash or motion blur, not identifiable."

---

## 8) If you want credible Finnish kit (target loadout)

Include refs for:
- M05 camo pants: Crye-style M05 battle pants / Sarma TST battlepants
- Weapon: RK95 TP
- Carrier: ResTac M05 setup with mag pouches + admin pouch
- Pouches: Savotta
- Backpack: Sarma TST or Savotta Jaakari
- Boots: black combat boots
- Belt: M05/OD belt + dump pouch
- Helmet: PGD high cut + Comtac
- Gloves: Mechanix

Important: the system needs visual references for these, not just the names.

---

## 9) Quick checklist before you run

- 1 environment pack (3-8 images)
- 1 lo-fi flash pack (3-6 images)
- M05 texture pack (2-4 images)
- If weapon: RK95 muzzle close + silhouette
- If Savotta: PALS close + straps connect
- If plate carrier/belt: layout + dump pouch refs

If yes, you will get consistent Potero output.

---

## 10) Common mistakes (and how to fix)

"Looks like generic US operator"
- Fix: add more Finnish environment refs + ban Multicam/M4 + include RK95 refs + include Savotta/PALS close.

"Winter looks warm/yellow"
- Fix: add kaamos environment refs + add lo-fi flash refs from winter + avoid "sunset".

"Camo becomes pixelated"
- Fix: provide higher-res M05 swatch close-ups and avoid the word "digital".

"PALS webbing is wobbly"
- Fix: add PALS close-up references; request 4K for that slide if available.

"Faces appear"
- Fix: provide anonymization refs; use shot types that crop head; specify anonymous mode.

---

If you want, share your current `assets/references/manifest.json` format and this guide can be tailored to your exact folder/role names.
