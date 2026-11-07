# Nexa AI — Theme Notes

## Theme Color Palette

- `nexa-bg` — `#020617`
- `nexa-panel` — `#07111F`
- `nexa-card` — `#0B1628`
- `nexa-cyan` — `#00E5FF`
- `nexa-blue` — `#2563EB`
- `nexa-purple` — `#8B5CF6`
- `nexa-green` — `#22C55E`
- `nexa-red` — `#EF4444`
- `nexa-text` — `#E6F1FF`
- `nexa-muted` — `#94A3B8`

## Design Style

- Futuristic cyberpunk / Jarvis-inspired interface
- Dark-first visual language
- Neon accents used as emphasis, not noise
- Structured panels with crisp spacing and restrained effects

## Glassmorphism Rules

- Use translucent dark surfaces over solid readable foundations
- Keep blur subtle enough for low-end laptops
- Preserve strong contrast between text and background
- Use glass treatment for containers, not every element

## Glow Rules

- Cyan glow for primary active states
- Purple glow for secondary emphasis
- Keep glow radius modest
- Avoid stacking multiple large glows on the same element

## Performance Rules

- Prefer lightweight gradients over heavy animated effects
- Avoid expensive visual filters in large repeated lists
- Keep decorative layers static unless motion adds meaning
- No heavy 3D treatment in MVP

## Accessibility Notes

- Maintain readable contrast for body text
- Do not rely on color alone to communicate state
- Preserve visible focus states
- Use neon accents sparingly so important signals remain distinct
