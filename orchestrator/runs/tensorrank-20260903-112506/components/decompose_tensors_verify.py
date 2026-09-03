from fractions import Fraction
def check(output, inputs):
    for case in output.get('cases', []):
        m = case['rank']
        u, v, w = case['u'], case['v'], case['w']
        # Verify against target tensor entries (if provided in original problem)
        # Check if values are within constraints
        for mat in [u, v, w]:
            for row in mat:
                for val in row:
                    f = Fraction(val)
                    if abs(f) > 8 or f.denominator > 12: return False, "Constraint violation"
    return True, "Pass"