# v19 independent parts: geometry and seam-safe sampling

The model uses seven ordered PSD-derived textures and six independent geometry arrays: rear hair (`head`), legs (`root`), skirt, torso clothing, screen-left arm, screen-right arm, and front head (`head`). Each texture has its own WebGL position buffer and draw call. Arm inputs never enter torso or skirt geometry. Skirt inputs never enter torso, arm, or head geometry. The root stays fixed; the skirt waist stays fixed and its small hem displacement follows a delayed spring. The approved underlying artwork limits horizontal skirt displacement to **three source pixels**.

The separate surfaces are transformed **before** compositing. There is no shared full-body deformation after the parts are assembled. The old arm-weight dilation has been removed. Ambient hair motion belongs only to the head/hair geometry, not torso clothing.

## Why the renderer resolves once

Filtering two neighboring cut textures independently can produce half-alpha samples on both sides of a perfectly joined seam. Ordinary source-over blending then produces 0.75 alpha, not 1.0. This can make an internal cut visible against a dark or light background even when the unfiltered source composite is exact.

`bodySampling: "coverage-2x"` samples **all** part textures coherently with NEAREST filtering into one premultiplied RGBA framebuffer at twice the output width and height. The parts still have independent geometry and separate draw calls. The complete assembled avatar is then downsampled once with LINEAR filtering. Mixing a separately LINEAR-filtered face into the coverage pass would reintroduce the seam problem, so the same sampling rule applies to every final part, including front and rear hair.

Source images, accepted expression records, the face canvas, and the v17 mouth-deformation helper are unchanged. This fixes sampling coverage; it does not invent pixels behind a moving garment or justify a larger skirt range. It does not force silhouette alpha, dilate the silhouette, blur the face, or reintroduce shared limb weights.

## Device limits

The requested 2× framebuffer is capped by `MAX_TEXTURE_SIZE`, `MAX_RENDERBUFFER_SIZE`, and `MAX_VIEWPORT_DIMS`. A limited device can receive a smaller coherent sampling surface, which can reduce edge quality. The actual dimensions and scale are available as `renderer.sampling`. An incomplete framebuffer is an explicit load error; the renderer does not silently revert to the known seam-prone per-part LINEAR path. Browser GPU/device performance and GUI E2E were not exercised for this milestone.

The offline OpenGL path imports the same crop-coordinate helper and uses the same independent role positions, premultiplied source-over blend, and coverage resolve. Its neutral prototype reduced the opaque-reference seam deficit from 1,544 pixels (maximum loss 114 alpha levels) to zero at the tested 900×1200 output. This is an offline rendering result, not a browser capture.

## Rebuild and verify

The art builder owns `assets/parts/v19/model-body-v19.json` and the cropped PNGs. After rebuilding art, integrate the coherent fragment with:

```bash
python scripts/integrate_body_v19.py --sampling coverage-2x
python scripts/integrate_body_v19.py --check --sampling coverage-2x
node --test runtime/tests/*.test.js
python -m unittest discover -s tests -p test_runtime_server.py
```

The integration script validates all crop dimensions, six render roles, eight head variants, the hem limit, and unchanged legacy face/model declarations. It does not edit artwork. `--check` rejects a stale manifest if the exported crops or rectangles changed.

For deterministic isolated render checks, use `renderer.render(pose, time, expression, {ambient:false})`. `onlyRoles:["torso"]` renders the actual torso pass alone; it is a diagnostic filter, not a different geometry implementation. `rig.frames(pose,time,{ambient:false})` returns all six full-grid source-coordinate surfaces. `rig.frame(...)` remains the torso-only return for older callers; it must not be used as a full-avatar warp.
