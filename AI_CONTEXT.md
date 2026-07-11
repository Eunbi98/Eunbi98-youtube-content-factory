# AI_CONTEXT.md

# Project

youtube-content-factory

Goal

Build an AI Content Factory capable of automatically producing high-quality YouTube Shorts.

This project is designed as a reusable content engine, not as a single YouTube automation script.

------------------------------------------------------------

# Development Philosophy

Core never knows genres.

Plugins know genres.

Renderer never knows stories.

New channels should be created by adding Plugins instead of modifying Core.

Always prioritize reusable architecture over quick implementation.

------------------------------------------------------------

# Current Architecture

Story

↓

Story Compiler

↓

Scene

↓

Director

↓

Timeline

↓

Remotion Renderer

↓

MP4

------------------------------------------------------------

# Current Version

v5.0 Factory Core

------------------------------------------------------------

# Completed

Release 1

✔ News Collector

Release 2

✔ Story Engine

Release 3

✔ Remotion Engine

Release 4

✔ Master Template

✔ SafeFrame

✔ Theme

✔ Overlay

✔ Ken Burns

✔ Transition

✔ MP4 Render Verified

Release 5

✔ Director Rule Engine

✔ Story Graph

✔ Story Compiler

✔ Timeline Builder

✔ timeline.json generation

------------------------------------------------------------

# Current Patch

Patch 5-3

Duration Planner

Goal

Remove duration from Story Beat.

Scene duration should be calculated automatically from narration length.

Duration calculation should consider

- narration length

- scene type

- minimum duration

- maximum duration

------------------------------------------------------------

# Next Patch

Patch 5-4

Timeline Scheduler

Goal

Remove Scene start.

Automatically calculate Scene start based on previous Scene duration.

------------------------------------------------------------

Patch 5-5

Factory Core

Goal

Story

↓

Timeline

automatically.

------------------------------------------------------------

# Future

v6

Mystery Plugin

Generate one complete Shorts automatically.

v7

Quiz Plugin

Same Core.

Only new Plugin.

v8

Publisher

YouTube Upload

v9

Web UI

v10

Learning Engine

Use YouTube analytics to improve future content.

------------------------------------------------------------

# Plugin Concept

Core

↓

Plugin

↓

Story

↓

Factory

↓

Video

Planned Plugins

- Mystery

- Quiz

- History

- Ranking

- Science

------------------------------------------------------------

# Remotion

Remotion is only a Renderer.

Do not put business logic inside Remotion.

All editing decisions belong to Factory.

------------------------------------------------------------

# Development Rules

Always modify at most 3 files.

Always keep project compiling.

Never break existing functionality.

Always provide

1. Modified files

2. Full source code

3. Run

4. Expected result

5. Git Commit

------------------------------------------------------------

# Current Directory Structure

projects/

director/

story_graph.py

story_compiler.py

director_rules.py

timeline_schema.py

remotion/

episodes/

docs/

------------------------------------------------------------

# Important

The user wants to complete the Mystery Plugin first.

After Mystery Plugin is production-ready,

develop Quiz Plugin.

Web UI will be implemented after Factory Core and Mystery Plugin are complete.

Avoid unnecessary architecture discussions.

Focus on writing production-quality code.

------------------------------------------------------------

# Current Development Mode

Write code.

Test.

Commit.

Repeat.

No large redesign unless absolutely necessary.
