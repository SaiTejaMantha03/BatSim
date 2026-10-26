# BattSimulator (TeamTitans, Tata Elxsi TELIPORT Season 4, Case Study 2)

Virtual design tool for a 48 V light-EV battery module. It compares cell chemistry, S x P layout and cooling
at a 1 kW constant-power load and 35 C ambient, and flags any design that exceeds 45 C or the cell current rating.

## Files
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

## Limits
Calibrated on one 18650 NMC cell; applying it to the 21700 NMC and 32700 LFP cells is an assumption.
Assumed (not measured): natural-air heat transfer (8 W/m2K), exposed area fraction (0.4), PCM properties, LFP cell mass (140 g) and current rating (6 A).
No module-level lab tests yet.
