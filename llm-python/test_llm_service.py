"""
Tests for LLM service based on security goals.
Goal 5: Only authentic data displayed on portal
Goal 9: Authorized doctor gets access to a patient's EMK-derived data
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from service.llm_service import LLMService


class TestLLMService:
    """Tests for LLM Service - Goals 5 and 9: Authorization and data authenticity"""
    
    def setup_method(self):
        self.llm_service = LLMService()
        self.mock_conn = Mock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = Mock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
    
    # POSITIVE: Goal 9 - Authorized doctor can retrieve investigation data for a report
    def test_get_investigation_authorized_doctor(self):
        """Test authorized doctor can retrieve investigation"""
        investigation_id = 1
        expected = {
            'id': 1,
            'patient_id': 1,
            'test_name': 'Blood Test',
            'results': 'Hemoglobin: 14.5 g/dL',
            'status': 'COMPLETED'
        }
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.llm_service.get_investigation(self.mock_conn, investigation_id)
            assert result == expected
    
    # NEGATIVE: HC-13 - Unauthorized user can retrieve a foreign investigation
    def test_hc13_get_investigation_unauthorized_user(self):
        """Test vulnerability: unauthorized user can retrieve an investigation."""
        investigation_id = 1
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'status': 'COMPLETED'}
            # VULNERABLE: No verification user is authorized doctor
            result = self.llm_service.get_investigation(self.mock_conn, investigation_id)
            assert result is not None
    
    # POSITIVE: Goal 5 - Generate authentic LLM analysis from completed investigation
    def test_generate_report_text_authentic_data(self):
        """Test generation of authentic report from real investigation data"""
        investigation = {
            'id': 1,
            'status': 'COMPLETED',
            'results': 'Hemoglobin: 14.5 g/dL, Leukocytes: 7.2 k/μL'
        }
        
        result = self.llm_service.generate_report_text(investigation)
        
        assert 'Hemoglobin' in result
        assert 'пределах нормы' in result
        assert result != ""
    
    # NEGATIVE: HC-10 - Tampered/incomplete lab data can reach report generation
    def test_hc10_generate_report_text_incomplete_investigation(self):
        """Test vulnerability: report generation accepts incomplete investigation input."""
        incomplete_investigation = {
            'id': 1,
            'status': 'ORDERED',  # Not completed
            'results': None
        }
        
        # VULNERABLE: Method returns message but doesn't prevent incomplete data
        result = self.llm_service.generate_report_text(incomplete_investigation)
        assert "не завершено" in result
    
    # POSITIVE: Authorized doctor saves authentic report
    def test_save_report_authorized_doctor(self):
        """Test authorized doctor can save LLM generated report"""
        patient_id = 1
        investigation_id = 1
        text = "Анализ: показатели крови в пределах нормы"
        expected = {
            'id': 1,
            'patient_id': patient_id,
            'investigation_id': investigation_id,
            'report_text': text,
            'created_at': '2026-04-25'
        }
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = expected
            result = self.llm_service.save_report(
                self.mock_conn,
                patient_id,
                investigation_id,
                text
            )
            assert result['report_text'] == text
    
    # NEGATIVE: HC-10 - Tampered report text is saved without authenticity proof
    def test_hc10_save_report_unauthorized_system(self):
        """Test vulnerability: fake report is accepted without authenticity verification."""
        patient_id = 1
        investigation_id = 1
        fake_text = "INJECTED: Анализ пациент здоров - нет заболеваний"
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = {'id': 1, 'report_text': fake_text}
            # VULNERABLE: No verification that report comes from authorized LLM
            result = self.llm_service.save_report(
                self.mock_conn,
                patient_id,
                investigation_id,
                fake_text
            )
            assert "INJECTED" in result['report_text']
    
    # POSITIVE: Complete workflow - authorized doctor generates and saves report
    def test_generate_and_save_authorized_workflow(self):
        """Test authorized complete workflow: get investigation -> generate -> save report"""
        investigation_id = 1
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            investigation = {
                'id': investigation_id,
                'patient_id': 1,
                'test_name': 'Blood Test',
                'results': 'Hemoglobin: 14.5 g/dL',
                'status': 'COMPLETED'
            }
            
            # First call returns investigation, second returns saved report
            mock_fetch.side_effect = [investigation, {
                'id': 1,
                'patient_id': 1,
                'investigation_id': investigation_id,
                'report_text': 'Анализ: показатели крови в пределах нормы. Детали: Hemoglobin: 14.5 g/dL'
            }]
            
            report, err = self.llm_service.generate_and_save(self.mock_conn, investigation_id)
            assert err is None
            assert report is not None
            assert 'пределах нормы' in report['report_text']
    
    # NEGATIVE: HC-24 - Unauthorized caller can generate a report for another patient's investigation
    def test_hc24_generate_and_save_unauthorized_user(self):
        """Test vulnerability: unauthorized caller can generate and save reports."""
        investigation_id = 1
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            investigation = {
                'id': investigation_id,
                'patient_id': 1,
                'test_name': 'Blood Test',
                'results': 'Fake results',
                'status': 'COMPLETED'
            }
            
            # VULNERABLE: No check if user is authorized doctor
            mock_fetch.side_effect = [investigation, {
                'id': 1,
                'report_text': 'INJECTED FAKE REPORT'
            }]
            
            report, err = self.llm_service.generate_and_save(self.mock_conn, investigation_id)
            assert err is None  # No error even though data is fake
            assert "INJECTED" in report['report_text']
    
    # NEGATIVE: Defensive check - non-existent investigation is rejected
    def test_generate_and_save_nonexistent_investigation(self):
        """Test error handling for non-existent investigation"""
        investigation_id = 9999
        
        with patch('service.llm_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            report, err = self.llm_service.generate_and_save(self.mock_conn, investigation_id)
            assert err == "investigation not found"
            assert report is None
    
    # NEGATIVE: HC-10 - Report authenticity cannot be verified
    def test_hc10_report_authenticity_not_verifiable(self):
        """Test vulnerability: generated report has no authenticity proof."""
        investigation = {
            'id': 1,
            'status': 'COMPLETED',
            'results': 'Any results'
        }
        
        # VULNERABLE: Report generation has no signature or proof of origin
        report1 = self.llm_service.generate_report_text(investigation)
        report2 = self.llm_service.generate_report_text(investigation)
        
        # Both reports are identical but no way to verify they came from LLM
        # Anyone could generate the same text
        assert report1 == report2  # Same output for same input, easily forgeable


class TestLLMAuthorization:
    """Tests for authorization checks in LLM service"""
    
    def setup_method(self):
        self.llm_service = LLMService()
        self.mock_conn = Mock()
    
    # NEGATIVE: HC-24 - No doctor role verification before report generation
    def test_hc24_no_role_verification_for_generation(self):
        """Test vulnerability: no role check before generating reports."""
        investigation_id = 1
        
        with patch('service.llm_service.LLMService.get_investigation') as mock_get, \
             patch('service.llm_service.LLMService.save_report') as mock_save:
            
            mock_get.return_value = {
                'id': 1,
                'patient_id': 1,
                'status': 'COMPLETED',
                'results': 'Test'
            }
            mock_save.return_value = {'id': 1}
            
            # VULNERABLE: Any user can call this method
            # No check if user is authorized doctor
            result, err = self.llm_service.generate_and_save(self.mock_conn, investigation_id)
            assert err is None  # Succeeds regardless of authorization


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
