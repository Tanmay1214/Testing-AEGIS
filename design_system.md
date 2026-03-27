# Design System Specification: High-Contrast Retro-Futurism

**Creative North Star: "The Obsidian Architect"**

This design system is not a mere "dark mode" theme; it is a digital manifest of 1980s high-end terminal hardware. It rejects the soft, approachable "SaaS-blue" aesthetics of the modern web in favor of a rigid, authoritative, and immersive command-line experience.

## Colors & Surface Philosophy
The palette is rooted in absolute contrast. We utilize a "Pitch Black" foundation to ensure the Electric Cyan and Neon Magenta "emit light" rather than just sitting on a page.

### Color Tokens
*   **Surface (Pitch Black):** `#050505`
*   **Primary (Electric Cyan):** `#00ffff`
*   **Secondary (Neon Magenta):** `#ff00ff`
*   **Neutral/Outline:** `outline-variant` at 20% opacity.

## Typography
Monospace system (**Space Grotesk**).
*   **Display-LG (3.5rem):** Uppercase, `letter-spacing: -0.05em`.
*   **Headline-SM (1.5rem):** Pair with a `secondary` (Magenta) highlight character.
*   **Body-MD (0.875rem):** Line-height 1.6.

## Components
### Buttons
*   **Primary:** No background fill. `0px` radius. `1px` border using `primary` (Cyan) with a `box-shadow: 0 0 8px #00ffff`.
*   **Secondary:** Magenta text, scanline-patterned background fill on hover.

### Progress Bars
*   **Style:** Segmented blocks instead of smooth fill. Use `secondary` (Magenta) for fill blocks.

## Do’s and Don’ts
*   **DO** use intentional asymmetry.
*   **DO** use 0px roundedness for everything.
*   **DON’T** use standard "drop shadows."
*   **DON’T** use "Border Radius."
