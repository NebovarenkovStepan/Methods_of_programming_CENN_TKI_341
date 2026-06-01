package identitycheck

import (
	"context"
	"errors"

	"pharmacy-go/internal/security"
)

type Service struct {
	enforce bool
}

func New(enforce bool) *Service {
	return &Service{enforce: enforce}
}

func (s *Service) VerifyPatientForDispense(_ context.Context, subject security.Subject, details security.DispenseContext) error {
	if !s.enforce {
		return nil
	}
	if details.PrescriptionID <= 0 || details.MedicineID <= 0 {
		return errors.New("invalid dispense context")
	}
	if subject.ID == "" || subject.ID == "anonymous" {
		return errors.New("anonymous subject is not allowed")
	}
	return nil
}
