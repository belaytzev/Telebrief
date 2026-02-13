# Update Website to Reflect Multi-Provider AI and Configurable Language

Update the Telebrief landing page to accurately reflect current capabilities: multi-provider AI support (OpenAI, Anthropic, Ollama), configurable output language, and free local AI option via Ollama.

## Context

- Files involved: `website/src/pages/index.astro`
- Related patterns: Existing Astro component structure, skeuomorphic design system
- Dependencies: None (content-only changes)

## Approach

- **Testing approach**: Manual (verify website builds and renders correctly)
- Single file modification - all changes are in `index.astro`
- Content updates only, no structural/layout changes needed

## Task 1: Update Hero Section Stats

**Files:**
- Modify: `website/src/pages/index.astro`

**Steps:**
- [x] Change hero stat from `GPT-5-nano` / `Powered` to `3 AI Providers` / `Supported` (or similar) to reflect OpenAI, Anthropic, Ollama support
- [x] Update cost stat from `~$0.30` / `Per Month` to `Free - $0.30` / `Per Month` to reflect that Ollama is free
- [x] Run `cd website && npm run build` - must pass before task 2

## Task 2: Update Feature Cards

**Files:**
- Modify: `website/src/pages/index.astro`

**Steps:**
- [x] Update "AI-Powered Summaries" card: change "Advanced GPT-5-nano technology generates concise, intelligent summaries of your Telegram channels in Russian" to mention multi-provider AI (OpenAI, Anthropic, Ollama) and configurable output language
- [x] Update "Multi-Language Support" card: change "Summaries are always in Russian" to "Output language is fully configurable" (or similar)
- [x] Update "Ultra Affordable" card: change "Runs on GPT-5-nano for just ~$0.30 per month" to mention free option with Ollama and paid cloud options
- [x] Run `cd website && npm run build` - must pass before task 3

## Task 3: Update How It Works Section

**Files:**
- Modify: `website/src/pages/index.astro`

**Steps:**
- [x] Update step 2 "AI Summarization" description: change "GPT-5-nano analyzes and generates intelligent summaries" to reference the user's chosen AI provider instead of a specific model
- [x] Run `cd website && npm run build` - must pass

## Verification

- [ ] Run full build: `cd website && npm run build`
- [ ] Manual review: verify no mention of "GPT-5-nano" remains as the sole AI option
- [ ] Manual review: verify "Russian" is not described as the only output language
- [ ] Manual review: verify Ollama/local AI is mentioned as a provider option

## Cleanup

- [ ] Move this plan to `docs/plans/completed/`
