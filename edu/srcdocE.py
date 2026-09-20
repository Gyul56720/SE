# -*- coding: utf-8 -*-
"""Per-block notes for Volume II: what the code is, why it exists, the EECS
concepts behind it, and a practice note."""

D = {}

def _(name, what, why, eecs, practice):
    D[name] = dict(what=what, why=why, eecs=eecs, practice=practice)


_("AES 골든 모델 (C)",
  "A 573-line C implementation of FIPS-197 AES: the S-box table, <code>xtime</code>, the "
  "four round functions, key expansion, and ECB/CBC/CTR modes.",
  "<b>To define what is correct.</b> Judging an RTL implementation requires an expected "
  "value computed independently. This file produces it. The complete absence of hardware "
  "concepts &mdash; no clock, no ports, no state machine &mdash; is deliberate: only the "
  "<i>meaning</i> remains.",
  "Finite-field GF(2<sup>8</sup>) arithmetic; substitution&ndash;permutation network "
  "structure; Shannon's confusion and diffusion.",
  "Note that <code>xtime</code> multiplies by a mask rather than branching. This keeps "
  "execution time independent of the data &mdash; the most basic timing-side-channel "
  "discipline &mdash; and it is worth preserving even in a model.")

_("AES·SHA·MD5 C 참조 구현",
  "Brad Conte's reference implementations of common cryptographic primitives, each "
  "self-contained in one file.",
  "<b>To serve as a second, independent implementation.</b> A single golden model cannot "
  "reveal its own misreading of a standard. Two implementations written by different "
  "authors from the same document agree only where both read it the same way.",
  "Merkle&ndash;Damg&aring;rd construction; compression functions; padding rules; "
  "collision resistance.",
  "Cross-validating two independent models early makes the later triage of an RTL "
  "mismatch much cheaper, because the possibility &ldquo;the model is wrong&rdquo; can be "
  "dismissed in minutes rather than days.")

_("AES 코어 (Verilog)",
  "Joachim Str&ouml;mbergson's AES in Verilog: encipher and decipher cores, S-box, key memory.",
  "<b>To provide the plain-RTL baseline.</b> Neither HLS C++ nor hardened security RTL, "
  "it shows how small AES is when only the function is implemented. Comparing it with "
  "OpenTitan's 17,000 lines isolates exactly what side-channel and fault countermeasures "
  "cost.",
  "Register-transfer abstraction; finite state machines; separation of datapath and control.",
  "When evaluating any IP, the useful question is not &ldquo;how many lines?&rdquo; but "
  "&ldquo;what threat model does it assume?&rdquo; Two blocks implementing the same "
  "standard under different threat models are different products.")

_("SHA-256 코어 (Verilog)",
  "SHA-256 with the compression function and the message schedule (W memory) as separate "
  "modules.",
  "<b>To show that a hash's message schedule is a block in its own right.</b> Each of the "
  "64 rounds consumes one W word, and the W words are generated recursively from earlier "
  "ones. Whether to expand all 64 in advance or to maintain a 16-word rotating buffer is "
  "a direct area&ndash;latency trade.",
  "Mapping a recurrence to hardware; circular buffers; area&ndash;time trade-offs.",
  "Read <code>sha256_w_mem.v</code> first. The 16-word rotating buffer idiom recurs in "
  "LDPC message storage, FFT delay lines and FIR delay chains; recognising it once makes "
  "all of them familiar.")

_("OpenTitan AES -- 양산 보안 RTL",
  "The AES block from a production security chip: cipher core, triplicated control FSMs, "
  "six S-box implementations, masking and clearing PRNGs, CTR and GCM support, shadowed "
  "registers, TL-UL interface.",
  "<b>It contains the entire difference between an AES that is functionally correct and "
  "one that can be shipped.</b> The algorithm is identical to the plain Verilog core. "
  "Everything else defends against power analysis, fault injection, misconfiguration and "
  "data remanence.",
  "Differential power analysis; threshold implementations and probing security; "
  "fault-tolerant design through complementary redundancy; CMOS switching energy "
  "<i>P</i>&nbsp;&prop;&nbsp;&alpha;<i>CV</i><sup>2</sup><i>f</i>.",
  "Open <code>aes_sbox_dom.sv</code> (1,077 lines) beside <code>aes_sbox_lut.sv</code> "
  "(120 lines). They compute the same mathematical function at nine times the size. "
  "<b>A functional regression cannot distinguish them</b> &mdash; which is precisely the "
  "boundary a modelling engineer must understand and state.")

_("OpenTitan HMAC-SHA256",
  "HMAC and SHA-256 combined in one block with a FIFO and a register interface.",
  "<b>Because the streaming interface, not the hash, is most of the work.</b> Message "
  "lengths are arbitrary and software delivers fragments, so the hardware must handle "
  "buffering, byte alignment, final-block padding, and suspend/resume.",
  "HMAC's ipad/opad construction; stream processing; backpressure; byte-enable handling.",
  "In most blocks the interface exceeds 70% of the code. Schedules that assume the "
  "algorithm is the work are systematically optimistic.")

_("OpenTitan KMAC (Keccak/SHA-3)",
  "SHA-3 family and KMAC built on the Keccak-f[1600] permutation.",
  "<b>Because its construction differs fundamentally from SHA-2.</b> It is a sponge, not "
  "a Merkle&ndash;Damg&aring;rd chain: a large state is stirred by a permutation while "
  "data is absorbed and squeezed. In hardware this becomes a 1600-bit register and very "
  "wide combinational logic.",
  "Sponge constructions; permutation-based cryptography; bit-slice implementation; "
  "routing congestion in wide datapaths.",
  "Keccak is a block where <b>wiring, not gate count, determines area</b>. If post-synthesis "
  "area greatly exceeds a gate-count estimate, congestion is usually the reason and RTL "
  "changes will not fix it. Include a routing factor in early estimates.")

_("OpenTitan CSRNG (SP800-90A)",
  "A CTR_DRBG deterministic random bit generator with arbitration among multiple requesters.",
  "<b>Because the standard prescribes a procedure, not merely an output.</b> "
  "Instantiate, reseed, generate and uninstantiate form a specified state machine with "
  "specified counter limits, and certification requires conformance to it.",
  "Pseudorandom versus cryptographically secure generation; forward and backward secrecy; "
  "entropy pool management; state machine design.",
  "Verification here means &ldquo;does it follow the specified procedure?&rdquo; The NIST "
  "CAVP vectors are effectively the specification. This is a block where inventiveness in "
  "the model is a liability rather than an asset.")

_("OpenTitan 엔트로피원 (SP800-90B)",
  "Extracts entropy from a physical noise source and runs continuous health tests on it.",
  "<b>Because a broken noise source that keeps producing output is worse than one that "
  "stops.</b> Physical sources can become stuck or biased, and keys derived from them "
  "would be predictable. The standard therefore mandates repetition-count and "
  "adaptive-proportion tests running at all times.",
  "Min-entropy as the security-relevant measure; statistical hypothesis testing; "
  "ring-oscillator jitter arising from thermal noise.",
  "<b>This block cannot be validated by simulation.</b> RTL verification covers the test "
  "logic; actual entropy quality is measured on silicon. A modelling engineer should state "
  "that boundary explicitly in the verification plan rather than let it be assumed away.")

_("OpenTitan OTBN -- 빅넘버 코프로세서",
  "A programmable coprocessor for wide-integer arithmetic, with its own instruction set, "
  "register file and modular multiplier.",
  "<b>Because public-key cryptography needs modular exponentiation on operands of "
  "hundreds or thousands of bits.</b> A general-purpose CPU is too slow; a fixed-function "
  "engine cannot follow algorithm changes such as curve replacement or the transition to "
  "post-quantum schemes.",
  "Modular arithmetic; Montgomery multiplication (modular reduction without division); "
  "constant-time implementation; instruction set design.",
  "Fixed-function versus programmable is a central IP business decision. <b>Where the "
  "standards move, programmability wins</b> &mdash; which is the situation in "
  "cryptography right now.")

_("SPI 호스트", "An SPI master: clock divider, CPOL/CPHA modes, FIFOs, segmented transfers.",
  "<b>Because it is the archetype of a block that looks trivial and has many variants.</b> "
  "Four clock modes, bit order, half- and full-duplex, dual and quad IO, and chip-select "
  "timing all differ between peripherals.",
  "Serial communication; clock phase and polarity; setup and hold margins; clock division.",
  "Most SPI field failures trace to CPOL/CPHA combinations or chip-select timing. A "
  "verification plan that does not exercise all four modes will leave one broken.")

_("I2C 컨트롤러", "An I2C controller supporting clock stretching, arbitration and multi-master operation.",
  "<b>Because I2C is an open-drain bidirectional bus</b>, which makes it unusual from a "
  "digital design viewpoint: targets may stretch the clock, and simultaneous masters must "
  "arbitrate. Neither behaviour fits a simple shift register.",
  "Open-drain / wired-AND signalling; bus arbitration; input filtering and debouncing.",
  "<b>Clock stretching is frequently unimplemented</b>, and that omission is a recurring "
  "field failure. Check for it in any I2C IP you evaluate, and state it explicitly in any "
  "you sell.")

_("UART", "An asynchronous serial transceiver with baud generation, oversampled receive, FIFOs and error flags.",
  "<b>Because it is the bring-up lifeline.</b> When a chip does not boot, the UART is "
  "often the only visible output, so it must be the simplest and most robust block on the die.",
  "Asynchronous communication; oversampling and majority voting; tolerance to clock "
  "frequency error (typically &plusmn;2%); framing errors.",
  "Compute and publish the baud-rate error for the intended system clocks. If the ratio is "
  "not close to integral, accumulated error drops bits near the end of a frame. A table of "
  "achievable baud rates and their errors is a mark of a well-documented UART.")

_("USB 디바이스", "A full-speed USB device controller: endpoints, packet handling, bus state machine.",
  "<b>Because it illustrates a deep protocol stack.</b> Above the differential signalling "
  "sit packets, transactions, transfers and enumeration, and deciding which layers are "
  "hardware and which are firmware is the principal architectural choice.",
  "Layered protocols; bit stuffing; NRZI encoding; clock recovery from SOF; CRC.",
  "State the hardware/firmware split in the datasheet. Without it, integrators assume the "
  "hardware performs enumeration and discover otherwise late.")

_("RISC-V 타이머", "The mtime/mtimecmp registers and timer interrupt generation.",
  "<b>Because the privileged specification defines its behaviour exactly</b>, leaving "
  "almost no implementation freedom. Verification reduces to conformance.",
  "Timers and counters; interrupt controllers; atomicity of wide counter reads.",
  "Reading a 64-bit counter over a 32-bit bus can tear if the value rolls over between the "
  "two halves. Either the read order is specified or a shadow register is required &mdash; "
  "a classic and easily missed defect.")

_("RISC-V 디버그 모듈", "A RISC-V debug module with JTAG transport and core control.",
  "<b>Because it is the only window into a chip that will not boot.</b> It must therefore "
  "operate while the core is halted, which usually places it in a separate clock and reset "
  "domain.",
  "JTAG TAP state machine (IEEE 1149.1); boundary scan; debug transport; clock domain crossing.",
  "Debug access crosses the security boundary. Production devices lock it according to "
  "life-cycle state. <b>The tension between debuggability and security is a design issue "
  "in every secure chip</b>, and the resolution must be specified, not improvised.")

_("TL-UL 버스 구조", "TileLink Uncached Lightweight adapters, sockets, FIFOs and error responders.",
  "<b>Because a common bus is what makes IP reuse practical.</b> One interface convention "
  "permits shared register generators, verification IP and address decoders across every "
  "peripheral.",
  "Bus protocols; handshaking; address decoding; arbitration; pipelining and throughput.",
  "Bus adapters are not free. For a small peripheral the adapter can exceed the function "
  "in area. <b>Resource reports should state whether the adapter is included.</b>")

_("SRAM 컨트롤러(스크램블)", "An SRAM controller that scrambles addresses and data and adds ECC.",
  "<b>Because secrets in memory can be read physically.</b> Decapsulating a die and probing "
  "SRAM cells is a practised attack, so contents are scrambled; independently, soft errors "
  "require ECC.",
  "Lightweight block ciphers (PRINCE and similar); SECDED Hamming codes; soft-error rate "
  "and FIT units.",
  "ECC adds a cycle of latency. Confirm early that the pipeline can absorb it; discovering "
  "this after timing closure forces a redesign.")

_("OTP 컨트롤러", "A controller for one-time-programmable memory.",
  "<b>Because some state must be unerasable</b>: device-unique keys, life-cycle state, "
  "trim values. Since writes are irreversible, the programming procedure is extremely "
  "conservative.",
  "Non-volatile memory physics (eFuse, antifuse); error correction; idempotent writes.",
  "A defect here produces permanently unusable devices. Verify this block more "
  "conservatively than any other.")

_("키 관리자", "Derives purpose-specific keys from a root key and gates access by life-cycle state.",
  "<b>To keep key material out of software entirely.</b> Software requests an operation "
  "with a named key; the value travels only over hardware paths to the crypto engines.",
  "Key derivation functions; chain of trust; least privilege; hardware isolation.",
  "Whether the hardware key path is genuinely isolated can only be established by reading "
  "the RTL: debug paths, scan chains and test modes are the usual leaks. <b>A scan chain "
  "can read every flip-flop</b>, which is why production parts lock scan.")

_("수명주기 컨트롤러",
  "Manages life-cycle state (RAW &rarr; TEST &rarr; DEV &rarr; PROD &rarr; RMA) and gates "
  "features accordingly.",
  "<b>Because some capabilities must exist in the factory and not in the field</b> &mdash; "
  "test modes, debug, key injection. Transitions are irreversible and authenticated by tokens.",
  "State machines; access control; irreversible transitions; fail-closed defaults.",
  "This block encodes product strategy in silicon. Which features are locked and when is a "
  "business decision, which makes it the block whose requirements change most often.")

_("OpenTitan 기본 셀 라이브러리",
  "Synchronisers, FIFOs, counters, LFSRs, arbiters, parity and ECC helpers, and security "
  "primitives such as duplicated registers and complementary signal pairs.",
  "<b>To get the subtle things right once.</b> A synchroniser written independently in "
  "every block will be wrong in at least one of them; written once and verified once, it "
  "is correct everywhere.",
  "Metastability and MTBF; Gray coding; LFSRs and primitive polynomials; arbitration fairness.",
  "<b>This library is the first thing a one-person IP house should build.</b> A block "
  "cannot be sold unless the primitives inside it are already trusted. OpenTitan's "
  "<code>prim_</code> modules are Apache-2.0 licensed and are a sound starting point.")

# --- remaining bundles -------------------------------------------------
_("Caliptra SHA-512", "SHA-512 from a datacentre root-of-trust design.",
  "<b>Because measurement of firmware needs a collision-resistant digest</b>, and SHA-512 "
  "is the width used for attestation in that ecosystem.",
  "Hash construction; 64-bit datapath arithmetic; message scheduling.",
  "Compare the round structure with the SHA-256 core: the same algorithmic shape at double "
  "width shows how word width propagates through a design.")

_("Caliptra SHA-256", "SHA-256 in a root-of-trust context.",
  "<b>Because the boot measurement chain requires it</b> and a root of trust cannot rely "
  "on software for its own integrity check.",
  "Hash functions; boot-time measurement; chain of trust.",
  "A root of trust is interesting less for its algorithms than for its <i>ordering</i> "
  "guarantees: what is measured before what, and what cannot be changed afterwards.")

_("Caliptra HMAC", "Keyed-hash message authentication in a root of trust.",
  "<b>Because integrity without authentication is insufficient</b>: a plain digest can be "
  "recomputed by an attacker who can modify the data.",
  "HMAC construction; key handling; constant-time comparison.",
  "Compare digests in constant time. A byte-by-byte comparison that returns early leaks "
  "the position of the first difference through timing &mdash; a classic and easily fixed "
  "vulnerability.")

_("Caliptra ECC (P-384)", "Elliptic-curve arithmetic over the NIST P-384 curve.",
  "<b>Because attestation requires digital signatures</b>, and ECC provides them at far "
  "smaller key sizes than RSA for equivalent classical security.",
  "Elliptic curve group law; modular arithmetic; Montgomery ladder for constant-time scalar "
  "multiplication; projective coordinates to avoid inversions.",
  "Scalar multiplication must be constant time and regular: any dependence of the operation "
  "sequence on secret scalar bits leaks the key. The Montgomery ladder exists for this "
  "reason, not for speed.")

_("Caliptra AES", "AES within a datacentre root of trust.",
  "<b>Because confidentiality is required alongside integrity</b>, and a root of trust must "
  "provide both without exporting keys.",
  "Block cipher modes; key hierarchies; hardware key paths.",
  "Compare this implementation's countermeasure set with OpenTitan's. Different threat "
  "models &mdash; a datacentre module versus a device exposed to physical attack &mdash; "
  "produce different designs from the same standard.")

_("PULP 기본 셀 (FIFO·CDC·아비터)",
  "The PULP platform's common cells: FIFOs, two-phase and Gray-coded CDC, round-robin "
  "arbiter trees, stream registers and spill registers.",
  "<b>Because every SoC needs them and getting them wrong is expensive.</b> The spill "
  "register in particular exists to break the combinational valid/ready loop that appears "
  "whenever two modules are connected directly.",
  "Metastability; Gray coding; handshake protocols; arbitration; pipeline decoupling.",
  "Read <code>cc_spill_register.sv</code> closely. It solves a problem &mdash; the "
  "zero-delay handshake cycle &mdash; that is invisible when each module is tested alone "
  "and appears immediately on integration.")

_("AXI4 상호연결", "AXI4 crossbars, multiplexers, demultiplexers, cuts and error slaves.",
  "<b>Because AXI is the de facto SoC interconnect</b>, and because its ordering rules "
  "&mdash; ordering guaranteed only within an ID &mdash; shape every verification component "
  "that touches it.",
  "Channel-based protocols; out-of-order completion; transaction identifiers; deadlock "
  "avoidance in interconnect.",
  "A scoreboard for AXI needs <b>one queue per ID</b>. A single queue both reports false "
  "failures on legal reordering and accepts genuine intra-ID violations.")

_("APB", "The APB peripheral bus.",
  "<b>Because not everything needs AXI.</b> Configuration registers and slow peripherals "
  "are better served by a simple non-pipelined bus, and bridging AXI to APB is standard practice.",
  "Simple bus protocols; address decoding; bridging between protocols.",
  "APB's simplicity is its value: a peripheral with an APB interface is trivial to verify "
  "and to integrate. Consider it for any block whose bandwidth is not the point.")

_("RISC-V 디버그", "The PULP RISC-V debug module.",
  "<b>Because debug must work when nothing else does</b>, which is why it is a separate "
  "module with its own transport and clocking.",
  "JTAG; debug transport modules; abstract commands; program buffers.",
  "Compare with the OpenTitan debug module: both implement the same specification with "
  "different structural choices, which is a useful exercise in reading two implementations "
  "of one document.")

_("CV32E40P RISC-V 코어",
  "A 32-bit RISC-V core with PULP extensions, taped out in several projects.",
  "<b>Because it is the design under test in the step-and-compare methodology</b> described "
  "in the verification chapters, and small enough to read completely.",
  "Pipelining; hazard detection and forwarding; exception handling; CSR implementation.",
  "Read the decode stage first, then the controller. Nearly all of a small core's "
  "complexity is in hazard and exception control, not in the datapath.")

_("CV32E40P RVFI 트레이스",
  "The RISC-V Formal Interface instrumentation for the core: retirement trace output.",
  "<b>Because model and RTL cannot be compared unless the RTL reports what it did.</b> "
  "This module exposes, per retired instruction, the PC, the instruction word, register "
  "reads and writes, memory accesses and traps.",
  "Observability; trace interfaces; instrumentation that does not alter behaviour.",
  "If your project lacks an equivalent interface, <b>building one is the highest-value "
  "first task</b> a new modelling engineer can undertake: nothing else in the comparison "
  "flow can exist without it.")

_("PicoRV32 -- 초소형 RISC-V", "A very small RISC-V core, widely used in FPGA designs.",
  "<b>Because it shows how little is needed for a working processor.</b> It trades cycles "
  "per instruction for area and is the clearest introduction to RISC-V RTL.",
  "Multi-cycle versus pipelined execution; area&ndash;performance trade-offs; simple bus interfaces.",
  "A good first core to read end to end. Understanding one complete core makes reading a "
  "complex one far easier.")

_("SERV -- 비트직렬 RISC-V", "A bit-serial RISC-V core &mdash; among the smallest in existence.",
  "<b>Because it demonstrates the extreme of the area&ndash;time trade.</b> Processing one "
  "bit per cycle makes the datapath almost disappear, at 32&times; the cycle count.",
  "Bit-serial arithmetic; area&ndash;time product; extreme resource constraint.",
  "Worth reading as an existence proof: many datapaths can be serialised when area matters "
  "more than latency, and the technique is under-used.")

_("형식검증된 AXI/Wishbone 브리지",
  "A bridge between Wishbone and AXI, developed with formal verification throughout.",
  "<b>Because a bus bridge is where protocol violations are introduced</b>, and because "
  "protocol conformance is exactly the kind of local, bounded property that formal methods "
  "settle completely.",
  "Formal property verification; protocol assertions; induction and bounded model checking.",
  "Read the assertions before the implementation. They are a precise, executable statement "
  "of the AXI rules and are more instructive than the protocol specification's prose.")

_("PCIe 코어", "PCIe interface logic: transaction layer, data link layer, DMA.",
  "<b>Because PCIe is the dominant system interconnect</b>, and because its layering shows "
  "how ordering rules, credit flow control and replay interact.",
  "Layered protocols; credit-based flow control; packet ordering rules; retry mechanisms.",
  "PCIe ordering rules (posted, non-posted, completion) are a frequent source of subtle "
  "bugs. They are worth studying as a specification-reading exercise in their own right.")

_("RVFI UVM 에이전트", "A UVM agent that monitors the RVFI interface and checks its properties.",
  "<b>Because the trace must be captured and checked, not merely emitted.</b> The agent "
  "turns retirement events into transactions a scoreboard can consume.",
  "UVM agent structure (driver, monitor, sequencer); transaction-level modelling; assertions.",
  "This is the bridge between the RTL's observability and the comparison logic. Studying it "
  "shows concretely how a verification environment is layered.")

_("step-compare 테스트벤치",
  "The testbench that steps a reference ISS and the RTL core together and compares "
  "architectural state after every retired instruction.",
  "<b>Because it is the operational definition of a bug</b> in a CPU project: model and "
  "design disagree. It compares the PC, all 32 general-purpose registers and the CSRs.",
  "Reference-model comparison; scoreboarding; masking of implementation-defined state.",
  "Read the comments. One records that static register checks were disabled because bus "
  "stalls made them fail &mdash; a real engineering compromise between coverage and "
  "usability, documented in place. <b>That is what honest verification code looks "
  "like.</b>")

_("Spike ISS -- 참조모델 본체",
  "The core of the RISC-V reference simulator: decoder, execution, CSRs, MMU, and one "
  "small file per instruction.",
  "<b>Because it is the canonical example of how a reference model should be organised.</b> "
  "Instruction semantics live in individual files; state access is hidden behind macros; "
  "the decoder is table-driven. Extensions are additive.",
  "Instruction set semantics; interpreter design; privilege and virtual memory modelling.",
  "Adopt this structure. A model that grows by adding files rather than by editing a "
  "growing switch statement remains maintainable after fifty extensions.")

_("Berkeley SoftFloat",
  "A bit-exact software implementation of IEEE 754 arithmetic.",
  "<b>Because host floating point cannot be used in a reference model.</b> Rounding modes, "
  "exception flags, subnormals and NaN propagation must match the specification exactly, "
  "and they must not vary with the machine running the simulation.",
  "IEEE 754 semantics; rounding modes; exception flags; subnormal handling.",
  "If you are handed a floating-point block to model, the first question is whether the "
  "existing model uses host arithmetic. If it does, the model is machine-dependent and "
  "every correctness claim made with it is provisional.")

_("RISC-V 형식 명세 (Sail)",
  "The RISC-V architecture written in Sail, a specification language from which both prose "
  "and an executable emulator are generated.",
  "<b>Because it removes the gap between the document and the model.</b> When the "
  "specification is executable, the reference implementation cannot drift from it.",
  "Formal semantics; specification languages; generated implementations.",
  "This is the strongest available answer to the independence problem described in the "
  "verification chapters: rather than hoping two readers interpret a document identically, "
  "make the document itself executable.")

_("플래시 컨트롤러", "The flash controller's interface logic.",
  "<b>Because embedded flash holds the code that runs before anything else.</b> Its "
  "controller therefore participates in secure boot: it must enforce read/write/erase "
  "permissions per region and cooperate with the life-cycle state.",
  "Non-volatile memory programming; wear levelling; region-based access control; "
  "integrity checking of stored code.",
  "Flash operations are slow and blocking relative to the CPU, so the controller's "
  "interface must allow the core to make progress. The resulting concurrency &mdash; "
  "erase in progress while reads continue from another bank &mdash; is where the "
  "verification effort concentrates.")

_("MIPI CSI-2 수신기 -- 패킷 디코더 · 레인 정렬 · RAW 언팩",
  "A working MIPI CSI-2 receiver in Verilog: byte and lane aligners, the packet decoder, "
  "RAW8/10/12 depackers, an output reformatter, and a debayer filter.",
  "<b>Because it is the concrete form of every block named in Chapter P1.</b> Reading "
  "<code>mipi_rx_lane_aligner.v</code> alongside the description of lane deskew, and "
  "<code>mipi_rx_raw12_depacker.v</code> alongside the explanation of RAW packing, turns "
  "an abstract block diagram into something that can be modified.",
  "Packet framing and synchronisation; ECC and CRC; bit-packing and unpacking; "
  "multi-lane deskew; line buffering for neighbourhood operations.",
  "Start with <code>mipi_rx_raw_depacker.v</code>. The bit-slicing there is exactly the "
  "part that Chapter P1 identifies as where verification effort concentrates, and seeing "
  "how few lines it takes &mdash; and how many ways it can be wrong &mdash; makes the "
  "point better than any description.")

_("MIPI CSI-2 수신기 (1세대)",
  "An earlier generation of the same receiver, targeting a different FPGA family.",
  "<b>Because comparing two implementations of one specification is instructive.</b> The "
  "differences show which parts are forced by the standard and which are choices &mdash; "
  "the distinction a specification writer must be able to make.",
  "Design portability; the boundary between specification and implementation.",
  "A useful exercise: list the differences between the two versions and classify each as "
  "required by the standard, forced by the target device, or a free choice. That "
  "classification is the substance of a good specification document.")

_("이더넷 MAC · 10G BASE-R PCS · XGMII/GMII",
  "A widely used open Ethernet implementation: 1G and 10G MACs, the 10G BASE-R PCS "
  "(64b/66b encode and decode, block synchronisation, BER monitor), and the GMII/XGMII "
  "interface adapters.",
  "<b>Because it is the reference point for Chapter P3.</b> It shows what a complete MAC "
  "contains, and &mdash; equally usefully &mdash; what it does not: there is no RS-FEC and "
  "no 100G multi-lane PCS here, which is precisely the gap a new IP could fill.",
  "Framing; CRC-32; inter-frame gap; 64b/66b line coding; scrambling for DC balance; "
  "block synchronisation state machines.",
  "Read <code>xgmii_baser_enc_64.v</code> and <code>xgmii_baser_dec_64.v</code> together "
  "with Chapter K2's account of 64b/66b. The two-bit sync header and the block type field "
  "are visible directly in the code, and the scrambler is in <code>lfsr.v</code> &mdash; "
  "the same LFSR structure that Chapter Z3 introduces as CRC, PRBS and scrambler at once.")

_("PCIe 코어 (추가)",
  "Additional PCIe interface logic: transaction handling and DMA.",
  "<b>Because Chapter P2 describes the layering abstractly and this shows the transaction "
  "layer as code.</b> DMA and descriptor handling, in particular, are where the "
  "throughput analysis of that chapter becomes concrete.",
  "Layered protocols; credit-based flow control; descriptor rings; DMA engines.",
  "Trace how outstanding requests are tracked. Chapter P2 argues that tag capacity rather "
  "than link width limits read throughput; the tag management logic here is where that "
  "limit physically lives.")
