# -*- coding: utf-8 -*-
"""Volume I, Part X24 -- Numerical linear algebra in finite precision."""
import sys, math
sys.path.insert(0, "/home/user/SE/edu")
import numpy as np
from bookE import tab, fig, E
from wex import ex, prob, derive, sweep, plot, num
from figs import svg, box, txt, arr, line


def ch_numlin():
    s = ['<h1 id="x24">X24. Numerical Linear Algebra in Finite Precision</h1>']
    s.append("""<p>Matrix operations appear in equalisers, beamformers, MIMO detectors,
    calibration engines and image pipelines. In floating point on a workstation they are
    a library call; in fixed point in hardware they are a conditioning problem, and the
    quantity that decides everything is the condition number. This part makes that
    quantity concrete.</p>""")

    s.append("<h2>X24.1 Conditioning: how many bits the problem destroys</h2>")
    s.append(derive("The condition number, and what it costs you", [
        ("For <b>A</b><b>x</b> = <b>b</b>, perturb <b>b</b> by &delta;<b>b</b>. Then "
         "&delta;<b>x</b> = <b>A</b><sup>&minus;1</sup>&delta;<b>b</b>.",
         "Linearity."),
        ("Bounding the relative error gives "
         "&#8214;&delta;<b>x</b>&#8214;/&#8214;<b>x</b>&#8214; &le; "
         "&kappa;(<b>A</b>) &#8214;&delta;<b>b</b>&#8214;/&#8214;<b>b</b>&#8214;, with "
         "&kappa; = &#8214;<b>A</b>&#8214;&nbsp;&#8214;<b>A</b><sup>&minus;1</sup>&#8214;.",
         "Combine the two norm inequalities. In the 2-norm, &kappa; is the ratio of "
         "largest to smallest singular value."),
        ("<b>So log<sub>2</sub>&kappa; bits of the answer are destroyed by the "
         "problem itself</b>, before any algorithm is chosen.",
         "A condition number of 10<sup>6</sup> costs about 20 bits. <b>No algorithm "
         "recovers them</b> &mdash; this is a property of the matrix, not of the "
         "arithmetic."),
        ("A <i>backward stable</i> algorithm adds only about log<sub>2</sub>(<i>n</i>) "
         "bits of its own.",
         "It returns the exact answer to a slightly perturbed problem. "
         "<b>Householder QR is backward stable; forming the normal equations is "
         "not</b>, and X24.2 measures the difference."),
        ("Word length needed &asymp; bits wanted + log<sub>2</sub>&kappa; + a few.",
         "<b>The practical sizing rule for any matrix operation in hardware.</b>"),
    ]))
    rng = np.random.default_rng(3)
    rows = []
    for k_target in (1e1, 1e3, 1e5, 1e7, 1e9):
        n = 8
        U, _ = np.linalg.qr(rng.normal(size=(n, n)))
        V, _ = np.linalg.qr(rng.normal(size=(n, n)))
        sv = np.logspace(0, -math.log10(k_target), n)
        A = U @ np.diag(sv) @ V.T
        x = rng.normal(size=n)
        b = A @ x
        best = None
        for bits in range(8, 60, 2):
            q = lambda z: np.round(z * (1 << bits)) / (1 << bits)
            xh = np.linalg.solve(q(A), q(b))
            rel = float(np.linalg.norm(xh - x) / np.linalg.norm(x))
            if rel < 1e-3:
                best = bits
                break
        rows.append([num(k_target, 2), num(float(np.linalg.cond(A)), 4),
                     num(math.log2(float(np.linalg.cond(A))), 4),
                     num(best if best else -1),
                     num((best - 10) if best else -1)])
    s.append(sweep("Measured fraction bits needed to solve an 8&times;8 system to "
                   "10<sup>&minus;3</sup> relative error, against condition number",
        ["Target &kappa;", "Actual &kappa;", "log<sub>2</sub>&kappa;",
         "Fraction bits needed", "Bits above the 10 the answer needs"], rows,
        "Matrices built with prescribed singular values, seed 3. <b>The last two "
        "columns track log<sub>2</sub>&kappa; closely</b>, which is the derivation's "
        "prediction and an independent confirmation of it."))
    s.append("""<div class="warn"><b>Condition number is a property of the problem you
    chose, and you often get to choose a better one.</b> A least-squares fit to a
    polynomial in the monomial basis has a condition number that grows exponentially with
    degree; the same fit in a Chebyshev or orthogonal-polynomial basis is well conditioned.
    A channel matrix that is ill conditioned can be regularised &mdash; add
    &lambda;<b>I</b> &mdash; trading a small bias for an enormous variance reduction. And
    an equaliser that inverts a channel is ill conditioned exactly where the channel has a
    null, which is why zero-forcing equalisers amplify noise and MMSE equalisers, which
    are regularised zero-forcing, do not. <b>Three apparently unrelated pieces of
    engineering folklore are the same statement about conditioning.</b></div>""")
    # zero-forcing vs MMSE measured
    rows = []
    N = 4096
    h = np.array([0.1, 0.55, 1.0, 0.45, 0.12])
    for snr_db in (5, 10, 15, 20, 25, 30):
        sn = 10 ** (-snr_db / 20)
        x = rng.choice([-1.0, 1.0], N)
        y = np.convolve(x, h, "same") + rng.normal(0, sn, N)
        nfft = 4096
        H = np.fft.fft(h, nfft)
        Y = np.fft.fft(y, nfft)
        zf = np.real(np.fft.ifft(Y / H))[:N]
        mm = np.real(np.fft.ifft(Y * np.conj(H) / (np.abs(H) ** 2 + sn ** 2)))[:N]
        ber_zf = float(np.mean(np.sign(zf[10:-10]) != x[10:-10]))
        ber_mm = float(np.mean(np.sign(mm[10:-10]) != x[10:-10]))
        rows.append([num(snr_db), num(float(np.abs(H).max() / np.abs(H).min()), 5),
                     num(ber_zf, 2), num(ber_mm, 2),
                     "<b>MMSE</b>" if ber_mm <= ber_zf else "ZF"])
    s.append(sweep("Zero-forcing against MMSE on the same channel &mdash; regularisation "
                   "measured",
        ["SNR (dB)", "Channel &kappa; (spectral)", "BER, zero-forcing", "BER, MMSE",
         "Better"], rows,
        "Both equalisers computed in the frequency domain on the same received signal; "
        "the channel is the same on every row, so its condition number is constant by "
        "construction and only the noise changes. "
        "<b>Zero-forcing divides by the channel and therefore divides the noise by the "
        "channel too</b>, which is catastrophic at the spectral null; MMSE adds the "
        "noise variance to the denominator and the problem disappears. The condition "
        "number column says why."))

    s.append("<h2>X24.2 Decompositions, and which one belongs in hardware</h2>")
    s.append(tab("Matrix decompositions for an <i>n</i>&times;<i>n</i> system",
        ["Decomposition", "Cost", "Stability", "Hardware friendliness", "Use"],
        [["Normal equations "
          "(<b>A</b><sup>T</sup><b>A</b>)", "<i>n</i><sup>3</sup>/3",
          "<b>Squares the condition number &mdash; halves your bits</b>", "Simple",
          "<b>Only when &kappa; is small and known</b>"],
         ["<b>QR by Givens rotations</b>", "2<i>n</i><sup>3</sup>",
          "<b>Backward stable</b>",
          "<b>Excellent &mdash; a systolic array of CORDIC cells</b>",
          "<b>The standard hardware answer</b>"],
         ["QR by Householder", "4<i>n</i><sup>3</sup>/3", "Backward stable",
          "Poor &mdash; needs whole-column operations", "Software"],
         ["Cholesky", "<i>n</i><sup>3</sup>/3", "Stable for positive definite",
          "Good, but needs a square root and a divide",
          "Covariance matrices, MMSE"],
         ["SVD", "~10<i>n</i><sup>3</sup>", "Most stable; gives &kappa; directly",
          "Expensive; iterative", "When you need the singular values themselves"],
         ["LU with pivoting", "2<i>n</i><sup>3</sup>/3", "Stable with pivoting",
          "<b>Pivoting is data-dependent control &mdash; awkward in a systolic "
          "array</b>", "General software"]]))
    s.append(ex("What forming the normal equations costs you, in bits",
        "A least-squares problem whose matrix has &kappa;&nbsp;=&nbsp;10<sup>4</sup>. "
        "You need 12 bits of accuracy in the answer.",
        "Compare the two routes. The normal-equations route squares the condition "
        "number before solving; the QR route does not.",
        [("&kappa;(<b>A</b>)", "10<sup>4</sup>"),
         ("log<sub>2</sub>&kappa;", num(math.log2(1e4), 4)),
         ("QR route: bits needed", num(12 + math.log2(1e4) + 3, 4)),
         ("&kappa;(<b>A</b><sup>T</sup><b>A</b>)", "10<sup>8</sup>"),
         ("Normal equations: bits needed", num(12 + math.log2(1e8) + 3, 4)),
         ("Extra bits", num(math.log2(1e8) - math.log2(1e4), 4)),
         ("Multiplier area penalty (quadratic in width)",
          num(((12 + math.log2(1e8) + 3) / (12 + math.log2(1e4) + 3)) ** 2, 4)
          + "&times;")],
        "<b>By choosing the normal equations because the operation count is half.</b> "
        "It is half, and the word length is larger, and multiplier area goes as the "
        "square of the word length &mdash; so the cheaper algorithm produces the larger "
        "circuit. <b>Operation count is the wrong cost model for fixed-point hardware</b>; "
        "the right one is operations times word length squared, with the word length "
        "derived from the conditioning. This single substitution reverses a great many "
        "textbook recommendations."))
    s.append("""<div class="ms"><b>Why Givens rotations and CORDIC are made for each
    other.</b> A Givens rotation zeroes one element by rotating two rows, which is exactly
    a two-dimensional rotation by an angle determined from the data &mdash; a
    <i>vectoring</i> operation followed by <i>rotation</i> operations, which is precisely
    what the two CORDIC modes of Part&nbsp;X9 compute. So a QR decomposition maps onto a
    triangular array of identical CORDIC cells with only nearest-neighbour connections:
    the boundary cells vectorise to find the angle, the internal cells rotate by it, and
    the angle travels along the row. No multipliers, no divides, no square roots, no
    data-dependent control, and a systolic schedule that keeps every cell busy. <b>This is
    one of the cleanest algorithm-architecture matches in the field</b>, and it is the
    reason adaptive beamformers and MIMO detectors look the way they do.</div>""")

    s.append("<h2>X24.3 Iterative methods, and when they beat a decomposition</h2>")
    rows = []
    for kappa in (10, 100, 1000, 10000):
        # CG convergence: error reduced by ((sqrt(k)-1)/(sqrt(k)+1))^i
        rate = (math.sqrt(kappa) - 1) / (math.sqrt(kappa) + 1)
        it = math.ceil(math.log(1e-6) / math.log(rate))
        jac = 0.5 ** 0  # placeholder
        rows.append([num(kappa), num(rate, 5), num(it),
                     num(it * 2), num(math.ceil(math.log(1e-6) /
                                                math.log((kappa - 1) / (kappa + 1))))])
    s.append(sweep("Conjugate-gradient iterations to reduce the error by "
                   "10<sup>&minus;6</sup>",
        ["&kappa;", "Convergence factor per iteration", "CG iterations",
         "Matrix&ndash;vector products", "Steepest descent, for comparison"], rows,
        "From the standard CG bound. <b>CG converges in O(&radic;&kappa;) iterations and "
        "steepest descent in O(&kappa;)</b> &mdash; the square root is the whole reason "
        "CG exists, and the last column shows what it is worth."))
    s.append(tab("Direct versus iterative, in hardware terms",
        ["", "Direct (QR, Cholesky)", "Iterative (CG, Jacobi, Gauss&ndash;Seidel)"],
        [["Latency", "Fixed and known", "<b>Data dependent</b>"],
         ["Suits", "Small dense matrices", "Large sparse ones"],
         ["Hardware", "Systolic array; fully scheduled",
          "A matrix&ndash;vector engine plus control"],
         ["Word length", "Set by &kappa; once", "Can be lower &mdash; iteration "
          "corrects earlier rounding"],
         ["<b>Mixed precision</b>", "Hard", "<b>Natural: iterate in low precision, "
          "refine in high</b>"],
         ["Fits a real-time deadline", "<b>Yes</b>",
          "Only with an iteration cap, and then the accuracy is not guaranteed"]]))
    s.append("""<div class="bs"><b>Iterative refinement is the trick that makes low
    precision usable, and it is worth stating exactly.</b> Solve <b>A</b><b>x</b> =
    <b>b</b> in low precision to get <b>x</b><sub>0</sub>; compute the residual <b>r</b> =
    <b>b</b> &minus; <b>A</b><b>x</b><sub>0</sub> <i>in high precision</i>; solve
    <b>A</b>&delta; = <b>r</b> in low precision again; add. Each round roughly squares the
    accuracy while only the residual &mdash; one matrix&ndash;vector product &mdash; needs
    the wide arithmetic. <b>This is why modern accelerators pair low-precision multipliers
    with high-precision accumulation</b>, which Part&nbsp;X9 justified on different
    grounds; here is the same asymmetry arriving from numerical analysis rather than from
    neural networks.</div>""")
    # iterative refinement measured
    rng2 = np.random.default_rng(11)
    rows = []
    n = 16
    for rho in (0.0, 0.9, 0.99):
        A = rng2.normal(size=(n, n))
        A = A + rho * np.outer(A[:, 0], np.ones(n))
        x = rng2.normal(size=n)
        b = A @ x
        q = lambda z, bb=12: np.round(z * (1 << bb)) / (1 << bb)
        x0 = np.linalg.solve(q(A), q(b))
        e0 = float(np.linalg.norm(x0 - x) / np.linalg.norm(x))
        xi = x0.copy()
        errs = [e0]
        for _ in range(3):
            r = b - A @ xi                       # high precision residual
            d = np.linalg.solve(q(A), q(r))
            xi = xi + d
            errs.append(float(np.linalg.norm(xi - x) / np.linalg.norm(x)))
        rows.append([num(rho, 3), num(float(np.linalg.cond(A)), 4)] +
                    [num(e, 3) for e in errs])
    s.append(sweep("Measured iterative refinement: 12-bit solves, high-precision "
                   "residual, 16&times;16 systems",
        ["Correlation &rho;", "&kappa;(<b>A</b>)", "After solve",
         "1 refinement", "2", "3"], rows,
        "The third column is what a 12-bit solver alone delivers; each refinement "
        "costs one more 12-bit solve plus one wide matrix&ndash;vector product. "
        "<b>The well-conditioned row converges to the limit of the arithmetic in one "
        "or two rounds; the ill-conditioned row does not, because refinement cannot "
        "recover the bits the problem destroyed</b> &mdash; the derivation in X24.1 "
        "said so, and this measures it."))
    s.append(prob("You must invert a 4&times;4 covariance matrix every microsecond in "
                  "hardware. What structure, and what word length?",
        "<b>Structure first: do not invert it.</b> A covariance matrix is symmetric "
        "positive definite, so the operation almost certainly wanted is to <i>solve</i> "
        "a system, and Cholesky plus two triangular solves is a third of the cost of "
        "forming an inverse and is better conditioned. If an explicit inverse really is "
        "needed &mdash; for example the weights must be exposed &mdash; Cholesky then "
        "inverts the triangular factor. <b>Word length second</b>: measure the condition "
        "number of the covariance over the operating range, because for a covariance it "
        "is the ratio of largest to smallest eigenvalue and it becomes enormous when the "
        "inputs are correlated, which is exactly when a beamformer is working hardest; "
        "then apply the rule from X24.1, bits wanted plus log<sub>2</sub>&kappa; plus a "
        "margin. <b>Third, regularise</b>: adding a small &lambda;<b>I</b> &mdash; "
        "diagonal loading, in the beamforming literature &mdash; bounds &kappa; by "
        "construction, costs a tiny bias, and converts an unbounded word-length "
        "requirement into a fixed one. That conversion from &lsquo;depends on the "
        "data&rsquo; to &lsquo;bounded by design&rsquo; is what makes the block "
        "implementable at all."))
    return "\n".join(s)
