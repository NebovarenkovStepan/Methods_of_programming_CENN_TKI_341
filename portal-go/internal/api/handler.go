package api

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"portal-go/internal/models"

	"github.com/go-chi/chi/v5"
)

type Repository interface {
	CreatePatient(ctx context.Context, p models.Patient) (models.Patient, error)
	CreateCard(ctx context.Context, c models.Card) (models.Card, error)
	CreateAppointment(ctx context.Context, a models.Appointment) (models.Appointment, error)
	CreateInvestigation(ctx context.Context, inv models.LaboratoryInvestigation) (models.LaboratoryInvestigation, error)
	CreatePrescription(ctx context.Context, p models.Prescription) (models.Prescription, error)
}

type Handler struct {
	repo Repository
}

func NewHandler(repo Repository) *Handler {
	return &Handler{repo: repo}
}

func (h *Handler) Router() http.Handler {
	r := chi.NewRouter()

	r.Get("/health", h.Health)

	r.Post("/patients", h.CreatePatient)
	r.Post("/cards", h.CreateCard)
	r.Post("/appointments", h.CreateAppointment)
	r.Post("/investigations", h.CreateInvestigation)
	r.Post("/prescriptions", h.CreatePrescription)

	return r
}

func (h *Handler) Health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

func (h *Handler) CreatePatient(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	patient, err := h.repo.CreatePatient(ctx, models.Patient{
		Surname:     req.Surname,
		Name:        req.Name,
		Patronymic:  req.Patronymic,
		DateOfBirth: dob,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, patient)
}

func (h *Handler) CreateCard(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	card, err := h.repo.CreateCard(ctx, models.Card{
		PatientID:  req.PatientID,
		EmployeeID: req.EmployeeID,
		Complaints: req.Complaints,
		Notes:      req.Notes,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, card)
}

func (h *Handler) CreateAppointment(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	appointment, err := h.repo.CreateAppointment(ctx, models.Appointment{
		PatientID:   req.PatientID,
		EmployeeID:  req.EmployeeID,
		ScheduledAt: scheduledAt,
		Reason:      req.Reason,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, appointment)
}

func (h *Handler) CreateInvestigation(w http.ResponseWriter, r *http.Request) {
	var req struct {
		PatientID int64  `json:"patient_id"`
		CardID    int64  `json:"card_id"`
		TestName  string `json:"test_name"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	inv, err := h.repo.CreateInvestigation(ctx, models.LaboratoryInvestigation{
		PatientID: req.PatientID,
		CardID:    req.CardID,
		TestName:  req.TestName,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, inv)
}

func (h *Handler) CreatePrescription(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	prescription, err := h.repo.CreatePrescription(ctx, models.Prescription{
		PatientID:          req.PatientID,
		EmployeeID:         req.EmployeeID,
		CardID:             req.CardID,
		MedicineID:         req.MedicineID,
		MedicineName:       req.MedicineName,
		DosageInstructions: req.DosageInstructions,
	})
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
