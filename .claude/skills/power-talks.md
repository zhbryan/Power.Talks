---
name: power-talks
description: Power.Talks project assistant. Saves generated code to "Database Codes/" and downloaded documents to "Documents Database/". Invoke when working in the Power.Talks project.
trigger: When the user invokes /power-talks, or when working in the Power.Talks project and needs a reminder of folder conventions.
---

# Power.Talks Project Skill

You are working in the **Power.Talks** project.

## Folder Conventions

| What | Where to save |
|------|--------------|
| Any generated programming code (scripts, HTML, CSS, JS, Python, etc.) | `Database Codes/` |
| Any downloaded/fetched documents from the internet (PDFs, articles, reports, etc.) | `Documents Database/` |

Always use these folders when creating or saving files — do not prompt the user to choose a location for these file types.
