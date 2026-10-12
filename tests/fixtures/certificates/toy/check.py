import json, sys
from fractions import Fraction
v = json.load(open(sys.argv[1]))["values"]
print("value =", float(Fraction(sum(v), len(v))))
