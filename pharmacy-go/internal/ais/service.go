package ais

import (
	"context"

	"pharmacy-go/internal/models"
)

type Repository interface {
	GetPrescriptionByID(ctx context.Context, id int64) (models.Prescription, error)
	DispensePrescription(ctx context.Context, prescriptionID int64, quantity int) (models.DispenseEvent, error)
}

type Service struct {
	repo Repository
}

func New(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) GetPrescription(ctx context.Context, id int64) (models.Prescription, error) {
	return s.repo.GetPrescriptionByID(ctx, id)
}

func (s *Service) Dispense(ctx context.Context, prescriptionID int64, quantity int) (models.DispenseEvent, error) {
	return s.repo.DispensePrescription(ctx, prescriptionID, quantity)
}