# BattSimulator (TeamTitans, Tata Elxsi TELIPORT Season 4, Case Study 2)

Virtual design tool for a 48 V light-EV battery module. It compares cell chemistry, S x P layout and cooling
at a 1 kW constant-power load and 35 C ambient, and flags any design that exceeds 45 C or the cell current rating.

## Run the simulator
```
pip install -r requirements.txt
python app.py        # open http://127.0.0.1:5000
python battsimx_model.py   # print the comparison table only
```

## Files
- `app.py` : web interface (Flask) on the same model: pick cell, S x P, cooling, load, ambient, PCM size.
- `battsimx_model.py` : electro-thermal design model. Run `python battsimx_model.py` to print the results table and write `results.json`.
- `BattSimX_train_validate.ipynb` : Colab notebook that downloads the Panasonic 18650PF dataset, calibrates the model and tests it on unseen data.
- `results/` : metrics, per-file errors, train/test split and the held-out plot from our run.

## Data
- Cell values: Samsung INR21700-50E datasheet, 32700 LFP datasheet, BNEF 2025 battery price survey (links on the slide).
- Training/validation data: Panasonic 18650PF Li-ion Battery Data (P. Kollmeyer), Mendeley Data, DOI 10.17632/wykht8y7tg.1
  https://data.mendeley.com/datasets/wykht8y7tg  (licence field blank: cite when used).

## Validation result (from `results/metrics.json`)
Trained on drive cycles at 25, 10, 0 and -10 C (37 files); tested on 9 unseen drive-cycle files at -20 C.
RMSE: physics model 0.97 C, physics + ML correction 0.82 C, "no temperature change" baseline 28.1 C. Max error 4.4 C (physics).
The whole-test RMSE includes the 2-hour rest/cool-down at the start of each file, which is easy to predict, so it flatters the number.

## Designs compared (1 kW, 35 C; `python battsimx_model.py`, checked by `python test_model.py`)
| Design | Peak T (range over assumptions) | Mass | $/kWh | Verdict |
|---|---|---|---|---|
| Baseline 14S4P NMC, natural air | 55.0 (48-65) | 4.48 kg | 132 | FAIL |
| Opt A 14S4P NMC, forced air | 46.1 (41-56) | 4.98 kg | 142 | FAIL |
| Opt B 16S4P LFP, PCM | 39.0 (38.6-39.3) | 11.54 kg | 89 | PASS |
| Opt C 14S4P NMC, PCM | 39.6 (39.3-39.8) | 5.73 kg | 140 | PASS |
| (Opt B without PCM) | 43.2 (40.6-46.9) | 10.3 kg | 83 | marginal, fails worst case |

$/kWh is per delivered kWh. Total module cost: Opt B $107 vs baseline $127.5 (-16%); Opt B delivers 24% more energy.
PCM is sized as a multiple of the cell heat, so its small range is partly by construction (see PCM sensitivity).

## Limits
The 0.97 C RMSE is pooled over all test points including the 2-hour rest period at the start of each file; per-file physics RMSE ranges 0.51-1.49 C.

Calibrated on one 18650 NMC cell; applying it to the 21700 NMC and 32700 LFP cells is an assumption.
Assumed (not measured): natural-air heat transfer (8 W/m2K), exposed area fraction (0.4), PCM properties, LFP cell mass (140 g) and current rating (6 A).
No module-level lab tests yet.

## PCM sensitivity (Opt B, 16S4P LFP, 1 kW, 35 C; simulated)
PCM sized as a multiple of the cell heat over the discharge (default 2x = 1.24 kg):
0.25x 41.5 C | 0.5x 40.6 C | 1x 39.7 C | 2x 39.0 C. Without PCM (natural air): 43.2 C (range 41-47 C over the assumption ranges), i.e. thin margin.
PCM contact is assumed perfect, so these are optimistic.
