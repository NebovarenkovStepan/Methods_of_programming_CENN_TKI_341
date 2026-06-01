# Role Policy Matrix

Матрица фиксирует разрешенные действия в strict-режиме (role -> action).

## Portal

| Action | admin | doctor | registrar | patient | guest |
| --- | --- | --- | --- | --- | --- |
| `patient:create` | allow | allow | allow | deny | deny |
| `card:create` | deny | allow | deny | deny | deny |
| `appointment:create` | allow | allow | allow | deny | deny |
| `investigation:create` | deny | allow | deny | deny | deny |
| `prescription:create` | deny | allow | deny | deny | deny |

## Pharmacy

| Action | admin | pharmacist | scanner | doctor | patient | guest |
| --- | --- | --- | --- | --- | --- | --- |
| `prescription:read` | allow | allow | deny | allow | deny | deny |
| `scanner:prescription` | allow | allow | allow | deny | deny | deny |
| `scanner:medicine` | allow | allow | allow | deny | deny | deny |
| `prescription:dispense` | allow | allow | deny | deny | deny | deny |

## Laboratory

| Action | admin | lab_tech | tech | doctor | patient | guest |
| --- | --- | --- | --- | --- | --- | --- |
| `investigation:list_ordered` | allow | allow | deny | allow | deny | deny |
| `investigation:read` | allow | allow | deny | allow | deny | deny |
| `sample:register` | allow | allow | deny | deny | deny | deny |
| `sample:to_storage` | allow | allow | deny | deny | deny | deny |
| `sample:to_analysis` | allow | allow | deny | deny | deny | deny |
| `analyzer:create` | allow | deny | allow | deny | deny | deny |
| `workstation:create` | allow | deny | allow | deny | deny | deny |
| `analyzer_result:create` | allow | allow | deny | deny | deny | deny |
| `investigation:complete` | allow | allow | deny | allow | deny | deny |
| `equipment:create` | allow | deny | allow | deny | deny | deny |
| `monitoring:add_metric` | allow | deny | allow | deny | deny | deny |
| `diagnostic:add` | allow | deny | allow | deny | deny | deny |

## LLM

| Action | admin | doctor | lab_tech | patient | staff | guest |
| --- | --- | --- | --- | --- | --- | --- |
| `llm:generate_report` | allow | allow | allow | deny | deny | deny |
| `llm:read_reports` | allow | allow | deny | allow | deny | deny |
