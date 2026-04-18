# Avatar Overlay Viseme Mapping Design

## Goal

Refactor the frontend avatar renderer so the head remains static while Rhubarb visemes swap only the transparent mouth overlay, with preloaded assets and stable alignment.

## Current State

- `frontend/index.html` swaps a single full-frame mouth image.
- The current mapping relies on a fallback map and does not explicitly model the updated `base-head.png` plus mouth overlay composition.
- Asset names in `frontend/mouths/` now use `B.png` through `H.png`, `X.png`, and `base-head.png`, with `A` intentionally reusing `X.png`.

## Design

### Viseme map

Use the frontend map below:

- `X -> ./mouths/X.png`
- `A -> ./mouths/X.png`
- `B -> ./mouths/B.png`
- `C -> ./mouths/C.png`
- `D -> ./mouths/D.png`
- `E -> ./mouths/E.png`
- `F -> ./mouths/F.png`
- `G -> ./mouths/G.png`
- `H -> ./mouths/H.png`

### Renderer structure

Render the avatar as one fixed-size stage containing:

- a constant `base-head.png`
- a transparent mouth overlay image positioned absolutely on top

Both layers must share the exact same dimensions and positioning so only the overlay changes during playback.

### Playback behavior

- Idle state uses `base-head.png + X.png`.
- During playback, the overlay updates to the viseme mapped from the active Rhubarb cue.
- On cue gaps, audio end, or stopped playback, reset to `X`.

### Asset preload

Preload the base head plus every distinct mouth image before interactive playback to avoid first-swap flicker.

### Transition

Apply a short opacity transition to the overlay only, keeping the duration short enough to avoid lagging Rhubarb timing.

## Validation

- The overlay stays visually locked to the base head.
- `A` and `X` both use `X.png`.
- No mouth image flashes blank on first playback.
- Idle state looks natural with `X.png` over `base-head.png`.
