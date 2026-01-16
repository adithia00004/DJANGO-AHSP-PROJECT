# Monitoring Dashboard Plan

## Proposed Metrics

| Panel | Metric | Source | Alert Threshold |
|-------|--------|--------|-----------------|
| Slow Requests | Count of `performance` logger entries (per minute) | Log sink / Loki | > 5/min |
| Error Rate | 5xx responses per minute | Application logs | > 5% |
| DB Connections | Active connections | PgBouncer / PostgreSQL | > 80% pool usage |
| Cache Hit Ratio | Hits vs misses | Cache backend (DB stats) | Hit ratio < 70% |

## Tools

- Grafana (preferred) or any log analytics tool.
- Pipeline suggestion: Fluent Bit → Loki → Grafana.

## Setup Steps

1. Stream JSON logs to the monitoring stack.
2. Create Grafana dashboard using table above.
3. Wire alerting to Slack/Email for thresholds.
