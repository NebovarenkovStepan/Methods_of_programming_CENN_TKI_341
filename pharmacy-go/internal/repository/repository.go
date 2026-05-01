package repository
import (

	"context"
	"errors"
	"fmt"
	"pharmacy-go/internal/models"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

)

var ErrNotFound = errors.New("not found")

var ErrInsufficientStock = errors.New("insufficient stock")

var ErrPrescriptionAlreadyDispensed = errors.New("prescription already dispensed")

var ErrPrescriptionCancelled = errors.New("prescription cancelled")

var ErrMedicineNotLinked = errors.New("prescription has no medicine_id")

type Repository struct {

	pool *pgxpool.Pool

}

func New(pool *pgxpool.Pool) *Repository {

	return &Repository{pool: pool}

}

func (r *Repository) GetPrescriptionByID(ctx context.Context, id int64) (models.Prescription, error) {

	query := `
		SELECT id, patient_id, employee_id, card_id, medicine_id, medicine_name,
		       dosage_instructions, status, date_of_receipt
		FROM public.prescriptions
		WHERE id = $1
	`
	var p models.Prescription
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&p.ID,
		&p.PatientID,
		&p.EmployeeID,
		&p.CardID,
		&p.MedicineID,
		&p.MedicineName,
		&p.DosageInstructions,
		&p.Status,
		&p.DateOfReceipt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return models.Prescription{}, ErrNotFound
		}
		return models.Prescription{}, fmt.Errorf("get prescription: %w", err)
	}
	return p, nil

}

func (r *Repository) CreateScannerEvent(

	ctx context.Context,
	eventType string,
	scannedCode string,
	prescriptionID *int64,
	medicineID *int64,

) (models.ScannerEvent, error) {

	query := `
		INSERT INTO public.scanner_events (event_type, scanned_code, prescription_id, medicine_id)
		VALUES ($1, $2, $3, $4)
		RETURNING id, event_type, scanned_code, prescription_id, medicine_id, scanned_at
	`
	var event models.ScannerEvent
	err := r.pool.QueryRow(ctx, query, eventType, scannedCode, prescriptionID, medicineID).
		Scan(
			&event.ID,
			&event.EventType,
			&event.ScannedCode,
			&event.PrescriptionID,
			&event.MedicineID,
			&event.ScannedAt,
		)
	if err != nil {
		return models.ScannerEvent{}, fmt.Errorf("create scanner event: %w", err)
	}
	return event, nil

}

func (r *Repository) DispensePrescription(

	ctx context.Context,
	prescriptionID int64,
	quantity int,

) (models.DispenseEvent, error) {

	tx, err := r.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return models.DispenseEvent{}, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx)
	var prescriptionStatus string
	var medicineID *int64
	err = tx.QueryRow(ctx, `
		SELECT status, medicine_id
		FROM public.prescriptions
		WHERE id = $1
		FOR UPDATE
	`, prescriptionID).Scan(&prescriptionStatus, &medicineID)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return models.DispenseEvent{}, ErrNotFound
		}
		return models.DispenseEvent{}, fmt.Errorf("load prescription: %w", err)
	}
	if prescriptionStatus == "DISPENSED" {
		return models.DispenseEvent{}, ErrPrescriptionAlreadyDispensed
	}
	if prescriptionStatus == "CANCELLED" {
		return models.DispenseEvent{}, ErrPrescriptionCancelled
	}
	if medicineID == nil {
		return models.DispenseEvent{}, ErrMedicineNotLinked
	}
	var stockID int64
	var currentQty int
	err = tx.QueryRow(ctx, `
		SELECT id, quantity
		FROM public.warehouse_stock
		WHERE medicine_id = $1
		FOR UPDATE
	`, *medicineID).Scan(&stockID, &currentQty)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return models.DispenseEvent{}, ErrInsufficientStock
		}
		return models.DispenseEvent{}, fmt.Errorf("load stock: %w", err)
	}
	if currentQty < quantity {
		return models.DispenseEvent{}, ErrInsufficientStock
	}
	_, err = tx.Exec(ctx, `
		UPDATE public.warehouse_stock
		SET quantity = quantity - $1,
		    updated_at = CURRENT_TIMESTAMP
		WHERE id = $2
	`, quantity, stockID)
	if err != nil {
		return models.DispenseEvent{}, fmt.Errorf("update stock: %w", err)
	}
	_, err = tx.Exec(ctx, `
		UPDATE public.prescriptions
		SET status = 'DISPENSED'
		WHERE id = $1
	`, prescriptionID)
	if err != nil {
		return models.DispenseEvent{}, fmt.Errorf("update prescription status: %w", err)
	}
	var event models.DispenseEvent
	err = tx.QueryRow(ctx, `
		INSERT INTO public.dispense_events (prescription_id, medicine_id, quantity)
		VALUES ($1, $2, $3)
		RETURNING id, prescription_id, medicine_id, quantity, dispensed_at
	`, prescriptionID, *medicineID, quantity).Scan(
		&event.ID,
		&event.PrescriptionID,
		&event.MedicineID,
		&event.Quantity,
		&event.DispensedAt,
	)
	if err != nil {
		return models.DispenseEvent{}, fmt.Errorf("insert dispense event: %w", err)
	}
	if err := tx.Commit(ctx); err != nil {
		return models.DispenseEvent{}, fmt.Errorf("commit tx: %w", err)
	}
	return event, nil

}