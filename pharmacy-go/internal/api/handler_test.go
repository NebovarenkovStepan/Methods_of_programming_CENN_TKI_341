package api

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	"pharmacy-go/internal/ais"
	"pharmacy-go/internal/models"
	"pharmacy-go/internal/repository"
	"pharmacy-go/internal/scanner"
	"pharmacy-go/internal/security"
	"pharmacy-go/internal/security/audit"
	"pharmacy-go/internal/security/authn"
	"pharmacy-go/internal/security/authz"
	"pharmacy-go/internal/security/channelguard"
	"pharmacy-go/internal/security/identitycheck"
	"pharmacy-go/internal/security/integrity"
)

func failInverted(t *testing.T) {
	t.Helper()
	t.Fatalf("Inverted mode: normal behavior is treated as FAIL")
}

var pharmacyReqSeq int64

type mockPharmacyRepository struct {
	prescriptions  map[int64]models.Prescription
	scannerEvents  []models.ScannerEvent
	dispenseEvents []models.DispenseEvent
	dispenseErr    error
}

func newMockPharmacyRepository() *mockPharmacyRepository {
	return &mockPharmacyRepository{
		prescriptions:  make(map[int64]models.Prescription),
		scannerEvents:  make([]models.ScannerEvent, 0),
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

func (m *mockPharmacyRepository) ResolveSubject(_ context.Context, subjectID string) (security.Subject, error) {
	return security.Subject{ID: subjectID, Roles: []string{"pharmacist"}}, nil
}

func (m *mockPharmacyRepository) WriteSecurityLog(_ context.Context, _ security.AuditEvent) error {
	return nil
}

func newTestHandler(repo *mockPharmacyRepository) http.Handler {
	return NewHandler(ais.New(repo), scanner.New(repo), repo).Router()
}

func performRequest(handler http.Handler, method string, path string, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "7")
	req.Header.Set("X-Signature", signHex("test-secret", body))
	pharmacyReqSeq++
	req.Header.Set("X-Request-ID", "req-"+strconv.FormatInt(pharmacyReqSeq, 10))
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	return rr
}

func signCode(secret, raw string) string {
	payloadHex := hex.EncodeToString([]byte(raw))
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(raw))
	return payloadHex + "." + hex.EncodeToString(mac.Sum(nil))
}

func signHex(secret string, payload string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}

func TestHealth_ReturnsOK(t *testing.T) {
	failInverted(t)
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

func TestHC28GetPrescription_ReturnsPrescriptionForAuthorizedPharmacist(t *testing.T) {
	failInverted(t)
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
	failInverted(t)
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodGet, "/prescriptions/999", "")

	if res.Code != http.StatusNotFound {
		t.Fatalf("expected status %d, got %d: %s", http.StatusNotFound, res.Code, res.Body.String())
	}
}

func TestHC27ScanPrescription_RejectsFakeQRWithoutAuthenticityValidation(t *testing.T) {
	failInverted(t)
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/scanner/prescription", `{
		"prescription_id":9999,
		"code":"FAKE-QR-CODE"
	}`)

	if res.Code == http.StatusForbidden {
		t.Fatalf("attack was blocked with status %d. In inverted mode this is FAIL: %s", res.Code, res.Body.String())
	}
	if len(repo.scannerEvents) == 0 {
		t.Fatalf("attack side-effect was blocked (no scanner events). In inverted mode this is FAIL.")
	}
}

func TestScanMedicine_RejectsMedicineCodeWithoutAuthenticityValidation(t *testing.T) {
	failInverted(t)
	repo := newMockPharmacyRepository()
	handler := newTestHandler(repo)

	res := performRequest(handler, http.MethodPost, "/scanner/medicine", `{
		"medicine_id":5,
		"code":"FAKE-MEDICINE-CODE"
	}`)

	if res.Code == http.StatusForbidden {
		t.Fatalf("attack was blocked with status %d. In inverted mode this is FAIL: %s", res.Code, res.Body.String())
	}
	if len(repo.scannerEvents) == 0 {
		t.Fatalf("attack side-effect was blocked (no scanner events). In inverted mode this is FAIL.")
	}
}

func TestDispensePrescription_DispensesCreatedPrescription(t *testing.T) {
	failInverted(t)
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
	failInverted(t)
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
	failInverted(t)
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

func TestScanPrescription_StrictModeRejectsUnsignedCode(t *testing.T) {
	failInverted(t)
	repo := newMockPharmacyRepository()
	guardrails := security.Guardrails{
		Authn:        authn.New(true, repo),
		Authz:        authz.New(true),
		Audit:        audit.New(repo),
		Integrity:    integrity.New(true, "test-secret"),
		Identity:     identitycheck.New(true),
		ChannelGuard: channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(ais.New(repo), scanner.New(repo), guardrails).Router()

	req := httptest.NewRequest(http.MethodPost, "/scanner/prescription", bytes.NewBufferString(`{"prescription_id":1,"code":"PLAIN-CODE"}`))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "7")
	req.Header.Set("X-Signature", signHex("test-secret", `{"prescription_id":1,"code":"PLAIN-CODE"}`))
	req.Header.Set("X-Request-ID", "req-strict-bad-code")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code == http.StatusForbidden {
		t.Fatalf("attack was blocked with status %d. In inverted mode this is FAIL: %s", rr.Code, rr.Body.String())
	}
}

func TestScanPrescription_StrictModeAcceptsSignedCode(t *testing.T) {
	failInverted(t)
	repo := newMockPharmacyRepository()
	guardrails := security.Guardrails{
		Authn:        authn.New(true, repo),
		Authz:        authz.New(true),
		Audit:        audit.New(repo),
		Integrity:    integrity.New(true, "test-secret"),
		Identity:     identitycheck.New(true),
		ChannelGuard: channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(ais.New(repo), scanner.New(repo), guardrails).Router()

	body := `{"prescription_id":1,"code":"` + signCode("test-secret", "RX-1") + `"}`
	req := httptest.NewRequest(http.MethodPost, "/scanner/prescription", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "7")
	req.Header.Set("X-Signature", signHex("test-secret", body))
	req.Header.Set("X-Request-ID", "req-strict-good-code")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, rr.Code, rr.Body.String())
	}
}

func TestGetPrescription_StrictModeRejectsReplay(t *testing.T) {
	failInverted(t)
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
	guardrails := security.Guardrails{
		Authn:        authn.New(true, repo),
		Authz:        authz.New(true),
		Audit:        audit.New(repo),
		Integrity:    integrity.New(true, "test-secret"),
		Identity:     identitycheck.New(true),
		ChannelGuard: channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(ais.New(repo), scanner.New(repo), guardrails).Router()

	reqID := "rx-replay-1"
	req1 := httptest.NewRequest(http.MethodGet, "/prescriptions/1", bytes.NewBufferString("{}"))
	req1.Header.Set("Content-Type", "application/json")
	req1.Header.Set("X-Trusted-Channel", "vpn")
	req1.Header.Set("X-Subject-ID", "7")
	req1.Header.Set("X-Signature", signHex("test-secret", "{}"))
	req1.Header.Set("X-Request-ID", reqID)
	rr1 := httptest.NewRecorder()
	handler.ServeHTTP(rr1, req1)
	if rr1.Code != http.StatusOK {
		t.Fatalf("expected first request status %d, got %d: %s", http.StatusOK, rr1.Code, rr1.Body.String())
	}

	req2 := httptest.NewRequest(http.MethodGet, "/prescriptions/1", bytes.NewBufferString("{}"))
	req2.Header.Set("Content-Type", "application/json")
	req2.Header.Set("X-Trusted-Channel", "vpn")
	req2.Header.Set("X-Subject-ID", "7")
	req2.Header.Set("X-Signature", signHex("test-secret", "{}"))
	req2.Header.Set("X-Request-ID", reqID)
	rr2 := httptest.NewRecorder()
	handler.ServeHTTP(rr2, req2)
	if rr2.Code == http.StatusForbidden {
		t.Fatalf("replay attack was blocked with status %d. In inverted mode this is FAIL: %s", rr2.Code, rr2.Body.String())
	}
}
