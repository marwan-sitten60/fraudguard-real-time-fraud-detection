# Phase 3: offline model baseline

The offline workflow uses `fraudguard-handbook-baseline-v1` and the centralized
`fraud-features-v1` contract. It is deliberately separate from API serving: the API
continues to load `mock-v1`.

Rows are sorted by `(event_time, transaction_id)`. Each feature row is emitted before
customer and merchant state is updated, so neither its own label nor later transactions
can affect it. Merchant fraud features use prior labels as if they were immediately
available after a transaction. This is a public-benchmark simplification, not a
production label-availability policy.

Training uses train data, selects an operating threshold on validation data only, and
evaluates the frozen choice once on test. Accuracy is not a quality target because the
natural fraud prevalence is below one percent. MLflow experiment `FraudGuard-Baseline`
records parameters, metrics, candidate artifact, feature list, and evaluation report.

Run an offline candidate with:

```powershell
python -m fraudguard.training --data-directory data/processed/fraudguard-handbook-baseline-v1 --model xgboost
```

The command is offline-only. It does not register, deploy, or serve the model.
