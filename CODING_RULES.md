# Developer Coding Rules

All modifications, additions, and tools built for this repository must strictly adhere to the following architectural guardrails.

## 1. Safety & Sandbox Protections
* **MESA Core is Read-Only**: Tools must NEVER alter, create, or delete any files located within the core MESA installation repository (`../mesa/`).
* **Workspace Separation**: All active code exploration, simulation building, and namelist writing must happen within isolated working folders created outside the main code tree.

## 2. Text Manipulation & Patching Modalities
* **No Wholesale Overwrites**: When editing `inlist` files or updating `src/run_star_extras.f90`, tools must avoid replacing the entire file. Use precise block location matching or explicit line patching to insert fields.
* **Format Stability**: Retain the existing Fortran spacing, syntax rules, and namelist formatting structures. Ensure all brackets, ampersands, and indentation profiles remain intact.

## 3. Technology Stack & Framework
* **Language**: Python 3.10+
* **Core Libraries**: `mcp[cli]`, `httpx`, `beautifulsoup4`, `pandas`
* **MCP Paradigm**: Utilize `FastMCP` decorators exclusively for tool and resource declarations. Keep functional structures short, modular, and highly focused.

## 4. Error Logging & Subprocess Control
* **Fail Fast**: Capture and relay stderr compiler outputs and process tracking messages cleanly to the tool evaluation output. Do not silence execution failures.
* **Asynchronous Lifecycles**: Ensure long-running simulations utilize detached process tracking tokens (PIDs) so tool loops do not hang or block the client.
