# Master Roadmap: All Requested Features

## Overview

Comprehensive plan covering all features requested:
1. Gradient ball-of-light indicator
2. Grammar post-processing with multiple modes
3. Auto-off on focus change
4. Unit tests (core logic + desktop app)
5. UI component library for Tauri app

## Status

- [ ] Indicator gradient (researching)
- [ ] Grammar post-processing modes (designing)
- [ ] Auto-off focus detection (researching)
- [ ] Additional text fixer modes (brainstorming)
- [ ] Unit tests
- [ ] UI component library

## Brainstorming: Additional Text Fixer Modes

Current planned modes:
1. **Light**: FullStop punctuation only (<1s)
2. **Aggressive**: FullStop + Qwen grammar (~2-3s)
3. **Agentic**: 2-3 cycle LLM loop for extensive expansion
4. **Writing**: Style-focused for prose
5. **Code**: Syntax-aware for code blocks

Need 3 additional creative modes that would help with:
- Agentic engineering workflows
- Voice input convenience
- Writing/editing workflows

## Next Steps

1. Complete research for gradient indicator (bg_baf24bb3)
2. Complete research for X11 focus detection (bg_101f6f92)
3. Complete research for Tauri UI patterns (bg_4ecab9b9)
4. Brainstorm 3 additional modes with user
5. Design master architecture
6. Create implementation plans
