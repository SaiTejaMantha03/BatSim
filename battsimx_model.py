"""
BattSimX Studio - Phase 1 module model (reproducible).
Run:  python3 battsimx_model.py
Compares a baseline 48 V light-EV module against two options at a fixed
1 kW constant-power discharge, 35 C ambient. Lumped, per-cell thermal model.

DATA SOURCES (cell values)
  NMC  Samsung INR21700-50E datasheet: 4.9 Ah std capacity, 3.63 V nominal,
       69.5 g max, 14 mOhm AC impedance @1 kHz, 9.8 A max continuous.
  LFP  Generic 32700 6.0 Ah / 3.2 V / <10 mOhm AC listing (HX IFR32700).
       Mass NOT listed -> ASSUMED 140 g. Diameter ASSUMED 32 mm, length 70.5 mm.
       Max continuous NOT listed -> ASSUMED 1C = 6 A.
  Cost BNEF 2025 survey averages: LFP pack $81/kWh, NMC pack $128/kWh.

CALIBRATION (from the Panasonic 18650PF drive-cycle fit, train_validate notebook, 37 files, DOI 10.17632/wykht8y7tg.1)
  - Fitted DC resistance at 25 C = 31.05 mOhm; the PF datasheet AC impedance = 21 mOhm  ->  DC/AC factor = 1.48
    (replaces the earlier assumed 2.0).  Applied to the 21700 NMC and 32700 LFP cells.
  - Fitted heat transfer hA = 0.0879 W/K on the 18650PF lateral area pi*0.0185*0.0653 = 0.00380 m2
    -> h = 23.2 W/m2K for a lone cell in moving chamber air.  Used as the FORCED-AIR coefficient.
  - Resistance rises when cold (fitted k = 0.039 /C) but is NOT extrapolated above 25 C: the design runs are at
    35 C and above, so R is held at its 25 C value (conservative).  Natural-air h is NOT calibrated.

ASSUMPTIONS (all flagged; see sensitivity table for ranges)
  - Chemistry transfer: the NMC-derived DC/AC factor is also applied to the LFP cell (not validated).
  - Mean-voltage model: V_cell = V_nom - I*R (no OCV curve, no SoC dependence).
  - Heat = I^2 * R only (no entropic term); R constant with temperature.
  - Cell lumped to one temperature; cp = 900 J/kgK (NMC), 1000 J/kgK (LFP).
  - Only a fraction of each cell's side area sees the air (module packing).
  - Natural convection h = 8 W/m2K (assumed); forced air h = 23.2 W/m2K (calibrated, see above).
  - PCM: paraffin-type, melts 38-43 C, latent 165 kJ/kg, cp 2.0 kJ/kgK,
    sized to 2x total cell heat over the discharge, perfect contact (optimistic).
  - Module overhead (frame, busbars, BMS) = 15 % of cell mass.
  - Cooling hardware: forced air +0.5 kg, +$10; PCM $6/kg.
"""
import json, itertools

LIMIT_T = 45.0   # C, requirement
T_AMB = 35.0     # C
P_LOAD = 1000.0  # W, constant power

NMC = dict(name="NMC 21700", Ah=4.9, Vnom=3.63, mass=0.0695, R_ac=0.014,
           I_max=9.8, d=0.02125, L=0.0708, cp=900.0, usd_kwh=128.0)
LFP = dict(name="LFP 32700", Ah=6.0, Vnom=3.2, mass=0.140, R_ac=0.010,
           I_max=6.0, d=0.032, L=0.0705, cp=1000.0, usd_kwh=81.0)

DESIGNS = [
    dict(key="Baseline", label="14S4P NMC, natural air", cell=NMC, Ns=14, Np=4, cooling="air"),
    dict(key="Opt A",    label="14S4P NMC, forced air",  cell=NMC, Ns=14, Np=4, cooling="forced"),
    dict(key="Opt B",    label="16S4P LFP, PCM",         cell=LFP, Ns=16, Np=4, cooling="pcm"),
    dict(key="Opt C",    label="14S4P NMC, PCM",         cell=NMC, Ns=14, Np=4, cooling="pcm"),
]

DEFAULT = dict(r_mult=1.48, h_nat=8.0, h_forced=23.2, expose=0.4, pcm_factor=2.0)


def run(d, p=DEFAULT):
    c = d["cell"]; Ns, Np = d["Ns"], d["Np"]
    P_LOAD_, T_AMB_ = p.get("load", P_LOAD), p.get("amb", T_AMB)
    n = Ns * Np
    R = c["R_ac"] * p["r_mult"]
    # constant power: P = n * Ic * (Vnom - Ic*R)  -> solve quadratic for Ic
    a, b, cc = R, -c["Vnom"], P_LOAD_ / n
    Ic = (-b - (b * b - 4 * a * cc) ** 0.5) / (2 * a)
    t_end = c["Ah"] * 3600.0 / Ic                    # s, discharge duration
    E_wh = P_LOAD_ * t_end / 3600.0                   # delivered energy
    q_cell = Ic ** 2 * R                             # W per cell
    area = 3.141593 * c["d"] * c["L"] * p["expose"]  # m2 effective
    h = p["h_forced"] if d["cooling"] == "forced" else p["h_nat"]
    hA = h * area
    m_cell = c["mass"]
    m_pcm = 0.0
    if d["cooling"] == "pcm":
        m_pcm = p.get("pcm_factor", 2.0) * q_cell * t_end / 165e3   # kg per cell (default: 2x the cell heat)
    # explicit time stepping, enthalpy method for PCM
    T, dt, peak, t = T_AMB_, 1.0, T_AMB_, 0.0
    while t < t_end:
        cp_pcm = 2000.0 + (165e3 / 5.0 if 38.0 <= T <= 43.0 else 0.0)
        C = m_cell * c["cp"] + m_pcm * cp_pcm
        T += (q_cell - hA * (T - T_AMB_)) / C * dt
        peak = max(peak, T); t += dt
    cell_mass = n * m_cell
    mass = cell_mass * 1.15 + n * m_pcm
    mass += 0.5 if d["cooling"] == "forced" else 0.0
    E_nom_kwh = n * c["Ah"] * c["Vnom"] / 1000.0
    cost = E_nom_kwh * c["usd_kwh"]
    cost += 10.0 if d["cooling"] == "forced" else 0.0
    cost += 6.0 * n * m_pcm if d["cooling"] == "pcm" else 0.0
    return dict(label=d["label"], Vnom=Ns * c["Vnom"], cells=n,
                I_cell=Ic, c_rate=Ic / c["Ah"], I_ok=Ic <= c["I_max"],
                hours=t_end / 3600.0, E_wh=E_wh, E_nom_kwh=E_nom_kwh,
                peak_T=peak, T_ok=peak <= LIMIT_T, mass=mass, pcm_kg=n * m_pcm,
                wh_per_kg=E_wh / mass, cost_usd=cost, cost_per_kwh=cost / (E_wh / 1000.0))


def sensitivity(d):
    lo, hi = 1e9, -1e9
    for rm, hn, hf, ex in itertools.product((1.2, 1.8), (5.0, 10.0), (16.0, 30.0), (0.3, 0.5)):
        T = run(d, dict(r_mult=rm, h_nat=hn, h_forced=hf, expose=ex))["peak_T"]
        lo, hi = min(lo, T), max(hi, T)
    return lo, hi


if __name__ == "__main__":
    res = {}
    base_cpk = None
    print(f"Load: {P_LOAD:.0f} W constant power, ambient {T_AMB:.0f} C, limit {LIMIT_T:.0f} C\n")
    for d in DESIGNS:
        r = run(d); r["sens_T"] = sensitivity(d); res[d["key"]] = r
    base = res["Baseline"]["cost_per_kwh"]
    for k, r in res.items():
        r["cost_vs_base_pct"] = (r["cost_per_kwh"] / base - 1) * 100
        verdict = "PASS" if (r["T_ok"] and r["I_ok"]) else "FAIL"
        r["verdict"] = verdict
        print(f"{k:9s} {r['label']:24s} V={r['Vnom']:.1f}  cells={r['cells']}  "
              f"I={r['I_cell']:.2f} A ({r['c_rate']:.2f}C, limit ok={r['I_ok']})  "
              f"t={r['hours']:.2f} h")
        print(f"          E={r['E_wh']:.0f} Wh  Wh/kg={r['wh_per_kg']:.0f}  mass={r['mass']:.2f} kg "
              f"(PCM {r['pcm_kg']:.2f} kg)  peakT={r['peak_T']:.1f} C "
              f"[range {r['sens_T'][0]:.0f}-{r['sens_T'][1]:.0f}]  "
              f"$/kWh={r['cost_per_kwh']:.0f} ({r['cost_vs_base_pct']:+.1f}%)  -> {verdict}\n")
    json.dump(res, open("results.json", "w"), indent=2)
