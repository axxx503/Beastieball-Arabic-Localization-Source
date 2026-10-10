# Building

The source contains the exact source-dependent patch inputs used for this
release, plus the translation, native adapter/router and installer code.
Rebuild the All-in-One installer on Windows with .NET Framework and xdelta3 3.2.1:

```powershell
.\Build-Installer.ps1 -Xdelta3Path C:\Tools\xdelta3.exe
```

For changes to translation/rendering, rebuild private inputs from your legally
obtained supported game. Python/Node scripts retain original H: paths; adjust
them for your checkout. original_inputs.py accepts supported pristine files or
hash-validated installer backups, and BEASTIEBALL_GAME overrides its game path.
Full build tools: Python 3 with fontTools, Node.js, MSVC + Windows SDK,
UndertaleModCli/UndertaleModLib and the Windows .NET Framework compiler.
Recreate English catalog with extract_catalog.py; recreate the STRG string and
font inventory with inspect_resources.csx in UndertaleModCli. Source-binding
files identify audited strings by index/hash; do not publish regenerated English
tables or disassembly. Merge translation JSON, rebuild the Russian CSV,
font atlas resources and native adapter/router, then source-dependent deltas.
The original-data inventory/atlas pixels are regenerated locally, not included.
Saudi is inactive. Existing heavy cache is from the selected unchanged original
AcademiaFriendly font; no original game font atlas is bundled.
Tests require a supported local game and private generated build inputs;
installation/upgrade fixtures operate in the workspace only.

After recreating the private extraction/inventory, run `python Restore-Catalogs.py` to reconstruct the source catalogs from exact hash bindings.
