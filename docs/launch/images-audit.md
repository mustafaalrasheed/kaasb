# Profile & Service Image Handling Audit

Opened 2026-04-25. User ask: *"enhance the profile image and the services and projects images."*

Scope: user avatars (`users.avatar_url`) + service images (`services.images[]`) — upload path, storage, and display.

---

## Verdict

**Safe but unoptimized.** Security posture is strong (magic-byte validation, path-traversal guard, size cap, extension whitelist). Visual + performance posture is weak: raw files are stored as-uploaded with no resizing, no format conversion, no thumbnails, and no CDN. A 5 MB phone photo is served 1:1 to every mobile client. On Iraqi cellular networks (3G common, spotty 4G) this is the single biggest perceived-perf drag on the platform.

---

## What is already right

- Upload pipeline validates content-type **and** magic bytes ([files.py:76-81](../../backend/app/utils/files.py#L76)) — can't smuggle an EXE named `.jpg`.
- Path-traversal filename check ([files.py:47-49](../../backend/app/utils/files.py#L47)).
- Size cap enforced **during read** (streaming) — no memory bomb from a claimed-huge upload.
- Extension whitelist (`jpg/jpeg/png/webp`) — SVG is correctly rejected (XSS vector).
- Old avatar files are cleaned up on re-upload ([files.py:94-95](../../backend/app/utils/files.py#L94)).
- Max 5 service images per listing ([files.py:105](../../backend/app/utils/files.py#L105)) — matches Fiverr's cap.
- Uploads live under `/uploads/avatars/` and `/uploads/gigs/` — served by FastAPI static mount.
- Chat attachments have a separate, broader whitelist (PDF + Office + zip) correctly kept separate from image validators.

---

## Findings

### P0 — Launch-visible performance hit

**F1. No server-side resizing.** A 5 MB iPhone photo uploaded as an avatar gets served at 5 MB to every page load that shows the navbar. Expected avatar size on screen is 32 px — the data delivered is ~3 orders of magnitude larger than needed. Same story for service images (card thumbnail = ~400 px, full view = ~1200 px; uploaded file is typically 4000×3000).

**Fix**: Pillow resizing at upload time. Store:
- Avatars: 200×200 (card) + 512×512 (profile header) + original
- Service images: 400×300 (card) + 1200×900 (detail) + original

Each tier stored as WebP (lossless-ish quality 85) falls back to JPG for older browsers. Naming: `{id}_{hex}_{size}.{ext}`.

Est: ~40 LoC add to `save_avatar` / `save_service_image`. Backfill existing files via a one-off script (safe to defer until backlog clears).

**F2. Frontend uses `<img>` not Next.js `<Image>`.** Raw `<img>` tags at [navbar.tsx:167](../../frontend/src/components/layout/navbar.tsx#L167) and elsewhere. No automatic `srcset`, no lazy-loading by default, no format negotiation. Next.js `<Image>` handles all three for free once `next.config.js` has the backend host in `images.remotePatterns`.

**Fix**: swap `<img src={backendUrl(...)}>` → `<Image src={...} width={...} height={...} />`. One file at a time, mechanical. Needs `remotePatterns` configured for `api.kaasb.com` (prod) + `localhost:8000` (dev).

### P1 — Real UX gaps

**F3. No drag-reorder of service images.** Freelancers upload images in whatever order they pick — first image becomes the card thumbnail. Currently the only way to change the thumbnail is to delete-and-reupload in the desired order. Fiverr allows drag-reorder of up to 3 images + 2 videos.

**Fix**: `PUT /services/{id}/images/reorder` taking an ordered list of image URLs. Frontend uses `@dnd-kit/sortable` (already in `package.json`? verify). Persist the new order to `services.images`.

**F4. No image alt-text input.** Accessibility + SEO: service images have no alt-text field; we fall back to the service title, which is OK but not great when there are 5 images of different subjects. Card surfaces also lack alts in some places.

**Fix**: `services.image_alts: list[str] | null` mirror column. Optional on upload.

**F5. No placeholder / default service image.** When a service has zero images, the card renders a blank grey box with the title overlay. Looks broken. Needs a category-derived placeholder (e.g. a simple gradient + the category's emoji/icon).

**F6. No image cropping UI.** Users must crop their photo before uploading. Avatars end up tall, oval-ish, or off-center because the UI just scales the raw file. A minimal `<input type=file>` → simple square-crop modal (react-easy-crop, 10 KB) would massively improve visual quality without any backend work.

### P2 — Polish

**F7. No CDN / cache headers on `/uploads/`.** FastAPI's `StaticFiles` serves without `Cache-Control: public, max-age=...`. Every page load re-fetches. Nginx reverse-proxy could add the headers, or we wire up Cloudflare free tier.

**F8. No EXIF stripping.** Phone photos carry GPS coordinates by default. Freelancers (and clients) may be unintentionally leaking their home location in avatar metadata. Pillow can strip on resize.

**F9. Avatar cache-busting uses `updated_at`.** Fine today, but if a user re-uploads within the same second, cache busting breaks. Use a short file hash (first 8 chars of sha256 of content, already computed via `uuid4().hex[:8]` in filename) instead.

**F10. No "portfolio images" entity for freelancers.** The user asked about "projects images." `User.portfolio_url` exists but is just one string URL (external link). There's no gallery upload for past work. Fiverr has a `portfolio` concept per seller with up to 30 images per package.

**Fix**: add `portfolio_items` table (freelancer_id, title, description, images[]), upload flow, and display on profile. Real feature; probably post-launch.

---

## Recommended sequence

If shipping one this week: **F1 (Pillow resize)** — biggest perceived-perf win per LoC; backfill script deferrable.

Next pass (~2-3 days): **F2 (Next/Image) + F5 (placeholder) + F8 (EXIF strip)**.

Polish pass: **F3 drag-reorder, F4 alt-text, F6 crop modal**.

Post-launch feature: **F10 portfolio gallery**.

F7 (CDN) is an ops change — land with Phase 2 on-server work.
