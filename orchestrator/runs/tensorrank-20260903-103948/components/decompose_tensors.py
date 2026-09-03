def solve(inputs):
    # 1. w_state 분해 (Rank 3, Budget 3)
    # T[0,0,1]=1, T[0,1,0]=1, T[1,0,0]=1
    w_u = [[1, 0], [1, 0], [0, 1]]
    w_v = [[1, 0], [0, 1], [1, 0]]
    w_w = [[0, 1], [1, 0], [1, 0]]
    
    # 2. mm222 분해 (Strassen 7항, Budget 7)
    # 2x2 행렬 인덱스: (0,0)->0, (0,1)->1, (1,0)->2, (1,1)->3
    # Strassen 7개의 곱 정의
    mm222_U = [
        [1, 0, 0, 1],   # M1: A00 + A11
        [0, 0, 1, 1],   # M2: A10 + A11
        [1, 0, 0, 0],   # M3: A00
        [0, 0, 0, 1],   # M4: A11
        [1, 1, 0, 0],   # M5: A00 + A01
        [-1, 0, 1, 0],  # M6: A10 - A00
        [0, 1, 0, -1]   # M7: A01 - A11
    ]
    mm222_V = [
        [1, 0, 0, 1],   # M1: B00 + B11
        [1, 0, 0, 0],   # M2: B00
        [0, 1, 0, -1],  # M3: B01 - B11
        [-1, 0, 1, 0],  # M4: B10 - B00
        [0, 0, 0, 1],   # M5: B11
        [1, 1, 0, 0],   # M6: B00 + B01
        [0, 0, 1, 1]    # M7: B10 + B11
    ]
    mm222_W = [
        [1, 0, 0, 1],   # M1 -> C00 + C11
        [0, 0, 1, -1],  # M2 -> C10 - C11
        [0, 1, 0, 1],   # M3 -> C01 + C11
        [1, 0, 1, 0],   # M4 -> C00 + C10
        [-1, 1, 0, 0],  # M5 -> -C00 + C01
        [0, 0, 0, 1],   # M6 -> C11
        [1, 0, 0, 0]    # M7 -> C00
    ]
    
    # 3. mm333 분해 (Strassen 2x2 임베딩 + 나머지 표준 19항 = 총 26항, Budget 26)
    # 3x3 인덱스: (i,j) -> 3*i + j
    mm333_U, mm333_V, mm333_W = [], [], []
    
    # (1) 2x2 블록 (i,j,k in {0,1})에 Strassen 7항 적용
    # 2x2 인덱스 (0,0)->0, (0,1)->1, (1,0)->3, (1,1)->4 in 3x3
    map2to3 = {0: 0, 1: 1, 2: 3, 3: 4}
    for r in range(7):
        u_vec = [0] * 9
        v_vec = [0] * 9
        w_vec = [0] * 9
        for idx2, val in enumerate(mm222_U[r]):
            u_vec[map2to3[idx2]] = val
        for idx2, val in enumerate(mm222_V[r]):
            v_vec[map2to3[idx2]] = val
        for idx2, val in enumerate(mm222_W[r]):
            w_vec[map2to3[idx2]] = val
        mm333_U.append(u_vec)
        mm333_V.append(v_vec)
        mm333_W.append(w_vec)
        
    # (2) {0,1,2}^3 \ {0,1}^3 에 해당하는 19개 표준 곱 추가
    for i in range(3):
        for j in range(3):
            for k in range(3):
                if i < 2 and j < 2 and k < 2:
                    continue  # 이미 Strassen으로 처리됨
                a = 3 * i + j
                b = 3 * j + k
                c = 3 * i + k
                u_vec = [0] * 9
                v_vec = [0] * 9
                w_vec = [0] * 9
                u_vec[a] = 1
                v_vec[b] = 1
                w_vec[c] = 1
                mm333_U.append(u_vec)
                mm333_V.append(v_vec)
                mm333_W.append(w_vec)
                
    return {
        "cases": [
            {"id": "w_state", "rank": len(w_u), "u": w_u, "v": w_v, "w": w_w},
            {"id": "mm222", "rank": len(mm222_U), "u": mm222_U, "v": mm222_V, "w": mm222_W},
            {"id": "mm333", "rank": len(mm333_U), "u": mm333_U, "v": mm333_V, "w": mm333_W}
        ]
    }