// Robot 3B modeli ve lazer kesim sekilleri. Veri (diziler) design/design.py'den uretilir: generated/<varyant>.scad
// Kullanim:  openscad -D 'part="plate_top"' -o cikti.stl design/robot_pico.scad
// part: tum parcalarin adi | "plate_bottom_2d" | "plate_bottom_marks" | "plate_top_2d" | "plate_top_marks" | "bracket_2d"
$fn = 40;

module rrect2d(o) {                       // o = [x0, x1, y0, y1, r]
  r = o[4];
  hull() for (x = [o[0] + r, o[1] - r], y = [o[2] + r, o[3] - r]) translate([x, y]) circle(r);
}
module plate2d(o, holes, slots) {
  difference() {
    rrect2d(o);
    for (h = holes) translate([h[0], h[1]]) circle(d = h[2], $fn = 24);
    for (s = slots) translate([s[0], s[1]]) rotate(s[4]) square([s[2], s[3]], center = true);
  }
}
module marks2d(marks) {                   // yerlesim cizgileri (kazima): ince dikdortgen cercevesi
  for (m = marks) difference() {
    translate([m[0], m[1]]) square([m[2] - m[0], m[3] - m[1]]);
    translate([m[0] + 0.3, m[1] + 0.3]) square([m[2] - m[0] - 0.6, m[3] - m[1] - 0.6]);
  }
}
module plate3d(z, o, holes, slots) {
  translate([0, 0, z[0]]) linear_extrude(height = z[1] - z[0]) plate2d(o, holes, slots);
}
module part3d(p) {
  k = p[0];
  if (k == "box") translate([p[2], p[4], p[6]]) cube([p[3] - p[2], p[5] - p[4], p[7] - p[6]]);
  else if (k == "rbox") translate([p[2], p[3], p[6]]) rotate(p[8]) translate([-p[5] / 2, -p[4] / 2, 0]) cube([p[5], p[4], p[7] - p[6]]);
  else if (k == "cylz") translate([p[2], p[3], p[5]]) cylinder(d = p[4], h = p[6] - p[5]);
  // cyly: ["cyly", ad, cx, cz, y0, y1, d]
  else if (k == "cyly") translate([p[2], p[4], p[3]]) rotate([-90, 0, 0]) cylinder(d = p[6], h = p[5] - p[4]);
  else if (k == "sphere") translate([p[2], p[3], p[4]]) sphere(r = p[5]);
}

module render_part(name) {
  if (name == "plate_bottom_2d") plate2d(OUT_B, HOLES_B, SLOTS_B);
  else if (name == "plate_bottom_marks") marks2d(MARKS_B);
  else if (name == "plate_top_2d") plate2d(OUT_T, HOLES_T, SLOTS_T);
  else if (name == "plate_top_marks") marks2d(MARKS_T);
  else if (name == "bracket_2d") square([BRACKET[0], BRACKET[1]]);
  else if (name == "plate_bottom") plate3d(Z_B, OUT_B, HOLES_B, SLOTS_B);
  else if (name == "plate_top") plate3d(Z_T, OUT_T, HOLES_T, SLOTS_T);
  else for (p = PARTS) if (p[1] == name) part3d(p);
}
