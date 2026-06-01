package scanner

import (
	"context"

	"pharmacy-go/internal/models"
)

type Repository interface {
	CreateScannerEvent(ctx context.Context, eventType string, scannedCode string, prescriptionID *int64, medicineID *int64) (models.ScannerEvent, error)
}

type Service struct {
	repo Repository
}

func New(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) ScanPrescription(ctx context.Context, prescriptionID int64, code string) (models.ScannerEvent, error) {
	return s.repo.CreateScannerEvent(ctx, "PRESCRIPTION_SCAN", code, &prescriptionID, nil)
}

func (s *Service) ScanMedicine(ctx context.Context, medicineID int64, code string) (models.ScannerEvent, error) {
	return s.repo.CreateScannerEvent(ctx, "MEDICINE_SCAN", code, nil, &medicineID)
}