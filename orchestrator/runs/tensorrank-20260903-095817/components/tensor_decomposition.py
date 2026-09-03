def solve(inputs):
    # 1. w_state: 3 terms
    w_u = [[1, 0], [1, 0], [0, 1]]
    w_v = [[1, 0], [0, 1], [1, 0]]
    w_w = [[0, 1], [1, 0], [1, 0]]

    # 2. mm222: Strassen's 7 terms
    # Matrix indices 0:(0,0), 1:(0,1), 2:(1,0), 3:(1,1)
    mm222_u = [
        [1, 0, 0, 1],   # M1: A0 + A3
        [0, 0, 1, 1],   # M2: A2 + A3
        [1, 0, 0, 0],   # M3: A0
        [0, 0, 0, 1],   # M4: A3
        [1, 1, 0, 0],   # M5: A0 + A1
        [-1, 0, 1, 0],  # M6: A2 - A0
        [0, 1, 0, -1]   # M7: A1 - A3
    ]
    mm222_v = [
        [1, 0, 0, 1],   # M1: B0 + B3
        [1, 0, 0, 0],   # M2: B0
        [0, 1, 0, -1],  # M3: B1 - B3
        [-1, 0, 1, 0],  # M4: B2 - B0
        [0, 0, 0, 1],   # M5: B3
        [1, 1, 0, 0],   # M6: B0 + B1
        [0, 0, 1, 1]    # M7: B2 + B3
    ]
    mm222_w = [
        [1, 0, 0, 1],   # M1: C0 + C3
        [0, 0, 1, -1],  # M2: C2 - C3
        [0, 1, 0, 1],   # M3: C1 + C3
        [1, 0, 1, 0],   # M4: C0 + C2
        [-1, 1, 0, 0],  # M5: -C0 + C1
        [0, 0, 0, 1],   # M6: C3
        [1, 0, 0, 0]    # M7: C0
    ]

    # 3. mm333: 27 terms (naive standard basis decomposition)
    # entries: (3*i+j, 3*j+k, 3*i+k) for i, j, k in 0..2
    mm333_u = []
    mm333_v = []
    mm333_w = []
    for i in range(3):
        for j in range(3):
            for k in range(3):
                a = 3 * i + j
                b = 3 * j + k
                c = 3 * i + k
                u_vec = [0] * 9
                v_vec = [0] * 9
                w_vec = [0] * 9
                u_vec[a] = 1
                v_vec[b] = 1
                w_vec[c] = 1
                mm333_u.append(u_vec)
                mm333_v.append(v_vec)
                mm333_w.append(w_vec)

    cases = [
        {
            "id": "w_state",
            "rank": 3,
            "u": w_u,
            "v": w_v,
            "w": w_w
        },
        {
            "id": "mm222",
            "rank": 7,
            "u": mm222_u,
            "v": mm222_v,
            "w": mm222_w
        },
        {
            "id": "mm333",
            "rank": 27,
            "u": mm333_u,
            "v": mm333_v,
            "w": mm333_w
        }
    ]
    return {"cases": cases}