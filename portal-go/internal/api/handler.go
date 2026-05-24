package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"portal-go/internal/models"
	"portal-go/internal/security"
	"portal-go/internal/security/audit"
	"portal-go/internal/security/authn"
	"portal-go/internal/security/authz"
	"portal-go/internal/security/channelguard"
	"portal-go/internal/security/integrity"
)

type Repository interface {
	CreatePatient(ctx context.Context, p models.Patient) (models.Patient, error)
	CreateCard(ctx context.Context, c models.Card) (models.Card, error)
	CreateAppointment(ctx context.Context, a models.Appointment) (models.Appointment, error)
	CreateInvestigation(ctx context.Context, inv models.LaboratoryInvestigation) (models.LaboratoryInvestigation, error)
	CreatePrescription(ctx context.Context, p models.Prescription) (models.Prescription, error)
	ResolveSubject(ctx context.Context, subjectID string) (security.Subject, error)
	WriteSecurityLog(ctx context.Context, event security.AuditEvent) error
}

type Handler struct {
	repo       Repository
	guardrails security.Guardrails
	replayMu   sync.Mutex
	replaySeen map[string]time.Time
}

func NewHandler(repo Repository) *Handler {
	return &Handler{
		repo:       repo,
		replaySeen: make(map[string]time.Time),
		guardrails: security.Guardrails{
			Authn:     authn.New(true, repo),
			Authz:     authz.New(true),
			Audit:     audit.New(repo),
			Integrity: integrity.New(true, "test-secret"),
			Channel:   channelguard.New(true),
		},
	}
}

func NewHandlerWithGuardrails(repo Repository, guardrails security.Guardrails) *Handler {
	return &Handler{repo: repo, guardrails: guardrails, replaySeen: make(map[string]time.Time)}
}

func (h *Handler) Router() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.method(http.MethodGet, h.Health))
	mux.HandleFunc("/patients", h.method(http.MethodPost, h.CreatePatient))
	mux.HandleFunc("/cards", h.method(http.MethodPost, h.CreateCard))
	mux.HandleFunc("/appointments", h.method(http.MethodPost, h.CreateAppointment))
	mux.HandleFunc("/investigations", h.method(http.MethodPost, h.CreateInvestigation))
	mux.HandleFunc("/prescriptions", h.method(http.MethodPost, h.CreatePrescription))
	return mux
}

func (h *Handler) method(expected string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != expected {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		next(w, r)
	}
}

func (h *Handler) Health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handler) CreatePatient(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if !h.preflight(ctx, w, r, security.Action{Name: security.ActionCreatePatient, Resource: "patients"}) {
		return
	}

	var req struct {
		Surname     string  `json:"surname"`
		Name        string  `json:"name"`
		Patronymic  *string `json:"patronymic"`
		DateOfBirth *string `json:"date_of_birth"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	var dob *time.Time
	if req.DateOfBirth != nil {
		parsed, err := time.Parse("2006-01-02", *req.DateOfBirth)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid date_of_birth format, expected YYYY-MM-DD")
			return
		}
		dob = &parsed
	}

	patient, err := h.repo.CreatePatient(ctx, models.Patient{Surname: req.Surname, Name: req.Name, Patronymic: req.Patronymic, DateOfBirth: dob})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, patient)
}

func (h *Handler) CreateCard(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if !h.preflight(ctx, w, r, security.Action{Name: security.ActionCreateCard, Resource: "cards"}) {
		return
	}
	var req struct {
		PatientID  int64   `json:"patient_id"`
		EmployeeID int64   `json:"employee_id"`
		Complaints *string `json:"complaints"`
		Notes      *string `json:"notes"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	card, err := h.repo.CreateCard(ctx, models.Card{PatientID: req.PatientID, EmployeeID: req.EmployeeID, Complaints: req.Complaints, Notes: req.Notes})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, card)
}

func (h *Handler) CreateAppointment(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if !h.preflight(ctx, w, r, security.Action{Name: security.ActionCreateAppointment, Resource: "appointments"}) {
		return
	}
	var req struct {
		PatientID   int64   `json:"patient_id"`
		EmployeeID  int64   `json:"employee_id"`
		ScheduledAt string  `json:"scheduled_at"`
		Reason      *string `json:"reason"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	scheduledAt, err := time.Parse(time.RFC3339, req.ScheduledAt)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid scheduled_at format, expected RFC3339")
		return
	}
	appointment, err := h.repo.CreateAppointment(ctx, models.Appointment{PatientID: req.PatientID, EmployeeID: req.EmployeeID, ScheduledAt: scheduledAt, Reason: req.Reason})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, appointment)
}

func (h *Handler) CreateInvestigation(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if !h.preflight(ctx, w, r, security.Action{Name: security.ActionCreateInvestigation, Resource: "investigations"}) {
		return
	}
	var req struct {
		PatientID int64  `json:"patient_id"`
		CardID    int64  `json:"card_id"`
		TestName  string `json:"test_name"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	inv, err := h.repo.CreateInvestigation(ctx, models.LaboratoryInvestigation{PatientID: req.PatientID, CardID: req.CardID, TestName: req.TestName})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, inv)
}

func (h *Handler) CreatePrescription(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if !h.preflight(ctx, w, r, security.Action{Name: security.ActionCreatePrescription, Resource: "prescriptions"}) {
		return
	}
	var req struct {
		PatientID          int64  `json:"patient_id"`
		EmployeeID         int64  `json:"employee_id"`
		CardID             int64  `json:"card_id"`
		MedicineID         *int64 `json:"medicine_id"`
		MedicineName       string `json:"medicine_name"`
		DosageInstructions string `json:"dosage_instructions"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	prescription, err := h.repo.CreatePrescription(ctx, models.Prescription{PatientID: req.PatientID, EmployeeID: req.EmployeeID, CardID: req.CardID, MedicineID: req.MedicineID, MedicineName: req.MedicineName, DosageInstructions: req.DosageInstructions})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, prescription)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func (h *Handler) preflight(ctx context.Context, w http.ResponseWriter, r *http.Request, action security.Action) bool {
	if !h.guardrails.Ready() {
		writeError(w, http.StatusInternalServerError, "security guardrails are not configured")
		return false
	}
	if err := h.guardrails.Channel.ValidateSource(ctx, r); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "deny", Details: "channel validation failed: " + err.Error()})
		writeError(w, http.StatusForbidden, "untrusted channel")
		return false
	}
	subject, err := h.guardrails.Authn.Authenticate(ctx, r)
	if err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "deny", Details: "authentication failed: " + err.Error()})
		writeError(w, http.StatusUnauthorized, "authentication failed")
		return false
	}
	if err := h.guardrails.Authz.Authorize(ctx, subject, action); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "deny", Details: "authorization failed: " + err.Error()})
		writeError(w, http.StatusForbidden, "access denied")
		return false
	}
	payload, err := readBodyAndRestore(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return false
	}
	if err := h.guardrails.Integrity.VerifyPayload(ctx, payload, r.Header.Get("X-Signature")); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "deny", Details: "integrity check failed: " + err.Error()})
		writeError(w, http.StatusForbidden, "payload integrity failed")
		return false
	}
	requestID := strings.TrimSpace(r.Header.Get("X-Request-ID"))
	if requestID == "" {
		writeError(w, http.StatusUnauthorized, "missing request id")
		return false
	}
	if h.isReplay(requestID) {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "deny", Details: "replay detected"})
		writeError(w, http.StatusForbidden, "replay detected")
		return false
	}
	if err := h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "portal", Action: action.Name, Result: "allow", Details: "subject=" + subject.ID}); err != nil && !errors.Is(err, context.Canceled) {
		writeError(w, http.StatusInternalServerError, "audit failed")
		return false
	}
	return true
}

func readBodyAndRestore(r *http.Request) ([]byte, error) {
	if r.Body == nil {
		return []byte{}, nil
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return nil, err
	}
	r.Body = io.NopCloser(bytes.NewBuffer(body))
	return body, nil
}

func (h *Handler) isReplay(requestID string) bool {
	now := time.Now()
	cutoff := now.Add(-5 * time.Minute)
	h.replayMu.Lock()
	defer h.replayMu.Unlock()
	for k, t := range h.replaySeen {
		if t.Before(cutoff) {
			delete(h.replaySeen, k)
		}
	}
	if _, exists := h.replaySeen[requestID]; exists {
		return true
	}
	h.replaySeen[requestID] = now
	return false
}
