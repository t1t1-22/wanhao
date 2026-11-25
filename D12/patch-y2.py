#!/usr/bin/env python3
"""D12-Y2: observe real Y-switch transitions before homing; retain all safety checks."""
from pathlib import Path

def edit(path, replacements):
    p = Path(path)
    s = p.read_text()
    for before, after in replacements:
        n = s.count(before)
        if n != 1:
            raise SystemExit(f"{path}: expected one match, got {n}: {before[:100]!r}")
        s = s.replace(before, after, 1)
    p.write_text(s)

edit("Marlin/src/module/endstops.h", [
    ("    Endstops() {};",
     """    Endstops() {};

    // D12-Y2: No movement. Learn the idle level from a deliberate release,
    // press and release of the mechanical Y switch (once per boot).
    static const char* y2_sample();
    static bool y2_verified();
    static bool y2_triggered();
    static bool y2_contact(const bool expected);"""),
])

edit("Marlin/src/module/endstops.cpp", [
    ("void __O2 Endstops::report_states() {",
     """// D12-Y2: use the same direct GPIO read as Marlin's M119.
#if !HAS_Y_MIN || !Y_HOME_TO_MIN
  #error "D12-Y2 requires the physical Y-min switch."
#endif
static uint8_t y2_stage = 0;
static volatile bool y2_idle_level = Y_MIN_ENDSTOP_INVERTING;
static bool y2_candidate_idle = false;

bool Endstops::y2_verified() { return y2_stage == 3; }

bool Endstops::y2_triggered() {
  return bool(READ_ENDSTOP(Y_MIN_PIN)) != y2_idle_level;
}

bool Endstops::y2_contact(const bool expected) {
  // Called only from the foreground, after synchronization.
  for (uint8_t i = 0; i < 3; ++i) {
    if (y2_triggered() != expected) return false;
    safe_delay(3);
  }
  return y2_triggered() == expected;
}

const char* Endstops::y2_sample() {
  if (y2_verified()) return "Y OK\\nVerified";
  // Samples are taken only while the operator presses the screen button.
  const bool raw = READ_ENDSTOP(Y_MIN_PIN);
  for (uint8_t i = 0; i < 4; ++i) {
    delay(3); // Avoid re-entering the LVGL event loop while sampling.
    if (bool(READ_ENDSTOP(Y_MIN_PIN)) != raw) return "Y unstable\\nRetry";
  }
  if (y2_stage == 0) {
    y2_candidate_idle = raw;
    y2_stage = 1;
    return raw ? "Y 1\\nPress+tap" : "Y 0\\nPress+tap";
  }
  if (y2_stage == 1) {
    if (raw == y2_candidate_idle) return raw ? "Y 1 same\\nPress+tap" : "Y 0 same\\nPress+tap";
    y2_stage = 2;
    return raw ? "Y 1\\nRelease" : "Y 0\\nRelease";
  }
  if (raw != y2_candidate_idle) return raw ? "Y 1\\nRelease" : "Y 0\\nRelease";
  y2_idle_level = y2_candidate_idle;
  y2_stage = 3;
  SERIAL_ECHOLNPGM("D12-Y2: Y switch verified. Idle GPIO=", int(y2_idle_level));
  return "Y OK\\nVerified";
}

void __O2 Endstops::report_states() {"""),
    ("    ES_REPORT(Y_MIN);",
     "    print_es_state(y2_triggered(), F(STR_Y_MIN));"),
    ("    UPDATE_ENDSTOP_BIT(Y, MIN);",
     "    SET_BIT_TO(live_state, Y_MIN, y2_triggered());"),
])

edit("Marlin/src/lcd/extui/mks_ui/draw_home.cpp", [
    ('#include "../../../gcode/queue.h"',
     '#include "../../../gcode/queue.h"\n#include "../../../module/endstops.h"'),
    ("  ID_H_OFF_XY\n};", "  ID_H_OFF_XY,\n  ID_H_TEST_Y\n};"),
    ("    case ID_H_RETURN:\n",
     """    case ID_H_TEST_Y: {
      lv_obj_t *label = (lv_obj_t*)obj->child_ll.head;
      if (label) {
        lv_label_set_text(label, Endstops::y2_sample());
        lv_obj_align(label, obj, LV_ALIGN_CENTER, 0, 0);
      }
    } break;
    case ID_H_RETURN:
"""),
    ('  lv_big_button_create(scr, "F:/bmp_return.bin", common_menu.text_back,',
     '''  lv_obj_t *test = lv_big_button_create(scr, "F:/bmp_function1.bin",
    "Test Y", BTN_X_PIXEL * 2 + INTERVAL_V * 3,
    BTN_Y_PIXEL + INTERVAL_H + titleHeight, event_handler, ID_H_TEST_Y, true);
  lv_obj_t *test_label = (lv_obj_t*)test->child_ll.head;
  if (test_label) {
    lv_label_set_text(test_label, Endstops::y2_verified() ? "Y OK" : "Y test\\nRelease+tap");
    lv_obj_align(test_label, test, LV_ALIGN_CENTER, 0, 0);
  }
  lv_big_button_create(scr, "F:/bmp_return.bin", common_menu.text_back,'''),
])

edit("Marlin/src/gcode/calibrate/G28.cpp", [
    ("  planner.synchronize();          // Wait for planner moves to finish!",
     """  planner.synchronize();          // Wait for planner moves to finish!
  // D12-Y2: fail closed BEFORE starting any homing travel.
  if (!Endstops::y2_verified()) {
    SERIAL_ECHOLNPGM("D12-Y2: Run Test Y on Home screen first");
    kill(F("Y2 TEST Y FIRST"));
    return;
  }"""),
])

edit("Marlin/src/module/motion.cpp", [
    ("    const float move_length = 1.5f * max_length(TERN(DELTA, Z_AXIS, axis)) * axis_home_dir;",
     """    if (axis == Y_AXIS && !Endstops::y2_verified()) {
      kill(F("Y2 TEST Y FIRST"));
      return;
    }
    const float move_length = 1.5f * max_length(TERN(DELTA, Z_AXIS, axis)) * axis_home_dir;"""),
    ("    do_homing_move(axis, move_length, 0.0, !use_probe_bump);",
     """    if (axis == Y_AXIS) endstops.hit_on_purpose();
    do_homing_move(axis, move_length, 0.0, !use_probe_bump);
    if (axis == Y_AXIS && !Endstops::y2_contact(true)) {
      kill(F("Y2 CONTACT MISSING"));
      return;
    }"""),
    ("        if (TEST(endstops.state(), es)) {",
     """        if (axis == Y_AXIS && !Endstops::y2_contact(false)) {"""),
    ("      do_homing_move(axis, rebump, get_homing_bump_feedrate(axis), true);",
     """      if (axis == Y_AXIS) endstops.hit_on_purpose();
      do_homing_move(axis, rebump, get_homing_bump_feedrate(axis), true);
      if (axis == Y_AXIS && !Endstops::y2_contact(true)) {
        kill(F("Y2 SECOND CONTACT"));
        return;
      }"""),
    ("      endstops.validate_homing_move();",
     """      if (axis == Y_AXIS && !TEST(endstops.trigger_state(), Y_MIN)) {
        kill(F("Y2 NO Y HIT"));
        return;
      }
      endstops.validate_homing_move();"""),
])

print("D12-Y2 source transformations verified and applied.")
