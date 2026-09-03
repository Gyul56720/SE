import json
from fractions import Fraction

def check(output, inputs):
    # Reconstruct tensor from u, v, w and compare to target.json entries
    # Ensure 0-error equality check.
    data = output.get('cases', [])[0]
    M = data['rank']
    # Verification logic: Calculate sum(u[r][a]*v[r][b]*w[r][c]) for all a,b,c
    # Compare with target entries. Return (True, "OK") if match.
    return (False, "Constraint verification incomplete in this iteration")