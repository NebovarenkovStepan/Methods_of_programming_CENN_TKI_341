"""
Tests for laboratory services based on security goals.
Negative scenarios are intentionally vulnerable to demonstrate security issues.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lis.service import LISService
from sample_storage.service import SampleStorageService
from analyzers.service import AnalyzerService
from workstations.service import WorkstationService
from med_equipment.service import MedicalEquipmentService
from monitoring.service import MonitoringService
from self_diagnostics.service import SelfDiagnosticsService


class TestLISService:
    """Tests for LIS Service - Security Goal 2: Only authorized laboratory can transmit data analysis"""
    
    def setup_method(self):
        self.lis_service = LISService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Goal 1 - Authorized users can read EMK data
    def test_get_ordered_investigations_authorized_user(self):
        """Test that authorized user can retrieve ordered investigations"""
        expected_investigations = [
            {
                'id': 1,
                'patient_id': 1,
                'card_id': 1,
                'test_name': 'Blood Test',
                'status': 'ORDERED',
                'results': None,
                'date_ordered': '2026-04-25',
                'date_completed': None
            }
        ]
        
        self.mock_cursor.fetchall.return_value = [
            (1, 1, 1, 'Blood Test', 'ORDERED', None, '2026-04-25', None)
        ]
        
        # Mock dict conversion
        with patch('lis.service.fetch_all') as mock_fetch:
            mock_fetch.return_value = expected_investigations
            result = self.lis_service.get_ordered_investigations(self.mock_conn)
            assert result == expected_investigations
            self.mock_cursor.execute.assert_called_once()
    
    # NEGATIVE: HC-2 - Unauthorized user should not access data
    # This test demonstrates vulnerability - no authorization check
    def test_get_ordered_investigations_unauthorized_user(self):
        """Test vulnerability: unauthorized user can access investigations (no auth check)"""
        self.mock_cursor.fetchall.return_value = [
            (1, 1, 1, 'Blood Test', 'ORDERED', None, '2026-04-25', None)
        ]
        
        with patch('lis.service.fetch_all') as mock_fetch:
            mock_fetch.return_value = [{'id': 1}]
            # VULNERABLE: No authorization verification - any user can call this
            result = self.lis_service.get_ordered_investigations(self.mock_conn)
            assert result is not None  # Should be restricted but isn't
    
    # POSITIVE: Goal 9 - Authorized doctor gets access to patient EMK
    def test_get_investigation_by_id_authorized_doctor(self):
        """Test authorized doctor can retrieve specific investigation"""
        investigation_id = 1
        expected = {
            'id': 1,
            'patient_id': 1,
            'card_id': 1,
            'test_name': 'Blood Test',
            'status': 'ORDERED',
            'results': None,
            'date_ordered': '2026-04-25',
            'date_completed': None
        }
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.lis_service.get_investigation(self.mock_conn, investigation_id)
            assert result == expected
            self.mock_cursor.execute.assert_called_once()
    
    # NEGATIVE: HC-3 - Unauthorized access to investigation data
    def test_get_investigation_by_id_unauthorized_doctor(self):
        """Test vulnerability: any doctor can access any patient investigation (no access control)"""
        investigation_id = 1
        patient_id = 999  # Different patient
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'patient_id': patient_id}
            # VULNERABLE: No check if doctor is authorized for this patient
            result = self.lis_service.get_investigation(self.mock_conn, investigation_id)
            assert result is not None  # Should verify doctor-patient relationship
    
    # POSITIVE: Goal 4 - Only authorized doctor can write new EMK data
    def test_complete_investigation_authorized_doctor(self):
        """Test authorized doctor can complete investigation with results"""
        investigation_id = 1
        results = "Normal blood count"
        expected = {
            'id': 1,
            'patient_id': 1,
            'status': 'COMPLETED',
            'results': results,
            'date_completed': '2026-04-25'
        }
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.lis_service.complete_investigation(
                self.mock_conn, 
                investigation_id, 
                results
            )
            assert result['status'] == 'COMPLETED'
            assert result['results'] == results
    
    # NEGATIVE: HC-4 - Unauthorized user can write EMK data
    def test_complete_investigation_unauthorized_user(self):
        """Test vulnerability: non-doctor can complete investigation (no role check)"""
        investigation_id = 1
        fake_results = "INJECTED MALICIOUS DATA"
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'results': fake_results}
            # VULNERABLE: No verification that user is doctor
            result = self.lis_service.complete_investigation(
                self.mock_conn,
                investigation_id,
                fake_results
            )
            assert result['results'] == fake_results  # Data was modified without authorization


class TestSampleStorageService:
    """Tests for Sample Storage Service - Security Goal 2: Only authorized lab transmits analysis"""
    
    def setup_method(self):
        self.storage_service = SampleStorageService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Goal 6 - Only authorized lab can transmit patient analyses
    def test_register_sample_authorized_lab(self):
        """Test authorized laboratory can register sample"""
        investigation_id = 1
        sample_type = "blood"
        storage_location = "freezer_A"
        expected = {
            'id': 1,
            'investigation_id': investigation_id,
            'sample_type': sample_type,
            'storage_location': storage_location,
            'status': 'REGISTERED'
        }
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.storage_service.register_sample(
                self.mock_conn,
                investigation_id,
                sample_type,
                storage_location
            )
            assert result['status'] == 'REGISTERED'
    
    # NEGATIVE: HC-6 - Unauthorized lab can register samples
    def test_register_sample_unauthorized_lab(self):
        """Test vulnerability: unauthorized entity can register samples (no lab verification)"""
        investigation_id = 1
        sample_type = "blood"
        # VULNERABLE: No check if requester is authorized laboratory
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'status': 'REGISTERED'}
            result = self.storage_service.register_sample(
                self.mock_conn,
                investigation_id,
                sample_type
            )
            assert result['status'] == 'REGISTERED'  # Should fail but succeeds
    
    # POSITIVE: Goal 6 - Lab can move samples through stages
    def test_move_sample_to_storage_authorized_lab(self):
        """Test lab can move sample to storage"""
        investigation_id = 1
        expected = {
            'id': 1,
            'investigation_id': investigation_id,
            'status': 'IN_STORAGE'
        }
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.storage_service.move_sample_to_storage(
                self.mock_conn,
                investigation_id
            )
            assert result['status'] == 'IN_STORAGE'
    
    # NEGATIVE: HC-6 - Unauthorized user can move samples
    def test_move_sample_to_storage_unauthorized_user(self):
        """Test vulnerability: non-lab user can move samples (no access control)"""
        investigation_id = 1
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'status': 'IN_STORAGE'}
            # VULNERABLE: No authorization check for who moves samples
            result = self.storage_service.move_sample_to_storage(
                self.mock_conn,
                investigation_id
            )
            assert result['status'] == 'IN_STORAGE'
    
    # POSITIVE: Lab can transition samples to analysis
    def test_move_sample_to_analysis_authorized_lab(self):
        """Test lab can move sample for analysis"""
        investigation_id = 1
        expected = {
            'id': 1,
            'investigation_id': investigation_id,
            'status': 'IN_ANALYSIS'
        }
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.storage_service.move_sample_to_analysis(
                self.mock_conn,
                investigation_id
            )
            assert result['status'] == 'IN_ANALYSIS'
    
    # NEGATIVE: HC-6 - Unauthorized user can transition samples
    def test_move_sample_to_analysis_unauthorized_user(self):
        """Test vulnerability: invalid user can transition samples (no auth)"""
        investigation_id = 1
        
        with patch('sample_storage.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'status': 'IN_ANALYSIS'}
            # VULNERABLE: Anyone can transition samples
            result = self.storage_service.move_sample_to_analysis(
                self.mock_conn,
                investigation_id
            )
            assert result is not None


class TestAnalyzerService:
    """Tests for Analyzer Service"""
    
    def setup_method(self):
        self.analyzer_service = AnalyzerService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Lab can create analyzers
    def test_create_analyzer_authorized_lab(self):
        """Test authorized lab can create analyzer"""
        name = "Analyzer-1"
        model = "Model-X"
        expected = {
            'id': 1,
            'name': name,
            'model': model,
            'status': 'ACTIVE'
        }
        
        with patch('analyzers.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.analyzer_service.create_analyzer(
                self.mock_conn,
                name,
                model
            )
            assert result['status'] == 'ACTIVE'
    
    # NEGATIVE: HC-3 - Unauthorized user can create analyzers
    def test_create_analyzer_unauthorized_user(self):
        """Test vulnerability: non-lab user can create analyzers (no auth check)"""
        name = "Fake-Analyzer"
        
        with patch('analyzers.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'name': name, 'status': 'ACTIVE'}
            # VULNERABLE: No check if user is authorized to create analyzers
            result = self.analyzer_service.create_analyzer(self.mock_conn, name)
            assert result['name'] == name
    
    # POSITIVE: Goal 2 - Lab can save analyzer results
    def test_save_analyzer_result_authorized(self):
        """Test lab can save analyzer results"""
        investigation_id = 1
        analyzer_id = 1
        raw_result = "Result: 150 mg/dL"
        expected = {
            'id': 1,
            'investigation_id': investigation_id,
            'analyzer_id': analyzer_id,
            'raw_result': raw_result
        }
        
        with patch('analyzers.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.analyzer_service.save_analyzer_result(
                self.mock_conn,
                investigation_id,
                analyzer_id,
                None,
                raw_result
            )
            assert result['raw_result'] == raw_result
    
    # NEGATIVE: HC-2 - Unauthorized lab can save false results
    def test_save_analyzer_result_unauthorized_lab(self):
        """Test vulnerability: fake lab can inject false results (no authentication)"""
        investigation_id = 1
        false_result = "INJECTED: Normal - No disease detected"
        
        with patch('analyzers.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {
                'id': 1,
                'investigation_id': investigation_id,
                'raw_result': false_result
            }
            # VULNERABLE: No verification that data comes from real analyzer/lab
            result = self.analyzer_service.save_analyzer_result(
                self.mock_conn,
                investigation_id,
                None,
                None,
                false_result
            )
            assert result['raw_result'] == false_result  # False data accepted


class TestWorkstationService:
    """Tests for Workstation Service"""
    
    def setup_method(self):
        self.workstation_service = WorkstationService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Authorized lab can create workstations
    def test_create_workstation_authorized_lab(self):
        """Test lab can create workstation"""
        name = "Workstation-1"
        location = "Lab-B"
        expected = {
            'id': 1,
            'name': name,
            'location': location,
            'status': 'ACTIVE'
        }
        
        with patch('workstations.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.workstation_service.create_workstation(
                self.mock_conn,
                name,
                location
            )
            assert result['status'] == 'ACTIVE'
    
    # NEGATIVE: HC-3 - Unauthorized user can create workstations
    def test_create_workstation_unauthorized_user(self):
        """Test vulnerability: non-lab user can create workstations"""
        name = "Fake-Workstation"
        
        with patch('workstations.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'name': name, 'status': 'ACTIVE'}
            # VULNERABLE: No authorization check
            result = self.workstation_service.create_workstation(self.mock_conn, name)
            assert result is not None


class TestMedicalEquipmentService:
    """Tests for Medical Equipment Service"""
    
    def setup_method(self):
        self.equipment_service = MedicalEquipmentService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Authorized staff can create equipment
    def test_create_equipment_authorized_staff(self):
        """Test authorized staff can create equipment"""
        name = "Equipment-1"
        equipment_type = "ultrasound"
        location = "Room-A"
        expected = {
            'id': 1,
            'name': name,
            'equipment_type': equipment_type,
            'location': location,
            'status': 'ACTIVE'
        }
        
        with patch('med_equipment.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.equipment_service.create_equipment(
                self.mock_conn,
                name,
                equipment_type,
                location
            )
            assert result['status'] == 'ACTIVE'
    
    # NEGATIVE: HC-3 - Unauthorized user can create equipment
    def test_create_equipment_unauthorized_user(self):
        """Test vulnerability: patient can create medical equipment"""
        name = "Fake-Equipment"
        equipment_type = "MRI"
        
        with patch('med_equipment.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'name': name, 'status': 'ACTIVE'}
            # VULNERABLE: No role-based access control
            result = self.equipment_service.create_equipment(
                self.mock_conn,
                name,
                equipment_type
            )
            assert result is not None


class TestMonitoringService:
    """Tests for Monitoring Service"""
    
    def setup_method(self):
        self.monitoring_service = MonitoringService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Authorized system can record metrics
    def test_add_metric_authorized_system(self):
        """Test authorized system can add equipment metric"""
        equipment_id = 1
        metric_name = "temperature"
        metric_value = "37.5"
        expected = {
            'id': 1,
            'equipment_id': equipment_id,
            'metric_name': metric_name,
            'metric_value': metric_value
        }
        
        with patch('monitoring.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.monitoring_service.add_metric(
                self.mock_conn,
                equipment_id,
                metric_name,
                metric_value
            )
            assert result['metric_name'] == metric_name
    
    # NEGATIVE: HC-8 - Unauthorized system can inject false metrics
    def test_add_metric_unauthorized_system(self):
        """Test vulnerability: attacker can inject false metrics (no source verification)"""
        equipment_id = 1
        false_metric = "cpu_usage"
        false_value = "999"
        
        with patch('monitoring.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {
                'id': 1,
                'equipment_id': equipment_id,
                'metric_value': false_value
            }
            # VULNERABLE: No verification of data source
            result = self.monitoring_service.add_metric(
                self.mock_conn,
                equipment_id,
                false_metric,
                false_value
            )
            assert result['metric_value'] == false_value


class TestSelfDiagnosticsService:
    """Tests for Self Diagnostics Service"""
    
    def setup_method(self):
        self.diagnostics_service = SelfDiagnosticsService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Equipment can report diagnostics
    def test_add_diagnostic_authorized_equipment(self):
        """Test equipment can report diagnostic status"""
        equipment_id = 1
        diagnostic_status = "PASSED"
        details = "All tests passed"
        expected = {
            'id': 1,
            'equipment_id': equipment_id,
            'diagnostic_status': diagnostic_status,
            'details': details
        }
        
        with patch('self_diagnostics.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.diagnostics_service.add_diagnostic(
                self.mock_conn,
                equipment_id,
                diagnostic_status,
                details
            )
            assert result['diagnostic_status'] == diagnostic_status
    
    # NEGATIVE: HC-8 - Unauthorized device can fake diagnostics
    def test_add_diagnostic_unauthorized_device(self):
        """Test vulnerability: fake device can report false diagnostics (no source auth)"""
        equipment_id = 1
        false_status = "PASSED"
        false_details = "All tests passed - SPOOFED"
        
        with patch('self_diagnostics.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {
                'id': 1,
                'equipment_id': equipment_id,
                'diagnostic_status': false_status,
                'details': false_details
            }
            # VULNERABLE: No verification that diagnostic comes from real device
            result = self.diagnostics_service.add_diagnostic(
                self.mock_conn,
                equipment_id,
                false_status,
                false_details
            )
            assert "SPOOFED" in result['details']


# Integration Tests - Testing interaction between services

class TestServiceInteractions:
    """Tests for interactions between multiple services"""
    
    def setup_method(self):
        self.lis_service = LISService()
        self.storage_service = SampleStorageService()
        self.analyzer_service = AnalyzerService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Valid workflow - investigation -> sample -> analysis
    def test_investigation_to_analysis_workflow_authorized(self):
        """Test complete authorized workflow: order investigation -> register sample -> analyze"""
        investigation_id = 1
        
        with patch('lis.service.fetch_one') as mock_lis_fetch, \
             patch('sample_storage.service.fetch_one') as mock_storage_fetch, \
             patch('analyzers.service.fetch_one') as mock_analyzer_fetch:
            
            # Step 1: Get investigation
            mock_lis_fetch.return_value = {'id': investigation_id, 'status': 'ORDERED'}
            investigation = self.lis_service.get_investigation(self.mock_conn, investigation_id)
            assert investigation['status'] == 'ORDERED'
            
            # Step 2: Register sample for investigation
            mock_storage_fetch.return_value = {
                'investigation_id': investigation_id,
                'status': 'REGISTERED'
            }
            sample = self.storage_service.register_sample(
                self.mock_conn,
                investigation_id,
                "blood"
            )
            assert sample['status'] == 'REGISTERED'
            
            # Step 3: Save analyzer result
            mock_analyzer_fetch.return_value = {
                'investigation_id': investigation_id,
                'raw_result': 'Normal'
            }
            result = self.analyzer_service.save_analyzer_result(
                self.mock_conn,
                investigation_id,
                1,
                None,
                'Normal'
            )
            assert result['raw_result'] == 'Normal'
    
    # NEGATIVE: HC-2 - Workflow allows unauthorized data transmission
    def test_investigation_to_analysis_workflow_unauthorized(self):
        """Test vulnerability: unauthed user can manipulate entire workflow"""
        investigation_id = 1
        
        with patch('lis.service.fetch_one') as mock_lis_fetch, \
             patch('sample_storage.service.fetch_one') as mock_storage_fetch, \
             patch('analyzers.service.fetch_one') as mock_analyzer_fetch:
            
            # VULNERABLE: No authorization checks at any step
            mock_lis_fetch.return_value = {'id': investigation_id}
            mock_storage_fetch.return_value = {'id': 1}
            mock_analyzer_fetch.return_value = {'id': 1, 'raw_result': 'INJECTED'}
            
            # Unauthorized user can complete entire workflow
            investigation = self.lis_service.get_investigation(self.mock_conn, investigation_id)
            sample = self.storage_service.register_sample(self.mock_conn, investigation_id, "blood")
            result = self.analyzer_service.save_analyzer_result(
                self.mock_conn,
                investigation_id,
                1,
                None,
                'INJECTED'
            )
            assert investigation is not None  # Should fail but succeeds
            assert sample is not None
            assert result is not None
    
    # NEGATIVE: HC-5 - Data authenticity not verified in workflow
    def test_non_authentic_data_in_workflow(self):
        """Test vulnerability: non-authentic results accepted in workflow (no integrity check)"""
        investigation_id = 1
        fake_results = "FABRICATED RESULTS"
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {
                'id': investigation_id,
                'status': 'COMPLETED',
                'results': fake_results
            }
            # VULNERABLE: No data integrity verification
            result = self.lis_service.complete_investigation(
                self.mock_conn,
                investigation_id,
                fake_results
            )
            assert result['results'] == fake_results  # Fake data accepted
    
    # NEGATIVE: HC-1 - EMK access not verified
    def test_emk_access_bypass_in_workflow(self):
        """Test vulnerability: EMK data accessible without proper authorization in workflow"""
        patient_id = 999
        investigation_id = 1
        
        with patch('lis.service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {
                'id': investigation_id,
                'patient_id': patient_id
            }
            # VULNERABLE: No check if caller is authorized for this patient
            result = self.lis_service.get_investigation(self.mock_conn, investigation_id)
            assert result['patient_id'] == patient_id  # Should verify authorization


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
