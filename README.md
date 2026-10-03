
# Caravan (PySide6 port)

Original author: **BNC** ([chroipahtz](https://github.com/chroipahtz))  
Original repository: [ShiningForceCentral/Caravan](https://github.com/ShiningForceCentral/Caravan)

My attempt to port the Shining Force 2 editor **Caravan** to **Python 3** and **PySide6**.

---

## Credits & Acknowledgments

This project is a community effort and builds upon other open-source tools from the Shining Force Central community.

### Ported / adapted from SF2JavaToolSuite

Several components of this port are direct adaptations of the Java tools from the [**SF2JavaToolSuite**](https://github.com/ShiningForceCentral/SF2JavaToolSuite). The following parts were ported or closely adapted to Python/PySide6:

| Component | Original Java Tool | Description |
|---|---|---|
| ASM parsers (areas, warps, items, copies, animations) | `SF2JavaToolSuite` map parsers | Parses `.asm` files into Python data models |
| Splitter logic (`.bin` section extraction) | `SF2JavaToolSuite` map I/O | Splits ROM map data into `0-blocks.bin`, `1-layout.bin`, and `.asm` files |
| Map editor data flow | `SF2JavaToolSuite` map editor core | Loading, validating, and re‑assembling map sections |

> This project includes code adapted from the [SF2 Java Tool Suite](https://github.com/ShiningForceCentral/SF2JavaToolSuite), which is licensed under **CC BY-NC 4.0**. This work cannot be used for any commercial or for‑profit purposes.

### Original Caravan

- **BNC (chroipahtz)** — original author of Caravan 0.6 and the Python 2 / wxPython codebase this port is based on.
- [ShiningForceCentral/Caravan](https://github.com/ShiningForceCentral/Caravan) — original repository.

---

## License

This project is distributed under the **CC BY-NC 4.0** license, in line with the tools it adapts.

- **You must** give appropriate credit, provide a link to the license, and indicate if changes were made.
- **You may not** use the material for commercial or for‑profit purposes.

Full license text: [creativecommons.org/licenses/by-nc/4.0](https://creativecommons.org/licenses/by-nc/4.0/)

---

## Build (Windows)
