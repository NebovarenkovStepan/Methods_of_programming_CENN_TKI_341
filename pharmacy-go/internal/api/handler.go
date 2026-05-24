package api

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"pharmacy-go/internal/ais"
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

type Handler struct {
	aisService     *ais.Service
	scannerService *scanner.Service
	guardrails     security.Guardrails
	replayMu       sync.Mutex
	replaySeen     map[string]time.Time
}

type SecurityRepository interface {
	ResolveSubject(ctx context.Context, subjectID string) (security.Subject, error)
	WriteSecurityLog(ctx context.Context, event security.AuditEvent) error
}

func NewHandler(aisService *ais.Service, scannerService *scanner.Service, securityRepo SecurityRepository) *Handler {
	return &Handler{
		aisService:     aisService,
		scannerService: scannerService,
		replaySeen:     make(map[string]time.Time),
		guardrails: security.Guardrails{
			Authn:        authn.New(true, securityRepo),
			Authz:        authz.New(true),
			Audit:        audit.New(securityRepo),
			Integrity:    integrity.New(true, "test-secret"),
			Identity:     identitycheck.New(true),
			ChannelGuard: channelguard.New(true),
		},
	}
}

func NewHandlerWithGuardrails(aisService *ais.Service, scannerService *scanner.Service, guardrails security.Guardrails) *Handler {
	return &Handler{aisService: aisService, scannerService: scannerService, guardrails: guardrails, replaySeen: make(map[string]time.Time)}
}

func (h *Handler) Router() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", h.method(http.MethodGet, h.Health))
	mux.HandleFunc("/prescriptions/", h.method(http.MethodGet, h.GetPrescription))
	mux.HandleFunc("/scanner/prescription", h.method(http.MethodPost, h.ScanPrescription))
	mux.HandleFunc("/scanner/medicine", h.method(http.MethodPost, h.ScanMedicine))
	mux.HandleFunc("/dispense", h.method(http.MethodPost, h.DispensePrescription))
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

func (h *Handler) GetPrescription(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if _, ok := h.preflight(ctx, w, r, security.ActionReadPrescription); !ok {
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/prescriptions/")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid prescription id")
		return
	}

	p, err := h.aisService.GetPrescription(ctx, id)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			writeError(w, http.StatusNotFound, "prescription not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, p)
}

func (h *Handler) ScanPrescription(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	_, ok := h.preflight(ctx, w, r, security.ActionScanPrescription)
	if !ok {
		return
	}

	var req struct {
		PrescriptionID int64  `json:"prescription_id"`
		Code           string `json:"code"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	if err := h.guardrails.Integrity.VerifyPrescriptionCode(ctx, req.PrescriptionID, req.Code); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: security.ActionScanPrescription, Result: "deny", Details: err.Error()})
		writeError(w, http.StatusForbidden, "prescription integrity check failed")
		return
	}

	event, err := h.scannerService.ScanPrescription(ctx, req.PrescriptionID, req.Code)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, event)
}

func (h *Handler) ScanMedicine(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	_, ok := h.preflight(ctx, w, r, security.ActionScanMedicine)
	if !ok {
		return
	}

	var req struct {
		MedicineID int64  `json:"medicine_id"`
		Code       string `json:"code"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	if err := h.guardrails.Integrity.VerifyMedicineCode(ctx, req.MedicineID, req.Code); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: security.ActionScanMedicine, Result: "deny", Details: err.Error()})
		writeError(w, http.StatusForbidden, "medicine integrity check failed")
		return
	}

	event, err := h.scannerService.ScanMedicine(ctx, req.MedicineID, req.Code)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, event)
}

func (h *Handler) DispensePrescription(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	subject, ok := h.preflight(ctx, w, r, security.ActionDispensePrescription)
	if !ok {
		return
	}

	var req struct {
		PrescriptionID int64 `json:"prescription_id"`
		Quantity       int   `json:"quantity"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.Quantity <= 0 {
		writeError(w, http.StatusBadRequest, "quantity must be greater than 0")
		return
	}

	prescription, err := h.aisService.GetPrescription(ctx, req.PrescriptionID)
	if err == nil {
		medicineID := int64(0)
		if prescription.MedicineID != nil {
			medicineID = *prescription.MedicineID
		}
		if err := h.guardrails.Identity.VerifyPatientForDispense(ctx, subject, security.DispenseContext{
			PrescriptionID: prescription.ID,
			PatientID:      prescription.PatientID,
			MedicineID:     medicineID,
		}); err != nil {
			_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: security.ActionDispensePrescription, Result: "deny", Details: err.Error()})
			writeError(w, http.StatusForbidden, "patient identity verification failed")
			return
		}
	}

	event, err := h.aisService.Dispense(ctx, req.PrescriptionID, req.Quantity)
	if err != nil {
		switch {
		case errors.Is(err, repository.ErrNotFound):
			writeError(w, http.StatusNotFound, "prescription not found")
			return
		case errors.Is(err, repository.ErrInsufficientStock):
			writeError(w, http.StatusConflict, "insufficient stock")
			return
		case errors.Is(err, repository.ErrPrescriptionAlreadyDispensed):
			writeError(w, http.StatusConflict, "prescription already dispensed")
			return
		case errors.Is(err, repository.ErrPrescriptionCancelled):
			writeError(w, http.StatusConflict, "prescription cancelled")
			return
		case errors.Is(err, repository.ErrMedicineNotLinked):
			writeError(w, http.StatusConflict, "prescription has no medicine_id")
			return
		default:
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}

	writeJSON(w, http.StatusCreated, event)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func (h *Handler) preflight(ctx context.Context, w http.ResponseWriter, r *http.Request, action string) (security.Subject, bool) {
	if !h.guardrails.Ready() {
		writeError(w, http.StatusInternalServerError, "security guardrails are not configured")
		return security.Subject{}, false
	}
	if err := h.guardrails.ChannelGuard.ValidateSource(ctx, r); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: action, Result: "deny", Details: "channel validation failed: " + err.Error()})
		writeError(w, http.StatusForbidden, "untrusted channel")
		return security.Subject{}, false
	}
	subject, err := h.guardrails.Authn.Authenticate(ctx, r)
	if err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: action, Result: "deny", Details: "authentication failed: " + err.Error()})
		writeError(w, http.StatusUnauthorized, "authentication failed")
		return security.Subject{}, false
	}
	if err := h.guardrails.Authz.Authorize(ctx, subject, action); err != nil {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: action, Result: "deny", Details: "authorization failed: " + err.Error()})
		writeError(w, http.StatusForbidden, "access denied")
		return security.Subject{}, false
	}
	requestID := strings.TrimSpace(r.Header.Get("X-Request-ID"))
	if requestID == "" {
		writeError(w, http.StatusUnauthorized, "missing request id")
		return security.Subject{}, false
	}
	if h.isReplay(requestID) {
		_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: action, Result: "deny", Details: "replay detected"})
		writeError(w, http.StatusForbidden, "replay detected")
		return security.Subject{}, false
	}
	_ = h.guardrails.Audit.WriteEvent(ctx, security.AuditEvent{Service: "pharmacy", Action: action, Result: "allow", Details: "subject=" + subject.ID})
	return subject, true
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
