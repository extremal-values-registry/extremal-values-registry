"""Exact verification of the step-function upper bound (stdlib only).
Usage: python -I verify.py construction.json
f is a step function on [-1/4, 1/4] with n equal cells of width h = (1/2)/n and the listed (signed) cell values.
(f*f)(t) = int f(t-x) f(x) dx is piecewise linear with knots at integer multiples of h, so max_t |f*f| is attained
at a knot, where (f*f)(m h) = h * sum_{i+j=m-1} v_i v_j. The ratio below is therefore the exact value of
max|f*f| / (int f)^2 for this f, computed in rational arithmetic, and it is an upper bound for the constant C.
"""
import json, sys
from fractions import Fraction as F
d = json.load(open(sys.argv[1]))
v = [F(x) for x in d["values"]]; n = len(v); h = F(1, 2) / n
conv = [F(0)] * (2 * n - 1)
for i in range(n):
    if v[i] == 0: continue
    for j in range(n): conv[i + j] += v[i] * v[j]
max_abs = h * max(abs(c) for c in conv)
integral = h * sum(v)
C = max_abs / (integral ** 2)
print("n =", n, " int f =", float(integral), " max|f*f| =", float(max_abs))
print("C(f) =", float(C), " (exact rational:", C.numerator, "/", C.denominator, ")")
print("upper bound C <=", float(C), "; previous best published 1.4688; improvement:", float(C) < 1.4688)
