# PetroTechRadar Methodology

PetroTechRadar combines technical curation with live repository metrics. Popularity is useful, but it is not treated as a proxy for engineering value.

## Repository ranking

The current repository score combines:
- Curated technical tier: 70%
- GitHub activity signal: 30%

GitHub activity uses log-scaled stars/forks plus development recency and issue activity.

## Papers with Code ranking

| Factor | Weight |
|---|---:|
| Technical relevance | 20% |
| Reproducibility | 20% |
| Code health | 15% |
| Journal / venue quality | 10% |
| Total citations | 15% |
| Citations/year | 10% |
| GitHub traction | 10% |

Citation counts are sourced from OpenAlex and are age-normalized using citations/year.

## Validation

Before public promotion, entries should be checked for:
- substantive code
- correct repository identity
- fork/duplicate status
- license
- recent activity
- domain relevance
- documentation quality
- reproducibility where applicable
