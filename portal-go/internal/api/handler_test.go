package api

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	"portal-go/internal/models"
	"portal-go/internal/security"
	"portal-go/internal/security/audit"
	"portal-go/internal/security/authn"
	"portal-go/internal/security/authz"
	"portal-go/internal/security/channelguard"
	"portal-go/internal/security/integrity"
)

type mockPortalRepository struct {
	patients       []models.Patient
	cards          []models.Card
	appointments   []models.Appointment
	investigations []models.LaboratoryInvestigation
	prescriptions  []models.Prescription
	err            error
}

var testReqSeq int64

func (m *mockPortalRepository) ResolveSubject(_ context.Context, subjectID string) (security.Subject, error) {
	return security.Subject{ID: subjectID, Roles: []string{"doctor"}}, nil
}

func (m *mockPortalRepository) WriteSecurityLog(_ context.Context, _ security.AuditEvent) error {
	return nil
}

func (m *mockPortalRepository) CreatePatient(_ context.Context, p models.Patient) (models.Patient, error) {
	if m.err != nil {
		return models.Patient{}, m.err
	}
	p.ID = int64(len(m.patients) + 1)
	m.patients = append(m.patients, p)
	return p, nil
}

func (m *mockPortalRepository) CreateCard(_ context.Context, c models.Card) (models.Card, error) {
	if m.err != nil {
		return models.Card{}, m.err
	}
	c.ID = int64(len(m.cards) + 1)
	c.DateOfVisit = time.Date(2026, 4, 25, 10, 0, 0, 0, time.UTC)
	m.cards = append(m.cards, c)
	return c, nil
}

func (m *mockPortalRepository) CreateAppointment(_ context.Context, a models.Appointment) (models.Appointment, error) {
	if m.err != nil {
		return models.Appointment{}, m.err
	}
	a.ID = int64(len(m.appointments) + 1)
	a.Status = "CONFIRMED"
	a.CreatedAt = time.Date(2026, 4, 25, 9, 0, 0, 0, time.UTC)
	m.appointments = append(m.appointments, a)
	return a, nil
}

func (m *mockPortalRepository) CreateInvestigation(_ context.Context, inv models.LaboratoryInvestigation) (models.LaboratoryInvestigation, error) {
	if m.err != nil {
		return models.LaboratoryInvestigation{}, m.err
	}
	inv.ID = int64(len(m.investigations) + 1)
	inv.Status = "ORDERED"
	inv.DateOrdered = time.Date(2026, 4, 25, 10, 0, 0, 0, time.UTC)
	m.investigations = append(m.investigations, inv)
	return inv, nil
}

func (m *mockPortalRepository) CreatePrescription(_ context.Context, p models.Prescription) (models.Prescription, error) {
	if m.err != nil {
		return models.Prescription{}, m.err
	}
	p.ID = int64(len(m.prescriptions) + 1)
	p.Status = "CREATED"
	p.DateOfReceipt = time.Date(2026, 4, 25, 10, 0, 0, 0, time.UTC)
	m.prescriptions = append(m.prescriptions, p)
	return p, nil
}

func performRequest(handler http.Handler, method string, path string, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "123")
	req.Header.Set("X-Signature", signHex("test-secret", body))
	testReqSeq++
	req.Header.Set("X-Request-ID", "req-"+strconv.FormatInt(testReqSeq, 10))
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	return rr
}

func signHex(secret string, payload string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}

func TestHealth_ReturnsOK(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodGet, "/health", "")

	if res.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d: %s", http.StatusOK, res.Code, res.Body.String())
	}
	if !strings.Contains(res.Body.String(), "ok") {
		t.Fatalf("expected health response to contain ok, got %s", res.Body.String())
	}
}

func TestCreatePatient_CreatesPatientWithValidSecurityHeaders(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/patients", `{
		"surname":"Иванов",
		"name":"Иван",
		"patronymic":"Иванович",
		"date_of_birth":"2000-01-01"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.patients) != 1 {
		t.Fatalf("expected 1 created patient, got %d", len(repo.patients))
	}
	if repo.patients[0].Surname != "Иванов" || repo.patients[0].Name != "Иван" {
		t.Fatalf("unexpected patient stored: %#v", repo.patients[0])
	}

	var body models.Patient
	if err := json.Unmarshal(res.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if body.ID != 1 {
		t.Fatalf("expected response patient id 1, got %d", body.ID)
	}
}

func TestCreatePatient_InvalidDateReturnsBadRequest(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/patients", `{
		"surname":"Иванов",
		"name":"Иван",
		"date_of_birth":"01.01.2000"
	}`)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d: %s", http.StatusBadRequest, res.Code, res.Body.String())
	}
	if len(repo.patients) != 0 {
		t.Fatalf("expected no created patients, got %d", len(repo.patients))
	}
}

func TestHC18CreateCard_CreatesRecordForAuthorizedDoctorSubject(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/cards", `{
		"patient_id":1,
		"employee_id":99,
		"complaints":"Поддельная жалоба",
		"notes":"Запись создана без авторизации врача"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.cards) != 1 {
		t.Fatalf("expected 1 created card, got %d", len(repo.cards))
	}
	if repo.cards[0].EmployeeID != 99 {
		t.Fatalf("expected employee_id 99, got %d", repo.cards[0].EmployeeID)
	}
	if repo.cards[0].Complaints == nil || *repo.cards[0].Complaints != "Поддельная жалоба" {
		t.Fatalf("expected complaints to be stored, got %#v", repo.cards[0].Complaints)
	}
}

func TestCreateAppointment_ConfirmsPatientVisit(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/appointments", `{
		"patient_id":1,
		"employee_id":2,
		"scheduled_at":"2026-05-05T09:30:00Z",
		"reason":"Первичная консультация"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.appointments) != 1 {
		t.Fatalf("expected 1 created appointment, got %d", len(repo.appointments))
	}
	if repo.appointments[0].PatientID != 1 || repo.appointments[0].EmployeeID != 2 {
		t.Fatalf("unexpected appointment participants: %#v", repo.appointments[0])
	}
	if repo.appointments[0].Status != "CONFIRMED" {
		t.Fatalf("expected status CONFIRMED, got %s", repo.appointments[0].Status)
	}
	if repo.appointments[0].Reason == nil || *repo.appointments[0].Reason != "Первичная консультация" {
		t.Fatalf("unexpected appointment reason: %#v", repo.appointments[0].Reason)
	}
}

func TestCreateAppointment_InvalidDateReturnsBadRequest(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/appointments", `{
		"patient_id":1,
		"employee_id":2,
		"scheduled_at":"05.05.2026 09:30",
		"reason":"Первичная консультация"
	}`)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d: %s", http.StatusBadRequest, res.Code, res.Body.String())
	}
	if len(repo.appointments) != 0 {
		t.Fatalf("expected no created appointments, got %d", len(repo.appointments))
	}
}

func TestHC32CreateInvestigation_CreatesOrderForAuthorizedDoctorSubject(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/investigations", `{
		"patient_id":1,
		"card_id":1,
		"test_name":"Общий анализ крови"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.investigations) != 1 {
		t.Fatalf("expected 1 created investigation, got %d", len(repo.investigations))
	}
	if repo.investigations[0].Status != "ORDERED" {
		t.Fatalf("expected status ORDERED, got %s", repo.investigations[0].Status)
	}
	if repo.investigations[0].TestName != "Общий анализ крови" {
		t.Fatalf("unexpected test name: %s", repo.investigations[0].TestName)
	}
}

func TestCreatePrescription_CreatesPrescriptionForAuthorizedDoctorSubject(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()
	medicineID := int64(5)

	res := performRequest(handler, http.MethodPost, "/prescriptions", `{
		"patient_id":1,
		"employee_id":99,
		"card_id":1,
		"medicine_id":5,
		"medicine_name":"Парацетамол",
		"dosage_instructions":"По 1 таблетке 2 раза в день"
	}`)

	if res.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, res.Code, res.Body.String())
	}
	if len(repo.prescriptions) != 1 {
		t.Fatalf("expected 1 created prescription, got %d", len(repo.prescriptions))
	}
	if repo.prescriptions[0].MedicineID == nil || *repo.prescriptions[0].MedicineID != medicineID {
		t.Fatalf("expected medicine_id %d, got %#v", medicineID, repo.prescriptions[0].MedicineID)
	}
	if repo.prescriptions[0].EmployeeID != 99 {
		t.Fatalf("expected unchecked employee_id 99, got %d", repo.prescriptions[0].EmployeeID)
	}
}

func TestCreatePrescription_InvalidJSONReturnsBadRequest(t *testing.T) {
	repo := &mockPortalRepository{}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/prescriptions", `{bad json}`)

	if res.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d: %s", http.StatusBadRequest, res.Code, res.Body.String())
	}
	if len(repo.prescriptions) != 0 {
		t.Fatalf("expected no created prescriptions, got %d", len(repo.prescriptions))
	}
}

func TestRepositoryErrorReturnsInternalServerError(t *testing.T) {
	repo := &mockPortalRepository{err: errors.New("db error")}
	handler := NewHandler(repo).Router()

	res := performRequest(handler, http.MethodPost, "/cards", `{
		"patient_id":1,
		"employee_id":1,
		"complaints":"Ошибка",
		"notes":"Проверка ошибки репозитория"
	}`)

	if res.Code != http.StatusInternalServerError {
		t.Fatalf("expected status %d, got %d: %s", http.StatusInternalServerError, res.Code, res.Body.String())
	}
}

func TestCreatePatient_StrictModeRejectsMissingSecurityHeaders(t *testing.T) {
	repo := &mockPortalRepository{}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, "test-secret"),
		Channel:   channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(repo, guardrails).Router()

	req := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(`{"surname":"Иванов","name":"Иван"}`))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected status %d, got %d: %s", http.StatusForbidden, rr.Code, rr.Body.String())
	}
}

func TestCreatePatient_StrictModeAcceptsValidHeadersAndSignature(t *testing.T) {
	repo := &mockPortalRepository{}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, "test-secret"),
		Channel:   channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(repo, guardrails).Router()

	body := `{"surname":"Иванов","name":"Иван"}`
	req := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "123")
	req.Header.Set("X-Signature", signHex("test-secret", body))
	req.Header.Set("X-Request-ID", "req-strict-ok")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusCreated {
		t.Fatalf("expected status %d, got %d: %s", http.StatusCreated, rr.Code, rr.Body.String())
	}
}

func TestCreatePatient_StrictModeRejectsReplay(t *testing.T) {
	repo := &mockPortalRepository{}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, "test-secret"),
		Channel:   channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(repo, guardrails).Router()

	body := `{"surname":"Иванов","name":"Иван"}`
	reqID := "req-replay"

	req1 := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(body))
	req1.Header.Set("Content-Type", "application/json")
	req1.Header.Set("X-Trusted-Channel", "vpn")
	req1.Header.Set("X-Subject-ID", "123")
	req1.Header.Set("X-Signature", signHex("test-secret", body))
	req1.Header.Set("X-Request-ID", reqID)
	rr1 := httptest.NewRecorder()
	handler.ServeHTTP(rr1, req1)
	if rr1.Code != http.StatusCreated {
		t.Fatalf("expected first request status %d, got %d: %s", http.StatusCreated, rr1.Code, rr1.Body.String())
	}

	req2 := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(body))
	req2.Header.Set("Content-Type", "application/json")
	req2.Header.Set("X-Trusted-Channel", "vpn")
	req2.Header.Set("X-Subject-ID", "123")
	req2.Header.Set("X-Signature", signHex("test-secret", body))
	req2.Header.Set("X-Request-ID", reqID)
	rr2 := httptest.NewRecorder()
	handler.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusForbidden {
		t.Fatalf("expected second request status %d, got %d: %s", http.StatusForbidden, rr2.Code, rr2.Body.String())
	}
}

func TestCreatePatient_StrictModeRejectsMissingSubjectWith401(t *testing.T) {
	repo := &mockPortalRepository{}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, "test-secret"),
		Channel:   channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(repo, guardrails).Router()

	body := `{"surname":"Иванов","name":"Иван"}`
	req := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Signature", signHex("test-secret", body))
	req.Header.Set("X-Request-ID", "req-missing-subject")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("expected status %d, got %d: %s", http.StatusUnauthorized, rr.Code, rr.Body.String())
	}
}

func TestCreatePatient_StrictModeRejectsSignatureMismatchWith403(t *testing.T) {
	repo := &mockPortalRepository{}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, "test-secret"),
		Channel:   channelguard.New(true),
	}
	handler := NewHandlerWithGuardrails(repo, guardrails).Router()

	body := `{"surname":"Иванов","name":"Иван"}`
	req := httptest.NewRequest(http.MethodPost, "/patients", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Trusted-Channel", "vpn")
	req.Header.Set("X-Subject-ID", "123")
	req.Header.Set("X-Signature", "deadbeef")
	req.Header.Set("X-Request-ID", "req-bad-signature")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusForbidden {
		t.Fatalf("expected status %d, got %d: %s", http.StatusForbidden, rr.Code, rr.Body.String())
	}
}
