---

name: rs-allin-platform-development
description: Use for RS_allin platform UI changes, architecture changes, module integration, plugin development, shared project/layer/task infrastructure, and refactors. Preserve strict independence between the platform shell and independently evolving business modules. Main UI and module internals must be able to change independently through stable platform contracts.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# RS_allin Platform Development

RS_allin is a modular remote-sensing desktop platform.

The primary architectural objective is **independent evolution**:

* the main application UI must be freely redesignable without requiring changes inside road, building, change-detection, or future business modules;
* each business module must be freely refactorable, extended, or replaced without requiring corresponding changes to the main application UI;
* integration must occur through a small, stable Platform API rather than direct references to concrete UI widgets, module classes, or algorithm implementations.

The repository structure, module APIs, and implementation details may evolve. Preserve the responsibility boundaries and communication contracts described below rather than preserving an obsolete implementation.

# 1. Start from the actual repository

Before modifying code:

1. Read the latest relevant repository files rather than reasoning from generic PySide6 patterns or historical assumptions.
2. Inspect `git status`, existing diffs, and user changes before editing.
3. Read only the files needed for the requested task and their direct dependencies.
4. Treat existing user changes as user work. Do not overwrite or revert unrelated modifications.
5. Prefer the current repository implementation over assumptions from previous versions.

For a platform-UI-only request, normally inspect:

* `main.py`;
* `main_window.py`;
* relevant files under `widgets/`;
* relevant files under `styles/`;
* the stable contracts used by those widgets.

Do not read or modify individual algorithm implementations merely because the UI displays their status.

For a module-only request, normally inspect:

* `modules/<module>/`;
* relevant stable contracts in `core/`;
* direct tests.

Do not modify the platform layout merely because a module workflow changed.

# 2. Repository responsibility boundaries

Treat the repository as four conceptual layers.

```text
┌─────────────────────────────────────┐
│  Platform Presentation / Shell      │
│  main_window.py / widgets / styles  │
└────────────────┬────────────────────┘
                 │
                 │ Stable Platform API
                 ▼
┌─────────────────────────────────────┐
│  Platform Core / Contracts          │
│  Command / Task / Event / Layer     │
│  Result / Project / Module API      │
└────────────────┬────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌──────────────┐    ┌──────────────┐
│ Road Module  │    │ Other Module │
│ internal     │    │ internal     │
└──────────────┘    └──────────────┘
```

The dependency direction is:

```text
Platform UI
    ↓
Platform Core Contracts
    ↑
Business Modules
```

The platform UI and business modules are siblings connected through the core contracts.

They must not depend directly on each other's implementation.

# 3. Platform shell responsibilities

The platform shell owns application-wide presentation and interaction.

Typical platform-owned files include:

```text
main.py
main_window.py
widgets/
styles/
```

The platform shell may own:

* main-window layout;
* menu bar;
* Ribbon or toolbar presentation;
* project tree presentation;
* map workspace presentation;
* global timeline presentation;
* log and task presentation;
* dock/splitter/layout behavior;
* global shortcuts;
* global status bar;
* global visual style and QSS;
* deciding where a module capability appears in the UI;
* translating generic user actions into platform Commands;
* displaying generic Events, Tasks, Results and Layers.

The platform shell must NOT:

* import concrete algorithm classes;
* call road/building/change functions directly;
* know internal algorithm steps unless they are exposed through a generic contract;
* inspect module-private files or data structures;
* contain branches such as `if module_id == "road"` for ordinary business behavior;
* pass concrete Qt widgets into modules;
* give modules direct references to `MainWindow`, project-tree widgets, log widgets, progress bars, or map widgets.

Changing the main-window layout must normally require changes only in the platform presentation layer.

# 4. Platform Core responsibilities

`core/` defines the stable communication boundary.

The core layer owns generic concepts such as:

* `Command`;
* `Task`;
* task state;
* platform Events;
* `Result`;
* `Layer`;
* `ProjectContext` / project model;
* module registration;
* module capability discovery;
* API compatibility;
* command routing;
* event routing;
* shared layer management.

Core types must remain domain-neutral whenever practical.

Avoid fields that exist only because one specific business module needs them.

For example, prefer:

```text
Task
- task_id
- module_id
- operation
- context
- parameters
- state
- progress
- outputs
- error
```

over putting road-specific concepts directly into a generic Task model.

Module-specific values belong in typed metadata, payloads, module-owned models, or extension fields.

# 5. Stable integration contracts

The following concepts form the primary integration contract.

## Command

Represents what the user/platform requests a module to do.

The platform may create a Command.

The module receives and interprets it.

The UI must not directly invoke algorithm implementations.

## Task

Represents one running or completed operation.

Task state should support generic platform features such as:

* queued;
* running;
* completed;
* failed;
* cancelled;
* progress;
* output registration.

A task is platform-visible but algorithm implementation details remain module-owned.

## Event

Modules report state through events.

Examples include:

* task started;
* progress changed;
* log emitted;
* task completed;
* task failed;
* result available;
* layer added or updated;
* selection changed.

A module must publish events rather than manipulate UI widgets.

## Result

Represents a business output produced by a module.

The platform may register, display, browse, or persist the result without knowing how it was calculated.

## Layer

Represents something displayable in the shared GIS/map workspace.

Raster imagery, validation polygons, road centerlines, road surfaces, buildings, road changes, building changes and future spatial outputs should use the shared layer abstraction when they enter the platform workspace.

Modules must not directly manipulate the platform map widget.

## Project Context

Represents platform-wide project information needed by modules.

Typical concepts include:

* project identity;
* project root;
* areas;
* periods;
* active area;
* active period;
* configured data sources;
* registered layers;
* registered results.

Do not put Qt widgets or module implementation objects in ProjectContext.

## Module API

Defines what capabilities a business module exposes to the platform.

A module describes **what it can do**.

The main UI decides **how and where that capability is presented**.

# 6. Capability is not UI layout

This distinction is mandatory.

Business modules may declare capabilities such as:

```text
road.extract
road.change
road.timeseries
road.manual_edit
road.evaluate
```

But a module must not determine that a capability must appear in:

* a Ribbon;
* a toolbar;
* the right panel;
* a particular page;
* a specific button position.

The platform shell owns presentation.

A future redesign may move the same capability from:

```text
Ribbon
```

to:

```text
menu / toolbar / page / context action
```

without modifying the business module.

Do not create architecture where `Plugin.workflows()` directly dictates the complete main-window layout.

Description-driven generic UI is acceptable as one presentation strategy, but it must remain a platform choice rather than a module-to-UI dependency.

# 7. Business module responsibilities

Each business module owns its own functionality.

Typical structure:

```text
modules/
  road/
  building_extract/
  building_change/
  future_module/
```

A module may own:

* workflow semantics;
* module-specific parameters;
* validation rules;
* backend adapters;
* subprocess management;
* algorithm orchestration;
* mapping between module backend events and Platform Events;
* module-specific data models;
* module-specific tools;
* module-specific result interpretation;
* module-specific tests.

A module must NOT:

* import `MainWindow`;
* import platform presentation widgets to manipulate them;
* call `map_view` directly;
* append text directly to platform log widgets;
* set a platform progress bar directly;
* alter Ribbon structure directly;
* depend on the physical position of any main-window widget.

# 8. Module-specific UI

Some capabilities require specialized UI, such as:

* road centerline manual editing;
* node editing;
* snapping;
* geometry inspection;
* specialized quality-control tools.

Such UI may live inside the owning module, for example:

```text
modules/road/ui/
```

Module-specific UI owns its internal layout and interaction.

The platform should open it through a generic capability/tool contract, for example conceptually:

```text
open_module_tool("road", "manual_editor")
```

The platform must not know the editor's internal widgets.

The module-specific editor must not manipulate unrelated platform widgets directly.

Data exchanged with the platform should use Project, Layer, Result, Selection and Event contracts.

# 9. Forbidden coupling patterns

Do not introduce patterns like:

```python
road_plugin.set_main_window(main_window)
road_plugin.set_progress_bar(progress)
road_plugin.set_map_widget(map_view)
road_plugin.set_log_widget(log_panel)
```

Do not introduce direct platform calls such as:

```python
road.run_period(...)
building.start_extract(...)
map_view.add_road_result(...)
```

Do not use UI-specific callbacks as the primary business integration mechanism when a generic Event or Command can represent the interaction.

Avoid growing code such as:

```python
if module_id == "road":
    ...
elif module_id == "building":
    ...
elif module_id == "building_change":
    ...
```

inside generic platform components.

When module-specific behavior is genuinely necessary, first determine whether it belongs in:

* the module;
* a capability descriptor;
* a generic extension point;
* a module-specific view.

# 10. UI-change isolation rule

When the requested task is a main-UI redesign:

Prefer changing only:

```text
main_window.py
widgets/
styles/
```

and, only when necessary, generic presentation-facing contracts.

Do not modify business-module internals just to accommodate a different layout.

Examples that should not require module changes:

* moving logs from bottom to right;
* replacing docks with splitters;
* redesigning Ribbon;
* changing toolbar structure;
* changing panel sizes;
* redesigning the project tree;
* adding a timeline;
* changing QSS;
* replacing one generic progress presentation with another.

# 11. Module-change isolation rule

When changing a business module:

Prefer changing only:

```text
modules/<module>/
```

and generic contracts only when a genuinely reusable platform capability is missing.

Examples that should normally not require platform UI changes:

* changing a road extraction algorithm;
* adding preprocessing steps;
* replacing a backend implementation;
* changing road width measurement;
* changing change-detection internals;
* adding checkpoint/resume behavior;
* changing subprocess execution;
* adding module-specific validation.

The module should continue to express state and output through stable Platform Events and Results.

# 12. Adding a new module

Adding a new module should not require editing `MainWindow` for normal capability discovery.

A new module should:

1. implement the supported Module API;
2. register or expose capabilities;
3. accept generic Commands;
4. publish generic Events;
5. produce Results and Layers through the platform contracts.

The platform decides how to present the new capabilities.

Do not add a new `elif module_id == ...` branch throughout the shell.

# 13. Contract evolution

Stable does not mean frozen forever.

When a core contract is insufficient:

1. determine whether the requirement is genuinely cross-module;
2. prefer extending a generic contract rather than exposing a concrete implementation;
3. maintain compatibility where reasonable;
4. update direct consumers consistently;
5. add focused contract tests.

Do not add a generic core field solely to avoid writing module-owned code.

# 14. Current RS_allin migration principle

The current repository is an architectural prototype.

Do not preserve prototype behavior merely because it exists.

In particular, description-driven workflow generation, Mock adapters, current Ribbon structure, current Dock layout and current project models may be refactored when they obstruct independent platform/module evolution.

Preserve the useful existing ideas:

* module registry;
* command routing;
* event routing;
* module discovery;
* API-version validation;
* layer management;
* no direct concrete-module imports in the main shell.

Refactor implementation details when necessary.

# 15. Architecture test requirements

Maintain focused tests that protect dependency direction.

Tests should detect at least:

* platform shell importing concrete business modules;
* modules importing `main_window` or platform presentation widgets;
* module registration/discovery failure;
* incompatible module API versions;
* generic command routing failure;
* generic event delivery failure.

Where practical, add a smoke test proving that a module implementation can be replaced without changing the shell.

# 16. Before completing a task

Before finalizing changes:

1. inspect the final diff;
2. verify no unintended cross-layer imports were introduced;
3. run focused tests;
4. confirm whether the change affected:

   * Platform UI only;
   * Platform Core;
   * one business module;
   * public Platform Contracts.
5. explicitly report any contract changes.

For architecture work, prefer a clear responsibility boundary over a locally convenient shortcut.

The success criterion is:

> Main UI changes and business-module changes remain largely independent, with integration performed through stable, generic and testable Platform Contracts.
