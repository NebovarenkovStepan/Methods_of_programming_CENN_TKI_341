# Negative Scenarios Matrix (НС-1..НС-33)

| НС | Статус | Тест/файл |
|---|---|---|
| НС-1 | covered | `test_hc01_emk_read_without_authorization` (`test/test_system_scenarios.py`) |
| НС-2 | covered | `test_hc20_existing_emk_record_can_be_changed_without_authorized_doctor` + `TestHC19...` |
| НС-3 | covered | `test_hc03_unprotected_data_transfer_simulation` |
| НС-4 | covered | `test_hc04_tampered_api_payload_accepted` |
| НС-5 | partial | `test_hc10_non_authentic_data_in_workflow` |
| НС-6 | covered | `test_hc06_sql_injection_like_input_accepted` |
| НС-7 | partial | `test_hc31_video_session_can_be_started_without_authorized_doctor` |
| НС-8 | partial | `TestHC19CreateCard...` |
| НС-9 | partial | `test_hc15_investigation_to_analysis_workflow_unauthorized_lab` |
| НС-10 | covered | `test_hc10_tampered_analyzer_result_is_accepted` |
| НС-11 | missing | - |
| НС-12 | covered | `test_hc13_get_investigation_by_id_unauthorized_user` |
| НС-13 | covered | `test_hc13_get_ordered_investigations_unauthorized_user` |
| НС-14 | covered | `test_hc15_complete_investigation_unauthorized_lab` |
| НС-15 | covered | `TestHC29ScanPrescription...` |
| НС-16 | partial | via dispense conflict tests (non-HC) |
| НС-17 | missing | - |
| НС-18 | covered | `TestHC18CreatePrescription...` |
| НС-19 | covered | `TestHC19CreateCard...` |
| НС-20 | covered | `test_hc20_existing_emk_record_can_be_changed_without_authorized_doctor` |
| НС-21 | missing | - |
| НС-22 | covered | `test_hc22_replay_attack_simulation` |
| НС-23 | covered | `test_hc13_get_ordered_investigations_unauthorized_user` |
| НС-24 | covered | `test_hc24_emk_access_bypass_in_workflow` |
| НС-25 | missing | - |
| НС-26 | missing | - |
| НС-27 | covered | `TestHC29ScanPrescription...` |
| НС-28 | covered | `TestHC30GetPrescription...` |
| НС-29 | covered | `test_hc31_video_session_can_be_started_without_authorized_doctor` |
| НС-30 | covered | `TestHC34CreateInvestigation...` (needs rename to HC30/НС30 alignment) |
| НС-31 | covered | `test_hc31_video_session_can_be_started_without_authorized_doctor` |
| НС-32 | covered | `TestHC34CreateInvestigation...` |
| НС-33 | covered | `test_hc33_backup_data_exposure_simulation` |

