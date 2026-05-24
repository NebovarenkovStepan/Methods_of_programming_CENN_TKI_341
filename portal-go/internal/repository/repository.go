package repository

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"portal-go/internal/models"
	"portal-go/internal/security"
)

type userRecord struct {
	patientID  *int64
	speciality *string
}

type Repository struct {
	mu sync.Mutex

	nextPatientID       int64
	nextCardID          int64
	nextAppointmentID   int64
	nextInvestigationID int64
	nextPrescriptionID  int64

	users map[int64]userRecord
	logs  []security.AuditEvent
}

func NewInMemory() *Repository {
	doctor := "Терапевт"
	admin := "Администратор"
	return &Repository{
		nextPatientID:       0,
		nextCardID:          0,
		nextAppointmentID:   0,
		nextInvestigationID: 0,
		nextPrescriptionID:  0,
		users: map[int64]userRecord{
			123: {speciality: &doctor},
			7:   {speciality: &admin},
		},
		logs: make([]security.AuditEvent, 0),
	}
}

func (r *Repository) CreatePatient(_ context.Context, p models.Patient) (models.Patient, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.nextPatientID++
	p.ID = r.nextPatientID
	return p, nil
}

func (r *Repository) CreateCard(_ context.Context, c models.Card) (models.Card, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.nextCardID++
	c.ID = r.nextCardID
	c.DateOfVisit = time.Now().UTC()
	return c, nil
}

func (r *Repository) CreateAppointment(_ context.Context, a models.Appointment) (models.Appointment, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.nextAppointmentID++
	a.ID = r.nextAppointmentID
	a.Status = "CONFIRMED"
	a.CreatedAt = time.Now().UTC()
	return a, nil
}

func (r *Repository) CreateInvestigation(_ context.Context, inv models.LaboratoryInvestigation) (models.LaboratoryInvestigation, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.nextInvestigationID++
	inv.ID = r.nextInvestigationID
	inv.Status = "ORDERED"
	inv.DateOrdered = time.Now().UTC()
	return inv, nil
}

func (r *Repository) CreatePrescription(_ context.Context, p models.Prescription) (models.Prescription, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.nextPrescriptionID++
	p.ID = r.nextPrescriptionID
	p.Status = "CREATED"
	p.DateOfReceipt = time.Now().UTC()
	return p, nil
}

func (r *Repository) ResolveSubject(_ context.Context, subjectID string) (security.Subject, error) {
	id, err := strconv.ParseInt(subjectID, 10, 64)
	if err != nil {
		return security.Subject{}, fmt.Errorf("invalid subject id: %w", err)
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	rec, ok := r.users[id]
	if !ok {
		return security.Subject{}, fmt.Errorf("subject not found")
	}
	roles := []string{"guest"}
	if rec.patientID != nil {
		roles = []string{"patient"}
	} else if rec.speciality != nil {
		roles = []string{roleFromSpeciality(*rec.speciality)}
	}
	return security.Subject{ID: subjectID, Roles: roles}, nil
}

func (r *Repository) WriteSecurityLog(_ context.Context, event security.AuditEvent) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.logs = append(r.logs, event)
	return nil
}

func roleFromSpeciality(speciality string) string {
	normalized := strings.ToLower(strings.TrimSpace(speciality))
	switch {
	case strings.Contains(normalized, "админ"):
		return "admin"
	case strings.Contains(normalized, "терап"), strings.Contains(normalized, "врач"), strings.Contains(normalized, "doctor"):
		return "doctor"
	case strings.Contains(normalized, "регист"):
		return "registrar"
	default:
		return "staff"
	}
}
