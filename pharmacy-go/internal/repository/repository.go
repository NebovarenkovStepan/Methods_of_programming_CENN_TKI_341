package repository

import (
	"context"
	"errors"
	"fmt"
	"pharmacy-go/internal/models"
	"pharmacy-go/internal/security"
	"strconv"
	"strings"
	"sync"
	"time"
)

var ErrNotFound = errors.New("not found")
var ErrInsufficientStock = errors.New("insufficient stock")
var ErrPrescriptionAlreadyDispensed = errors.New("prescription already dispensed")
var ErrPrescriptionCancelled = errors.New("prescription cancelled")
var ErrMedicineNotLinked = errors.New("prescription has no medicine_id")

type userRecord struct {
	patientID  *int64
	speciality *string
}

type Repository struct {
	mu sync.Mutex

	prescriptions map[int64]models.Prescription
	scannerEvents []models.ScannerEvent
	dispenseEvents []models.DispenseEvent
	stock map[int64]int
	users map[int64]userRecord
	logs []security.AuditEvent
}

func NewInMemory() *Repository {
	admin := "Администратор"
	return &Repository{
		prescriptions: make(map[int64]models.Prescription),
		scannerEvents: make([]models.ScannerEvent, 0),
		dispenseEvents: make([]models.DispenseEvent, 0),
		stock: make(map[int64]int),
		users: map[int64]userRecord{7: {speciality: &admin}},
		logs: make([]security.AuditEvent, 0),
	}
}

func (r *Repository) GetPrescriptionByID(_ context.Context, id int64) (models.Prescription, error) {
	r.mu.Lock(); defer r.mu.Unlock()
	p, ok := r.prescriptions[id]
	if !ok { return models.Prescription{}, ErrNotFound }
	return p, nil
}

func (r *Repository) CreateScannerEvent(_ context.Context, eventType string, scannedCode string, prescriptionID *int64, medicineID *int64) (models.ScannerEvent, error) {
	r.mu.Lock(); defer r.mu.Unlock()
	e := models.ScannerEvent{ID: int64(len(r.scannerEvents)+1), EventType: eventType, ScannedCode: scannedCode, PrescriptionID: prescriptionID, MedicineID: medicineID, ScannedAt: time.Now().UTC()}
	r.scannerEvents = append(r.scannerEvents, e)
	return e, nil
}

func (r *Repository) DispensePrescription(_ context.Context, prescriptionID int64, quantity int) (models.DispenseEvent, error) {
	r.mu.Lock(); defer r.mu.Unlock()
	p, ok := r.prescriptions[prescriptionID]
	if !ok { return models.DispenseEvent{}, ErrNotFound }
	if p.Status == "DISPENSED" { return models.DispenseEvent{}, ErrPrescriptionAlreadyDispensed }
	if p.Status == "CANCELLED" { return models.DispenseEvent{}, ErrPrescriptionCancelled }
	if p.MedicineID == nil { return models.DispenseEvent{}, ErrMedicineNotLinked }
	current := r.stock[*p.MedicineID]
	if current < quantity { return models.DispenseEvent{}, ErrInsufficientStock }
	r.stock[*p.MedicineID] = current - quantity
	p.Status = "DISPENSED"
	r.prescriptions[prescriptionID] = p
	e := models.DispenseEvent{ID:int64(len(r.dispenseEvents)+1), PrescriptionID:prescriptionID, MedicineID:*p.MedicineID, Quantity:quantity, DispensedAt:time.Now().UTC()}
	r.dispenseEvents = append(r.dispenseEvents, e)
	return e, nil
}

func (r *Repository) ResolveSubject(_ context.Context, subjectID string) (security.Subject, error) {
	id, err := strconv.ParseInt(subjectID, 10, 64)
	if err != nil { return security.Subject{}, fmt.Errorf("invalid subject id: %w", err) }
	r.mu.Lock(); defer r.mu.Unlock()
	rec, ok := r.users[id]
	if !ok { return security.Subject{}, fmt.Errorf("subject not found") }
	roles := []string{"guest"}
	if rec.patientID != nil { roles = []string{"patient"} } else if rec.speciality != nil { roles = []string{roleFromSpeciality(*rec.speciality)} }
	return security.Subject{ID:subjectID, Roles:roles}, nil
}

func (r *Repository) WriteSecurityLog(_ context.Context, event security.AuditEvent) error {
	r.mu.Lock(); defer r.mu.Unlock()
	r.logs = append(r.logs, event)
	return nil
}

func roleFromSpeciality(speciality string) string {
	n := strings.ToLower(strings.TrimSpace(speciality))
	switch {
	case strings.Contains(n, "админ"):
		return "admin"
	case strings.Contains(n, "фарм"), strings.Contains(n, "pharmac"):
		return "pharmacist"
	case strings.Contains(n, "врач"), strings.Contains(n, "doctor"):
		return "doctor"
	default:
		return "staff"
	}
}
