def solve(inputs):
    from fractions import Fraction
    
    # 1. w_state: shape (2, 2, 2), rank 3 <= budget 3
    # T[0,0,1] = 1, T[0,1,0] = 1, T[1,0,0] = 1
    u_w = [[1, 0], [1, 0], [0, 1]]
    v_w = [[1, 0], [0, 1], [1, 0]]
    w_w = [[0, 1], [1, 0], [1, 0]]
    case_w = {
        "id": "w_state",
        "rank": 3,
        "u": u_w,
        "v": v_w,
        "w": w_w
    }
    
    # 2. mm222: 2x2 matmul, shape (4, 4, 4), rank 7 <= budget 7 (Strassen)
    # a = (i, j) = 2*i + j; b = (j, k) = 2*j + k; c = (i, k) = 2*i + k
    # Strassen 7 products
    # M1 = (A00 + A11) * (B00 + B11) -> C00 += M1, C11 += M1
    # M2 = (A10 + A11) * B00         -> C10 += M2, C11 -= M2
    # M3 = A00 * (B01 - B11)         -> C01 += M3, C11 += M3
    # M4 = A11 * (B10 - B00)         -> C00 += M4, C10 += M4
    # M5 = (A00 + A01) * B11         -> C00 -= M5, C01 += M5
    # M6 = (A10 - A00) * (B00 + B01) -> C11 += M6
    # M7 = (A01 - A11) * (B10 + B11) -> C00 += M7
    u_222 = [
        [1, 0, 0, 1],
        [0, 0, 1, 1],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [1, 1, 0, 0],
        [-1, 0, 1, 0],
        [0, 1, 0, -1]
    ]
    v_222 = [
        [1, 0, 0, 1],
        [1, 0, 0, 0],
        [0, 1, 0, -1],
        [-1, 0, 1, 0],
        [0, 0, 0, 1],
        [1, 1, 0, 0],
        [0, 0, 1, 1]
    ]
    w_222 = [
        [1, 0, 0, 1],
        [0, 0, 1, -1],
        [0, 1, 0, 1],
        [1, 0, 1, 0],
        [-1, 1, 0, 0],
        [0, 0, 0, 1],
        [1, 0, 0, 0]
    ]
    case_222 = {
        "id": "mm222",
        "rank": 7,
        "u": u_222,
        "v": v_222,
        "w": w_222
    }
    
    # 3. mm333: 3x3 matmul, shape (9, 9, 9), rank 26 <= budget 26
    # a = 3*i + j, b = 3*j + k, c = 3*i + k
    # We apply Strassen on the top-left 2x2 submatrix product (saving 1 multiplication: 27 -> 26)
    u_333, v_333, w_333 = [], [], []
    
    def add_term(u_vec, v_vec, w_vec):
        u_333.append(u_vec)
        v_333.append(v_vec)
        w_333.append(w_vec)
        
    # (1) Strassen for 2x2 submatrix (i in {0,1}, j in {0,1}, k in {0,1})
    # Terms M1..M7
    s_u = [
        {(0,0): 1, (1,1): 1},
        {(1,0): 1, (1,1): 1},
        {(0,0): 1},
        {(1,1): 1},
        {(0,0): 1, (0,1): 1},
        {(1,0): 1, (0,0): -1},
        {(0,1): 1, (1,1): -1}
    ]
    s_v = [
        {(0,0): 1, (1,1): 1},
        {(0,0): 1},
        {(0,1): 1, (1,1): -1},
        {(1,0): 1, (0,0): -1},
        {(1,1): 1},
        {(0,0): 1, (0,1): 1},
        {(1,0): 1, (1,1): 1}
    ]
    s_w = [
        {(0,0): 1, (1,1): 1},
        {(1,0): 1, (1,1): -1},
        {(0,1): 1, (1,1): 1},
        {(0,0): 1, (1,0): 1},
        {(0,0): -1, (0,1): 1},
        {(1,1): 1},
        {(0,0): 1}
    ]
    for r in range(7):
        u_vec = [0]*9
        v_vec = [0]*9
        w_vec = [0]*9
        for (i, j), val in s_u[r].items(): u_vec[3*i + j] = val
        for (j, k), val in s_v[r].items(): v_vec[3*j + k] = val
        for (i, k), val in s_w[r].items(): w_vec[3*i + k] = val
        add_term(u_vec, v_vec, w_vec)
        
    # (2) For (i,k) in {0,1}x{0,1}, add A[i, 2] * B[2, k]
    for i in [0, 1]:
        for k in [0, 1]:
            u_vec = [0]*9; u_vec[3*i + 2] = 1
            v_vec = [0]*9; v_vec[3*2 + k] = 1
            w_vec = [0]*9; w_vec[3*i + k] = 1
            add_term(u_vec, v_vec, w_vec)
            
    # (3) For (i, k) where i=2 or k=2, all standard A[i,j] * B[j,k] terms
    for i in range(3):
        for k in range(3):
            if i == 2 or k == 2:
                for j in range(3):
                    u_vec = [0]*9; u_vec[3*i + j] = 1
                    v_vec = [0]*9; v_vec[3*j + k] = 1
                    w_vec = [0]*9; w_vec[3*i + k] = 1
                    add_term(u_vec, v_vec, w_vec)
                    
    case_333 = {
        "id": "mm333",
        "rank": len(u_333),
        "u": u_333,
        "v": v_333,
        "w": w_333
    }
    
    return {"cases": [case_w, case_222, case_333]}