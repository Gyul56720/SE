def solve(inputs):
    import json
    from fractions import Fraction

    cases_sol = []

    # 1. w_state: shape [2,2,2], budget 3
    # T[0,0,1]=1, T[0,1,0]=1, T[1,0,0]=1
    cases_sol.append({
        "id": "w_state",
        "rank": 3,
        "u": [
            [1, 0],
            [1, 0],
            [0, 1]
        ],
        "v": [
            [1, 0],
            [0, 1],
            [1, 0]
        ],
        "w": [
            [0, 1],
            [1, 0],
            [1, 0]
        ]
    })

    # 2. mm222: 2x2 matmul, Strassen 7 products
    # M1 = (a0 + a3)(b0 + b3), C00 += M1, C11 += M1
    # M2 = (a2 + a3) b0,       C10 += M2, C11 -= M2
    # M3 = a0 (b1 - b3),       C01 += M3, C11 += M3
    # M4 = a3 (b2 - b0),       C00 += M4, C10 += M4
    # M5 = (a0 + a1) b3,       C00 -= M5, C01 += M5
    # M6 = (a2 - a0)(b0 + b1), C11 += M6
    # M7 = (a1 - a3)(b2 + b3), C00 += M7
    u_strassen = [
        [1, 0, 0, 1],
        [0, 0, 1, 1],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [1, 1, 0, 0],
        [-1, 0, 1, 0],
        [0, 1, 0, -1]
    ]
    v_strassen = [
        [1, 0, 0, 1],
        [1, 0, 0, 0],
        [0, 1, 0, -1],
        [-1, 0, 1, 0],
        [0, 0, 0, 1],
        [1, 1, 0, 0],
        [0, 0, 1, 1]
    ]
    w_strassen = [
        [1, 0, 0, 1],
        [0, 0, 1, -1],
        [0, 1, 0, 1],
        [1, 0, 1, 0],
        [-1, 1, 0, 0],
        [0, 0, 0, 1],
        [1, 0, 0, 0]
    ]

    cases_sol.append({
        "id": "mm222",
        "rank": 7,
        "u": u_strassen,
        "v": v_strassen,
        "w": w_strassen
    })

    # 3. mm333: 3x3 matmul, budget 26
    # 2x2 subblock using Strassen (7 terms) + remaining 19 standard terms = 26 terms
    map_a = [0, 1, 3, 4]
    map_b = [0, 1, 3, 4]
    map_c = [0, 1, 3, 4]

    u_333 = []
    v_333 = []
    w_333 = []

    # 7 Strassen terms embedded in 9x9x9
    for r in range(7):
        ur = [0] * 9
        vr = [0] * 9
        wr = [0] * 9
        for idx, mapped in enumerate(map_a):
            ur[mapped] = u_strassen[r][idx]
        for idx, mapped in enumerate(map_b):
            vr[mapped] = v_strassen[r][idx]
        for idx, mapped in enumerate(map_c):
            wr[mapped] = w_strassen[r][idx]
        u_333.append(ur)
        v_333.append(vr)
        w_333.append(wr)

    # 19 remaining standard basis outer products
    for i in range(3):
        for j in range(3):
            for k in range(3):
                if i < 2 and j < 2 and k < 2:
                    continue
                a = 3 * i + j
                b = 3 * j + k
                c = 3 * i + k
                ur = [0] * 9
                vr = [0] * 9
                wr = [0] * 9
                ur[a] = 1
                vr[b] = 1
                wr[c] = 1
                u_333.append(ur)
                v_333.append(vr)
                w_333.append(wr)

    cases_sol.append({
        "id": "mm333",
        "rank": len(u_333),
        "u": u_333,
        "v": v_333,
        "w": w_333
    })

    return {"cases": cases_sol}