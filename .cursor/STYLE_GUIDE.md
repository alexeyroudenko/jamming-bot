# Design System & UI Style Guide (inspired by openspec.dev)

## 1. Общий стиль и философия
- **Тёмная тема только** (deep dark mode)
- Минималистичный modern tech aesthetic (похож на Vercel + Linear + shadcn/ui + terminal vibe)
- Максимальная читаемость кода и спецификаций
- Никаких лишних декоративных элементов — чистота и фокус на контенте
- "Spec-driven" ощущение: структурировано, точно, профессионально, но легко

## 2. Цветовая палитра (Tailwind + CSS variables)

**Backgrounds**
- `--background`: `#09090b` или `zinc-950`
- Surface / Cards: `#18181b` или `zinc-900`
- Subtle surface: `zinc-950/70`

**Text**
- Primary: `#ffffff` или `zinc-100`
- Secondary / Muted: `#a1a1aa` (`zinc-400`)

**Borders**
- Default: `#27272a` (`zinc-800`)

**Accent / Primary (главный акцент сайта)**
- Cyan / Sky: `#22d3ee` (`cyan-400`) или `#67e8f9`
- Hover: чуть ярче (`#67e8f9` → `#a5f4ff`)

**Дополнительно**
- Success: `emerald-500`
- Destructive: `red-500`

## 3. Типографика

- **Headings**: Inter / Satoshi / Geist Sans — `font-semibold` / `font-bold`, tracking-tight
- **Body**: Inter / system-ui sans-serif
- **Code / Monospace**: `ui-monospace`, `SF Mono`, `JetBrains Mono`, `Geist Mono`

**Размеры (Tailwind)**
- h1: `text-4xl` / `text-5xl` leading-none
- h2: `text-3xl`
- h3: `text-2xl`
- Body: `text-base` / `text-[15px]`
- Line-height: щедрый (1.6–1.8 для body)

## 4. Компоненты (примеры Tailwind / shadcn-style)

**Buttons**
```html
<!-- Primary -->
<button class="bg-cyan-400 hover:bg-cyan-300 text-black font-semibold px-6 py-3 rounded-xl transition-all">
<!-- Outline / Ghost -->
<button class="border border-zinc-700 hover:border-cyan-400 text-white px-6 py-3 rounded-xl transition-colors">