package api

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"pharmacy-go/internal/ais"
	"pharmacy-go/internal/models"
	"pharmacy-go/internal/repository"
	"pharmacy-go/internal/scanner"
)

type mockPharmacyRepository struct {
	prescriptions map[int64]models.Prescription
	scannerEvents []models.ScannerEvent
	dispenseEvents []models.DispenseEvent
	dispenseErr    error
}

func newMockPharmacyRepository() *mockPharmacyRepository {
	return &mockPharmacyRepository{
		prescriptions: make(map[int64]models.Prescription),
		scannerEvents: make([]models.ScannerEvent, 0),
		dispenseEvents: make([]models.DispenseEvent, 0),
	}
}

func int64Ptr(v int64) *int64 {
	return &v
}

func (m *mockPharmacyRepository) GetPrescriptionByID(_ context.Context, id int64) (models.Prescription, error) {
	p, ok := m.prescriptions[id]
	if !ok {
		return models.Prescription{}, repository.ErrNotFound
	}
	return p, nil
}

func (m *mockPharmacyRepository) CreateScannerEvent(_ context.Context, eventType string, scannedCode string, prescriptionID *int64, medicineID *int64) (models.ScannerEvent, error) {
	event := models.ScannerEvent{
		ID:             int64(len(m.scannerEvents) + 1),
		EventType:      eventType,
		ScannedCode:    scannedCode,
		PrescriptionID: prescriptionID,
		MedicineID:     medicineID,
		ScannedAt:      time.Date(2026, 4, 25, 10, 0, 0, 0, time.UTC),
	}
	m.scannerEvents = append(m.scannerEvents, event)
	return event, nil
}

func (m *mockPharmacyRepository) DispensePrescription(_ context.Context, prescriptionID int64, quantity int) (models.DispenseEvent, error) {
	if m.dispenseErr != nil {
		return models.DispenseEvent{}, m.dispenseErr
	}
	p, ok := m.prescriptions[prescriptionID]
	if !ok {
		return models.DispenseEvent{}, repository.ErrNotFound
	}
	if p.MedicineID == nil {
		return models.DispenseEvent{}, repository.ErrMedicineNotLinked
	}
	event := models.DispenseEvent{
		ID:             int64(len(m.dispenseEvents) + 1),
		PrescriptionID: prescriptionID,
		MedicineID:     *p.MedicineID,
		Quantity:       quantity,
		DispensedAt:    time.Date(2026, 4, 25, 10, 0, 0, 0, time.UTC),
	}
	m.dispenseEvents = append(m.dispenseEvents, event)
	return event, nil
}

func newTestHandler(repo *mockPharmacyRepository) http.Handler {
	return NewHandler(ais.New(repo), scanner.New(repo)).Router()
}

func performRequest(handler http.Handler, method string, path string, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	return rr
}

func TestHealth_ReturnsOK(t *testing.T) {
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodGet, "/health", "")

	if res.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, res.Code, res.Body.String())
	}
	if !strings.Contains(res.Body.String(), "ok") {
		t.Fatalf("expected health response to contain ok, got %s", res.Body.String())
	}
}

func TestGetPrescription_ReturnsExistingPrescription(t *testing.T) {
	repo := newMockPharmacyRepository()
	repo.prescriptions[1] = models.Prescription{
		ID:           1,
		PatientID:    10,
		EmployeeID:   20,
		CardID:       30,
		MedicineID:   int64Ptr(5),
		MedicineName: "Парацетамол",
		Status:       "CREATED",
	}
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodGet, "/prescriptions/1", "")

	if res.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, res.Code, res.Body.String())
	}
	var body models.Prescription
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if body.ID != 1 || body.MedicineName != "Парацетамол" {
		t.Fatalf("unexpected prescription response: %#v", body)
	}
}

func TestGetPrescription_NotFound(t *testing.T) {
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodGet, "/prescriptions/999", "")

	if res.Code != http.StatusNotFound {
		t.Fatalf("expected status %d, got %d: %s", http.StatusNotFound, res.Code, res.Body.String())
	}
}

func TestScanPrescription_AcceptsFakeQRWithoutAuthenticityValidation(t *testing.T) {
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/scanner/prescription", `{
		"prescription_id":9999,
		"code":"FAKE-QR-CODE"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.scannerEvents) != 1 {
		t.Fatalf("expected 1 scanner event, got %d", len(repo.scannerEvents))
	}
	if repo.scannerEvents[0].ScannedCode != "FAKE-QR-CODE" {
		t.Fatalf("expected fake code to be stored, got %s", repo.scannerEvents[0].ScannedCode)
	}
	if repo.scannerEvents[0].PrescriptionID == nil || *repo.scannerEvents[0].PrescriptionID != 9999 {
		t.Fatalf("expected prescription_id 9999, got %#v", repo.scannerEvents[0].PrescriptionID)
	}
}

func TestScanMedicine_AcceptsMedicineCodeWithoutAuthenticityValidation(t *testing.T) {
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/scanner/medicine", `{
		"medicine_id":5,
		"code":"FAKE-MEDICINE-CODE"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.scannerEvents) != 1 {
		t.Fatalf("expected 1 scanner event, got %d", len(repo.scannerEvents))
	}
	if repo.scannerEvents[0].EventType != "MEDICINE_SCAN" {
		t.Fatalf("expected MEDICINE_SCAN, got %s", repo.scannerEvents[0].EventType)
	}
}

func TestDispensePrescription_DispensesCreatedPrescription(t *testing.T) {
	repo := newMockPharmacyRepository()
	repo.prescriptions[1] = models.Prescription{
		ID:           1,
		MedicineID:   int64Ptr(5),
		MedicineName: "Парацетамол",
		Status:       "CREATED",
	}
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/dispense", `{
		"prescription_id":1,
		"quantity":2
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.dispenseEvents) != 1 {
		t.Fatalf("expected 1 dispense event, got %d", len(repo.dispenseEvents))
	}
	if repo.dispenseEvents[0].MedicineID != 5 || repo.dispenseEvents[0].Quantity != 2 {
		t.Fatalf("unexpected dispense event: %#v", repo.dispenseEvents[0])
	}
}

func TestDispensePrescription_RejectsInvalidQuantityAtAPILevel(t *testing.T) {
	repo := newMockPharmacyRepository()
	repo.prescriptions[1] = models.Prescription{ID: 1, MedicineID: int64Ptr(5), Status: "CREATED"}
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/dispense", `{
		"prescription_id":1,
		"quantity":0
	}`)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d: %s", http.StatusBadRequest, res.Code, res.Body.String())
	}
	if len(repo.dispenseEvents) != 0 {
		t.Fatalf("expected no dispense events, got %d", len(repo.dispenseEvents))
	}
}

func TestDispensePrescription_MapsRepositoryErrors(t *testing.T) {
	tests := []struct {
		name       string
		repoErr    error
		wantStatus int
	}{
		{name: "not found", repoErr: repository.ErrNotFound, wantStatus: http.StatusNotFound},
		{name: "insufficient stock", repoErr: repository.ErrInsufficientStock, wantStatus: http.StatusConflict},
		{name: "already dispensed", repoErr: repository.ErrPrescriptionAlreadyDispensed, wantStatus: http.StatusConflict},
		{name: "cancelled", repoErr: repository.ErrPrescriptionCancelled, wantStatus: http.StatusConflict},
		{name: "medicine not linked", repoErr: repository.ErrMedicineNotLinked, wantStatus: http.StatusConflict},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			repo := newMockPharmacyRepository()
			repo.dispenseErr = tt.repoErr
			repo.prescriptions[1] = models.Prescription{ID: 1, MedicineID: int64Ptr(5), Status: "CREATED"}
			handler := newTestHandler(repo)

			res := performRequest(handler, http.MethodPost, "/dispense", `{
				"prescription_id":1,
				"quantity":1
			}`)

			if res.Code != tt.wantStatus {
				t.Fatalf("expected status %d, got %d: %s", tt.wantStatus, res.Code, res.Body.String())
			}
		})
	}
}
