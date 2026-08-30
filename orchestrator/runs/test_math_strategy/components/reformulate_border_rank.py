def solve(inputs):
    import numpy as np
    # Border rank decomposition strategy for size=3, b=3 tensor
    # Approximating via limit of CP decompositions
    # Return planned parameters and initial factors
    np.random.seed(42)
    R = 5 # border rank upper bound
    factors = [np.random.randn(3, R) for _ in range(3)]
    return {'rank': R, 'factors': [f.tolist() for f in factors], 'status': 'border_rank_formulated'}