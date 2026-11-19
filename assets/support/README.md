# Coffee inspector

An original ImageGen sprite sheet, assembled with Pillow into a transparent 144 × 144 GIF. No stock artwork or borrowed character. The four-second loop contains 16 frames, a quick blink, small tail movements, steam and a rising heart. The first pose is also available as a PNG.

The profile uses only native GitHub Markdown/HTML. The PNG is selected by `prefers-reduced-motion` in a `picture` element, and a visible still-image link remains available. GitHub controls page typography, spacing and keyboard focus; no custom CSS or JavaScript is added.

## Art and button tokens

- Graphite: `#202127`; ink: `#F1EEFA`; violet: `#A78BFA`; amber: `#EAB66C`.
- Native README body and heading typography; image-button labels use 12px Verdana.
- Buttons: 40px high, 4px corner radius; 144px Star and 164px Sponsors. Inline links wrap naturally at narrow widths.
- Cat: 144px square, a shared 95-color palette plus transparency, 4,000ms loop. No flashing.

## Regenerate

Install Pillow and run `python scripts/gen_support_cat.py` from the repository root. The original sheet is retained for repeatable assembly. The script crops registered cells, reduces them by an integer factor, applies one shared GIF palette, and verifies the frame count, loop flag and duration.

## Support destinations

Verified on 2026-10-17:

- Star: https://github.com/MadB0i/MadB0i — live repository; visitors use GitHub's Star control.
- GitHub Sponsors: https://github.com/sponsors/MadB0i — HTTP 200; GitHub GraphQL reports `hasSponsorsListing: true` and `sponsorsListing.isPublic: true`.
- Buy Me a Coffee: no verified URL found in the local/remote README, repository funding links, public social accounts or Sponsors description. No donation destination has been guessed. Create or supply your actual creator-page URL, verify its ownership and public availability, then add an amber image-button link next to the existing two. The README currently shows plain text explaining that this option is pending.

The repository's effective `fundingLinks` list was empty. Sponsors is nevertheless public and usable. Adding `github: [MadB0i]` to `.github/FUNDING.yml` is an optional later step to enable GitHub's repository Sponsor control.

All existing remote image origins returned HTTP 200 with image content. The original profile-view counter initially failed through GitHub's Camo image proxy (404/503), then recovered to HTTP 200 on recheck. It was retained to preserve the existing count. The failure was intermittent; no service uptime guarantee is implied. Two alternatives were tested successfully through Camo, but would start separate counters, so no migration was made.

## ImageGen prompt

Built-in ImageGen was used with a transparent background. Final prompt:

> Use case: illustration-story.
> Asset type: ORIGINAL pixel-art animation sprite sheet for a compact professional GitHub README.
> Create one square transparent PNG sprite sheet arranged in an EXACT 4 by 4 grid, sixteen equal square cells, NO gutter, NO cell borders, NO labels, NO text. Every cell contains the SAME exceptionally charming tiny midnight-graphite cat holding a small warm amber ceramic coffee mug with BOTH paws. Original designed pixel art, deliberate stair-step edges and limited palette, no painterly smears, no stickers, no logos, no copyright characters.
> Character: seated little dark charcoal cat, oversized softly squared head, small triangular ears with muted violet inside, two bright warm cream eyes with a tiny highlight, tiny amber nose, subtle cream muzzle, lavender neckerchief, short rounded seated body, two feet, long curved tail extending on the cat's right. All silhouettes have a soft violet outer edge so readable on both white and midnight backgrounds. Little coffee mug amber with dark coffee and tiny violet paw mark. Under cat a tiny flat violet oval grounding shadow. No background scene, no large surrounding empty space.
> CRITICAL exact registration: cat head, body, paws and mug at IDENTICAL position and IDENTICAL scale in all 16 cells, full cat and tail remain completely inside each cell. Character fills roughly 72% cell width and 76% height. Top area reserved for puff. Camera stationary. ONLY tail tip, eyelids and mug steam change.
> Read frames left to right, then top to bottom. Across all 16 frames tail slowly swings through one smooth complete cycle and returns, subtle breathing only if exact registration maintained. Frames 1-6 eyes open. Frame 7 eyelids half closed. Frame 8 eyes closed in sweet curved lines. Frame 9 eyelids half closed. Frames 10-16 eyes open. One tiny violet steam curl above mug grows through frames 2-5 and disappears. One small amber heart rises above mug through frames 11-15 and disappears in frame 16. First and last poses near identical for seamless four-second looping. Handmade-looking crisp pixel grid, cozy restrained personality; no enormous sparkles, no gradients, no text. Transparent background throughout.
