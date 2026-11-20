# Merchant art catalogue

Author: **Codex, created 13/11/2026**. Approval: **to be validated by chevre**.

All figures are **original creations in primitives**. Their inspiration is the
**private style reference supplied by chevre**, for Japanese anime chibi proportions,
large reflective eyes and smooth glossy toy material only. The reference character,
hat, hairstyle and cross motif are not reproduced. The reference image is not distributed.

The original drawings, sculpted models and visual designs are licensed under
**CC BY-NC-SA 4.0**, as specified in `LICENSE-CONTENT.txt` at the repository root.
The executable software follows the repository's **PolyForm Noncommercial 1.0.0**
license. The existing vendored three.js keeps its MIT license.

| Resource path and identifier | Original design | Author / date | Art license | Inspiration | Approval |
| --- | --- | --- | --- | --- | --- |
| `examples/board3d/art/merchants.js` / `human-man` | Swept dark hair, teal tunic, oat apron, parcel and satchel; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `human-woman` | Auburn coiled bun, rose tunic, cream apron and satchel; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `elf-man` | Pointed ears, swept silver crop, sage tunic and cream apron; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `elf-woman` | Pointed ears, gathered violet hair, saffron tunic and sea-glass apron; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `dwarf-man` | Broad body, copper hair and tied beard, ochre tunic and teal apron; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `dwarf-woman` | Broad body, twin coils and short braids, plum tunic, moss apron; no beard by default; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/merchants.js` / `dwarf-woman`, `{beard:true}` | Same dwarf woman with a small tied beard; original creation in primitives | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre | To be validated by chevre |
| `examples/board3d/art/gallery.html` | Seven-study shelf, labels and adjacent beard comparison | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 (visual design) | Original gallery composition; private style reference supplied by chevre for the figures | To be validated by chevre |
| `examples/board3d/art/gallery.css` | Paper, sage and ink presentation; system fonts | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 (visual design) | Original gallery composition | To be validated by chevre |
| `examples/board3d/art/gallery.js` | Enlarged and board-scale staging, board scene lighting and inspection angles | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 (visual staging); PolyForm Noncommercial 1.0.0 (software) | Existing board lighting; original gallery composition | To be validated by chevre |
| `examples/board3d/art/gallery-preview.png` | Browser-rendered contact sheet of the seven original primitive sculpts | Codex, created 13/11/2026 | CC BY-NC-SA 4.0 | Private style reference supplied by chevre for the figures; original gallery composition | To be validated by chevre |

## Integration contract

```js
import {MERCHANTS, makeMerchant} from "./art/merchants.js";
const figure = makeMerchant("elf-woman");
const alternative = makeMerchant("dwarf-woman", {beard:true});
```

- `MERCHANTS`: frozen array of six frozen `{id, people, gender, label}` records.
  `people` is `human`, `elf` or `dwarf`; `gender` is `male` or `female`.
- `makeMerchant(id, options = {})`: a fresh `THREE.Group`, front towards **+Z**,
  feet at **y = 0**, bounding-box centre at **x = z = 0**. Height **0.70**,
  maximum width and depth **0.42**, without a base. No player or seat inputs.
- `options.beard` is a boolean for `dwarf-woman` only, default `false`.
  The dwarf man always has a beard. Invalid ids or beard options throw explicitly.
- Every instance has independent meshes and transforms. Geometry and materials
  are pooled across all figures. Do not dispose or mutate shared geometry/materials
  when removing a single figure; clone a material before a local alteration.
- No model files, image textures, font downloads, canvas atlas, network calls,
  player state, animation loop, or game logic are needed by the sculpt module.

## Gallery route for the board launcher

Expected page: **`http://127.0.0.1:8879/art/gallery.html`**.

Add these static routes to the launcher without changing the art's imports:

| URL | Repository file |
| --- | --- |
| `/art/gallery.html` | `examples/board3d/art/gallery.html` |
| `/art/gallery.css` | `examples/board3d/art/gallery.css` |
| `/art/gallery.js` | `examples/board3d/art/gallery.js` |
| `/art/merchants.js` | `examples/board3d/art/merchants.js` |
| `/art/MANIFEST.md` | `examples/board3d/art/MANIFEST.md` |

The import `../../vendor/three/three.module.js` resolves to the launcher's existing
**`/vendor/three/three.module.js`** route. Serve JavaScript as `text/javascript`.
The launcher has not been changed by this art lot.

The gallery uses one WebGL context, renders on demand, and offers front,
three-quarter, back and board views. Both beard choices appear side by side.
The lower strip uses the board's 15:22 camera elevation at **88 CSS pixels per
world unit**, approximately the supplied board screenshot's scale. Actual apparent
size in the game depends on the board viewport. Each outline is a one-unit square;
it is gallery scenery and is not included in `makeMerchant`.

## Verification

Run `node --test tests/board3d-art.test.cjs` for the catalogue, exact dimensions,
grounding, facial/body features, beard choices, resource sharing and explicit errors.
The dimension test was checked against an intentional 0.71-height mutation and failed;
the sculpt was restored to 0.70. Chromium rendered all seven studies in all four views
at 1680 x 1000, and the horizontal shelf at 430 x 900, without runtime exceptions.
`gallery-preview.png` is the front-view capture. The art suite passes all five tests.
The initial full Node run passed 41 tests. After concurrent board work appeared,
the final run found 47 tests: 44 passed and three failed in `board3d-app.test.cjs`
(public route playback, fixture placement and motion settlement). Those failures
are outside this art lot; no board or game files were changed by this lot.
The Python suite was not run: no Python executable was available in the environment.
In-game integration and the launcher routes remain for the integrating maintainer.
`.preview-run/` is ignored local rendering scratch space and is not an art resource.
