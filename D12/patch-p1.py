#!/usr/bin/env python3
from pathlib import Path

def edit(path, pairs):
    p = Path(path)
    s = p.read_text()
    for a, b in pairs:
        if s.count(a) != 1:
            raise SystemExit(f"{path}: missing or ambiguous anchor {a[:80]!r}")
        s = s.replace(a, b, 1)
    p.write_text(s)

edit("Marlin/src/lcd/extui/mks_ui/draw_preHeat.cpp", [["    case ID_P_PLA:\n      if (uiCfg.curTempType == 0) {\n        TERN_(HAS_HOTEND, thermalManager.setTargetHotend(PREHEAT_1_TEMP_HOTEND, 0));\n      }\n      else if (uiCfg.curTempType == 1) {\n        TERN_(HAS_HEATED_BED, thermalManager.setTargetBed(PREHEAT_1_TEMP_BED));\n      }\n      break;","    case ID_P_PLA:\n      TERN_(HAS_HOTEND, thermalManager.setTargetHotend(PREHEAT_1_TEMP_HOTEND, 0));\n      TERN_(HAS_HEATED_BED, thermalManager.setTargetBed(PREHEAT_1_TEMP_BED));\n      disp_desire_temp();\n      break;"]])
edit("Marlin/src/lcd/extui/mks_ui/draw_baby_stepping.cpp", [["#include \"../../../gcode/gcode.h\"","#include \"../../../gcode/gcode.h\"\n#include \"../../../feature/babystep.h\"\n#include \"../../../module/planner.h\""],["    strcpy_P(buf, PSTR(\"Offset Z: 0 mm\"));","    char str_1[16];\n    const float delta = float(babystep.axis_total[BS_TOTAL_IND(Z_AXIS)]) / planner.settings.axis_steps_per_mm[Z_AXIS];\n    snprintf_P(buf, sizeof(buf), PSTR(\"Baby Z: %s mm\"), dtostrf(delta, 1, 3, str_1));"]])
# Refresh immediately after either Z button. Keep the existing periodic refresh too.
p = Path("Marlin/src/lcd/extui/mks_ui/draw_baby_stepping.cpp")
s = p.read_text()
for name, end in [("ID_BABY_STEP_Z_P", "ID_BABY_STEP_Z_N"), ("ID_BABY_STEP_Z_N", "ID_BABY_STEP_DIST")]:
    a = s.index("case " + name + ":")
    b = s.index("case " + end + ":", a)
    block = s[a:b]
    if block.count("has_adjust_z = 1;") != 1:
        raise SystemExit("Unexpected babystep handler")
    s = s[:a] + block.replace("has_adjust_z = 1;", "disp_z_offset_value();\\n      has_adjust_z = 1;".replace("\\n", "\n")) + s[b:]
p.write_text(s)

# Fail early if the pinned build is ever accidentally configured for a probe.
config = Path('Marlin/Configuration.h')
# The compiler copies the selected profile after this source patch.
print('P1 UI patch applied; use only with the no-probe profile.')
