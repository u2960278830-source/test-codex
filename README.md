+from __future__ import annotations
+
+from typing import Sequence
+
+import numpy as np
+from manim import (
+    BLUE,
+    DOWN,
+    FadeIn,
+    FadeOut,
+    GREEN,
+    LEFT,
+    Line,
+    MathTex,
+    ORANGE,
+    Polygon,
+    PURPLE,
+    RED,
+    RIGHT,
+    Scene,
+    Tex,
+    UP,
+    VGroup,
+    Write,
+    config,
+)
+
+
+class TrapezoidButterflyTheorem(Scene):
+    """Animate the butterfly area theorem inside a trapezoid."""
+
+    def construct(self) -> None:
+        # Define the vertices of the trapezoid in counter-clockwise order.
+        point_a = np.array([-4.5, 2.5, 0.0])
+        point_b = np.array([4.5, 2.5, 0.0])
+        point_c = np.array([-3.0, -2.5, 0.0])
+        point_d = np.array([3.5, -2.5, 0.0])
+
+        trapezoid = Polygon(point_a, point_b, point_d, point_c, color=ORANGE)
+        trapezoid.set_fill(ORANGE, opacity=0.15)
+
+        label_a = Tex("A").next_to(point_a, UP + LEFT * 0.2)
+        label_b = Tex("B").next_to(point_b, UP + RIGHT * 0.2)
+        label_c = Tex("C").next_to(point_c, DOWN + LEFT * 0.2)
+        label_d = Tex("D").next_to(point_d, DOWN + RIGHT * 0.2)
+
+        # Draw diagonals and find their intersection O.
+        diagonal_ac = self._segment(point_a, point_d)
+        diagonal_bd = self._segment(point_b, point_c)
+        intersection_o = self._line_intersection(point_a, point_d, point_b, point_c)
+        label_o = Tex("O").next_to(intersection_o, DOWN * 0.8)
+
+        # Draw the horizontal line through O parallel to AB.
+        intersection_e = self._line_intersection(point_a, point_c, intersection_o, intersection_o + np.array([1, 0, 0]))
+        intersection_f = self._line_intersection(point_b, point_d, intersection_o, intersection_o + np.array([1, 0, 0]))
+
+        parallel_line = self._segment(
+            intersection_o + np.array([-6, 0, 0]),
+            intersection_o + np.array([6, 0, 0]),
+            color=PURPLE,
+        )
+
+        label_e = Tex("E").next_to(intersection_e, LEFT)
+        label_f = Tex("F").next_to(intersection_f, RIGHT)
+
+        self.play(FadeIn(trapezoid))
+        self.play(*[Write(obj) for obj in [label_a, label_b, label_c, label_d]])
+
+        self.play(FadeIn(diagonal_ac), FadeIn(diagonal_bd))
+        self.play(FadeIn(label_o))
+
+        self.play(FadeIn(parallel_line))
+        self.play(FadeIn(label_e), FadeIn(label_f))
+
+        # Highlight the "butterfly" triangles.
+        triangle_top_left = Polygon(point_a, intersection_o, intersection_e, color=BLUE)
+        triangle_top_left.set_fill(BLUE, opacity=0.4)
+
+        triangle_top_right = Polygon(point_b, intersection_o, intersection_f, color=GREEN)
+        triangle_top_right.set_fill(GREEN, opacity=0.4)
+
+        triangle_bottom_left = Polygon(point_c, intersection_o, intersection_e, color=RED)
+        triangle_bottom_left.set_fill(RED, opacity=0.4)
+
+        triangle_bottom_right = Polygon(point_d, intersection_o, intersection_f, color=PURPLE)
+        triangle_bottom_right.set_fill(PURPLE, opacity=0.4)
+
+        top_group = VGroup(triangle_top_left, triangle_top_right)
+        bottom_group = VGroup(triangle_bottom_left, triangle_bottom_right)
+
+        self.play(FadeIn(top_group))
+        self.play(FadeIn(bottom_group))
+
+        statement = MathTex(
+            r"S_{\triangle AOE} + S_{\triangle BOF} = S_{\triangle COE} + S_{\triangle DOF}",
+            color=ORANGE,
+        )
+        statement.to_edge(DOWN)
+
+        explanation = Tex(
+            "通过对角线交点作底边的平行线，",
+            "梯形中的四个小三角形形成蝴蝶结构，",
+            "上翼与下翼面积相等。",
+            tex_environment="flushleft",
+        )
+        explanation.arrange(DOWN, aligned_edge=LEFT)
+        explanation.to_edge(LEFT)
+
+        self.play(Write(statement))
+        self.play(Write(explanation))
+
+        self.wait(2)
+
+        self.play(FadeOut(top_group), FadeOut(bottom_group), FadeOut(statement), FadeOut(explanation))
+        self.wait(0.5)
+
+    def _segment(self, start: np.ndarray, end: np.ndarray, color=ORANGE) -> Line:
+        """Create a thin polygon segment between two points."""
+
+        segment = Line(start, end, color=color)
+        segment.set_stroke(color=color, width=4)
+        return segment
+
+    def _line_intersection(
+        self,
+        p1: Sequence[float],
+        p2: Sequence[float],
+        p3: Sequence[float],
+        p4: Sequence[float],
+    ) -> np.ndarray:
+        """Compute the intersection point of lines p1p2 and p3p4."""
+
+        x1, y1 = p1[:2]
+        x2, y2 = p2[:2]
+        x3, y3 = p3[:2]
+        x4, y4 = p4[:2]
+
+        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
+        if abs(denominator) < 1e-6:
+            raise ValueError("Lines do not intersect or are coincident")
+
+        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
+        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
+
+        return np.array([px, py, 0.0])
+
+
+if __name__ == "__main__":
+    config.pixel_width = 1280
+    config.pixel_height = 720
+    config.frame_rate = 30
+    scene = TrapezoidButterflyTheorem()
+    scene.render()
 
EOF
)
