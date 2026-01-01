# Ivy House｜Meta 週會 MVP (Streamlit)

## What this repo is
- Streamlit app for weekly Meta report ingestion (Adset CSV + Ad CSV + Web Excel)
- Step B produces `report_summary.json` and **forces schema validation** using `schemas/report_summary.v1.json`
- Validation errors are logged into `pipeline_state.json` with event step `B(validate_error)`


## Run app
```bash
streamlit run app.py
