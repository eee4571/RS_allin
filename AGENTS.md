# RS_allin Repository Instructions

RS_allin is a modular remote-sensing desktop platform.

For platform UI changes, architecture work, module development, module integration, shared project/layer/task infrastructure, and refactors, use the repository skill:

```text
.agents/skills/rs-allin-platform-development/SKILL.md
```

The primary architecture requirement is:

> Platform UI and business modules must evolve independently through stable Platform Contracts.

Before editing, read the actual relevant implementation and inspect the current diff. Do not rely on generic assumptions or older repository structure.

Preserve user changes and avoid unrelated edits.

For business modules, do not introduce direct dependencies on `MainWindow` or platform presentation widgets.

For platform UI, do not introduce direct dependencies on concrete business-module implementations.

Run focused tests appropriate to the changed responsibility boundary.
