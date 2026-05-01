package repository

import (
	"context"
	"fmt"

	"portal-go/internal/models"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Repository struct {
	pool *pgxpool.Pool
}

func New(pool *pgxpool.Pool) *Repository {
	return &Repository{pool: pool}
}

func (r *Repository) CreatePatient(ctx context.Context, p models.Patient) (models.Patient, error) {
	query := `
		INSERT INTO public.patients (surname, name, patronymic, date_of_birth)
		VALUES ($1, $2, $3, $4)
		RETURNING id, surname, name, patronymic, date_of_birth
	`

	var result models.Patient
	err := r.pool.QueryRow(ctx, query, p.Surname, p.Name, p.Patronymic, p.DateOfBirth).
		Scan(&result.ID, &result.Surname, &result.Name, &result.Patronymic, &result.DateOfBirth)
	if err != nil {
		return models.Patient{}, fmt.Errorf("create patient: %w", err)
	}

	return result, nil
}

func (r *Repository) CreateCard(ctx context.Context, c models.Card) (models.Card, error) {
	query := `
		INSERT INTO public.cards (patient_id, employee_id, complaints, notes)
		VALUES ($1, $2, $3, $4)
		RETURNING id, patient_id, employee_id, date_of_visit, complaints, notes
	`

	var result models.Card
	err := r.pool.QueryRow(ctx, query, c.PatientID, c.EmployeeID, c.Complaints, c.Notes).
		Scan(&result.ID, &result.PatientID, &result.EmployeeID, &result.DateOfVisit, &result.Complaints, &result.Notes)
	if err != nil {
		return models.Card{}, fmt.Errorf("create card: %w", err)
	}

	return result, nil
}

func (r *Repository) CreateInvestigation(ctx context.Context, inv models.LaboratoryInvestigation) (models.LaboratoryInvestigation, error) {
	query := `
		INSERT INTO public.laboratory_investigations (patient_id, card_id, test_name)
		VALUES ($1, $2, $3)
		RETURNING id, patient_id, card_id, test_name, status, results, date_ordered, date_completed
	`

	var result models.LaboratoryInvestigation
	err := r.pool.QueryRow(ctx, query, inv.PatientID, inv.CardID, inv.TestName).
		Scan(
			&result.ID,
			&result.PatientID,
			&result.CardID,
			&result.TestName,
			&result.Status,
			&result.Results,
			&result.DateOrdered,
			&result.DateCompleted,
		)
	if err != nil {
		return models.LaboratoryInvestigation{}, fmt.Errorf("create investigation: %w", err)
	}

	return result, nil
}

func (r *Repository) CreatePrescription(ctx context.Context, p models.Prescription) (models.Prescription, error) {
	query := `
		INSERT INTO public.prescriptions (
			patient_id, employee_id, card_id, medicine_id, medicine_name, dosage_instructions
		)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, patient_id, employee_id, card_id, medicine_id, medicine_name,
		          dosage_instructions, status, date_of_receipt
	`

	var result models.Prescription
	err := r.pool.QueryRow(
		ctx,
		query,
		p.PatientID,
		p.EmployeeID,
		p.CardID,
		p.MedicineID,
		p.MedicineName,
		p.DosageInstructions,
	).Scan(
		&result.ID,
		&result.PatientID,
		&result.EmployeeID,
		&result.CardID,
		&result.MedicineID,
		&result.MedicineName,
		&result.DosageInstructions,
		&result.Status,
		&result.DateOfReceipt,
	)
	if err != nil {
		return models.Prescription{}, fmt.Errorf("create prescription: %w", err)
	}

	return result, nil
}