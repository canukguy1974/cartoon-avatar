# Avatar Overlay Viseme Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the frontend avatar renderer to keep `base-head.png` fixed while mouth overlays swap according to Rhubarb visemes with preloaded assets and stable alignment.

**Architecture:** Keep the implementation inside `frontend/index.html`, replace the single mouth-frame renderer with a layered stage, add an explicit `visemeMap`, preload all required images on init, and reset the overlay to `X` outside active speech.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript

---

### Task 1: Add a failing regression test for the renderer contract

**Files:**
- Create: `backend/tests/test_frontend_avatar_markup.py`
- Test: `backend/tests/test_frontend_avatar_markup.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from unittest import TestCase


class FrontendAvatarMarkupTests(TestCase):
    def test_frontend_uses_overlay_renderer_and_explicit_viseme_map(self) -> None:
        html = Path("frontend/index.html").read_text()

        self.assertIn('id="baseHead"', html)
        self.assertIn('id="mouthOverlay"', html)
        self.assertIn('const visemeMap = {', html)
        self.assertIn('A: "./mouths/X.png"', html)
        self.assertIn('preloadImages()', html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/canuk/projects/sunny-local && backend/.venv/bin/python -m unittest backend.tests.test_frontend_avatar_markup -v`
Expected: FAIL because the current markup still uses a single `mouthFrame` image and no explicit preload function.

- [ ] **Step 3: Write minimal implementation**

```html
<img id="baseHead" src="./mouths/base-head.png" alt="Sunny base head" />
<img id="mouthOverlay" src="./mouths/X.png" alt="Sunny mouth overlay" />
```

```js
const visemeMap = {
  X: "./mouths/X.png",
  A: "./mouths/X.png",
  B: "./mouths/B.png",
  C: "./mouths/C.png",
  D: "./mouths/D.png",
  E: "./mouths/E.png",
  F: "./mouths/F.png",
  G: "./mouths/G.png",
  H: "./mouths/H.png"
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/canuk/projects/sunny-local && backend/.venv/bin/python -m unittest backend.tests.test_frontend_avatar_markup -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_frontend_avatar_markup.py frontend/index.html
git commit -m "test: cover overlay avatar renderer contract"
```

### Task 2: Refactor the frontend renderer

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Replace the single image renderer with a layered stage**

```html
<div class="avatar-stage">
  <img id="baseHead" src="./mouths/base-head.png" alt="Sunny base head" />
  <img id="mouthOverlay" src="./mouths/X.png" alt="Sunny mouth overlay" />
</div>
```

- [ ] **Step 2: Add preload and overlay update logic**

```js
async function preloadImages() {
  await Promise.all(
    [...new Set(["./mouths/base-head.png", ...Object.values(visemeMap)])].map(
      source =>
        new Promise((resolve, reject) => {
          const image = new Image();
          image.onload = resolve;
          image.onerror = reject;
          image.src = source;
        })
    )
  );
}
```

- [ ] **Step 3: Keep idle and ended playback on `X`**

```js
function setMouth(viseme) {
  mouthOverlay.src = visemeMap[viseme] || visemeMap.X;
}
```

- [ ] **Step 4: Run the regression test**

Run: `cd /home/canuk/projects/sunny-local && backend/.venv/bin/python -m unittest backend.tests.test_frontend_avatar_markup -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/index.html backend/tests/test_frontend_avatar_markup.py
git commit -m "feat: add overlay-based viseme renderer"
```
