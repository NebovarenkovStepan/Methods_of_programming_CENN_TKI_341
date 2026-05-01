package api

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"time"

	"pharmacy-go/internal/ais"
	"pharmacy-go/internal/repository"
	"pharmacy-go/internal/scanner"

	"github.com/go-chi/chi/v5"
)

type Handler struct {
	aisService     *ais.Service
	scannerService *scanner.Service
}

func NewHandler(aisService *ais.Service, scannerService *scanner.Service) *Handler {
	return &Handler{
		aisService:     aisService,
		scannerService: scannerService,
	}
}

func (h *Handler) Router() http.Handler {
	r := chi.NewRouter()

	r.Get("/health", h.Health)

	r.Get("/prescriptions/{id}", h.GetPrescription)
	r.Post("/scanner/prescription", h.ScanPrescription)
	r.Post("/scanner/medicine", h.ScanMedicine)
	r.Post("/dispense", h.DispensePrescription)

	return r
}

func (h *Handler) Health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handler) GetPrescription(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.ParseInt(chi.URLParam(r, "id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid prescription id")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

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
	var req struct {
		PrescriptionID int64  `json:"prescription_id"`
		Code           string `json:"code"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	event, err := h.scannerService.ScanPrescription(ctx, req.PrescriptionID, req.Code)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, event)
}

func (h *Handler) ScanMedicine(w http.ResponseWriter, r *http.Request) {
	var req struct {
		MedicineID int64  `json:"medicine_id"`
		Code       string `json:"code"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	event, err := h.scannerService.ScanMedicine(ctx, req.MedicineID, req.Code)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusCreated, event)
}

func (h *Handler) DispensePrescription(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

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