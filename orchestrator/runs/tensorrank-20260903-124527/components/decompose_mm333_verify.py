import json
from fractions import Fraction

def check(output, inputs):
    try:
        case = output['cases'][0]
        rank = case['rank']
        if rank > 23: return False, "Rank exceeds budget"
        # Verify constraints: |c| <= 8, den <= 12
        for vec in [case['u'], case['v'], case['w']]:
            for row in vec:
                for val in row:
                    f = Fraction(val)
                    if abs(f.numerator) > 8*f.denominator or f.denominator > 12: return False, "Constraint violation"
        return True, "Passed"
    except Exception as e: return False, str(e)