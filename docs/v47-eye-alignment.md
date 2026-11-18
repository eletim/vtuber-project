# v47 eye alignment correction — review candidate

The previous v46 acceptance is withdrawn. Native neutral open crop equality did not validate the authored closed positions or expression-specific intermediate rendering.

## Reproduced causes
- v46 closure paths were approximately 10–20 model pixels above the native closed lashes. This changed the face at frame 22/23, although the fully open source crop was exact.
- The compositor shared neutral closed reference/skin/aperture with other expressions. Bashful frames 237 and 247 exposed neutral-colour bands and duplicate blush/lower contours.
- Expression defaults multiplied an already half-open authored drawing a second time.
- Open and closed PNGs have different model rectangles. A canonical canvas confined to the open rectangle clipped the larger closed source. Compositing a full base under the native transparent patch also changed its edge alpha.
- The iris ownership ellipse omitted peripheral native pixels when gaze moved. Its coverage and per-expression center were corrected. White sclera revealed below an upward-looking iris is expected; fine rim quality still needs independent visual review.

## Implementation
- Union canvas of the native open/closed rectangles, retaining their model coordinate offsets and transparent padding. No head transform is added to either eye.
- Native per-expression open and closed pixels are used independently. Endpoints are exact. Curves are registered to each expression's native closed lash, not the neutral eye.
- Intermediate lids use registered open/closed skin and lash sampling with premultiplied-alpha interpolation. The iris is translated at native size and clipped by the aperture; it is not vertically scaled for blinking.
- Normalize the expression cap once, so a half-eye drawing is its own maximum opening. `big_smile` retains its original closed smile eyes.
- Head remains rigid 2D roll. Body/hair/arm/waist/gesture code is unchanged. Shoulder image generation was not attempted.

## Validation
- `audit/report.json`: normal renderer vs v45, same input, pose, expression and 480x420 native face camera; 8 expressions x 5 openings. All 16 fully-open/closed endpoints have pixel max difference 0. This does NOT certify intermediate frames by itself.
- Native intermediate face images, gaze crops, and the 30fps comparison sequence are retained. Regression focus: frames 22/23, 237, 247 and 315.
- `review/report.json`: v46 vs v47 under identical input, 360 frames, 30fps CFR. The v46 renderer, compositor and profile JSON are routed from the saved v46 commit rather than accidentally sharing the candidate compositor.
- `ui-review/report.json`: 2 independent browser contexts, gaze/mouth priority, all 8 expressions, reconnect and normal-speed playback measurement.
- `final-tests.json`: full JavaScript suite plus runtime Python suite. Legacy full discovery exclusions remain as documented in v46 (missing SciPy; unchanged CRLF hash fixture); no installation was performed.
- PSD source groups include all native expression endpoint patches at their actual model coordinates. Hidden source groups preserve the accepted merged preview exactly; runtime procedural interpolation is described by code, not baked into the merged PSD image.

## Limits
This is a corrected candidate, not independent final acceptance. At enlarged scale the original hair/lash intersection remains rough. The headless playback measurement does not guarantee smooth performance on every display. Source shoulder cut edges remain outside this eye-only correction.
