# meditopia-cli

The official CLI for [Meditopia](https://meditopia.ai) — push clinical AI models and datasets from your terminal.

## Install

```bash
pip install meditopia-cli
```

## Quick start

```bash
# Authenticate once
medi login --token mtc_xxxxxxxxxxxxxxxx

# Upload a dataset
medi add dataset ./my-data \
  --to pedram/chest-xray-nih \
  --modality imaging \
  --privacy public

# Upload a model
medi add model ./weights/ \
  --to pedram/chexnet \
  --task radiology \
  --framework pytorch \
  --auc 0.89
```

See the [full documentation](https://meditopia.ai/docs/cli) for all options.
