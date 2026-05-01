package models

import "time"

type Prescription struct {
	ID                 int64     `json:"id"`
	PatientID          int64     `json:"patient_id"`
	EmployeeID         int64     `json:"employee_id"`
	CardID             int64     `json:"card_id"`
	MedicineID         *int64    `json:"medicine_id,omitempty"`
	MedicineName       string    `json:"medicine_name"`
	DosageInstructions string    `json:"dosage_instructions"`
	Status             string    `json:"status"`
	DateOfReceipt      time.Time `json:"date_of_receipt"`
}

type Medicine struct {
	ID           int64   `json:"id"`
	Name         string  `json:"name"`
	Form         *string `json:"form,omitempty"`
	Dosage       *string `json:"dosage,omitempty"`
	Manufacturer *string `json:"manufacturer,omitempty"`
	Description  *string `json:"description,omitempty"`
}

type WarehouseStock struct {
	ID         int64     `json:"id"`
	MedicineID int64     `json:"medicine_id"`
	Quantity   int       `json:"quantity"`
	UpdatedAt  time.Time `json:"updated_at"`
}

type ScannerEvent struct {
	ID             int64      `json:"id"`
	EventType      string     `json:"event_type"`
	ScannedCode    string     `json:"scanned_code"`
	PrescriptionID *int64     `json:"prescription_id,omitempty"`
	MedicineID     *int64     `json:"medicine_id,omitempty"`
	ScannedAt      time.Time  `json:"scanned_at"`
}

type DispenseEvent struct {
	ID             int64     `json:"id"`
	PrescriptionID int64     `json:"prescription_id"`
	MedicineID     int64     `json:"medicine_id"`
	Quantity       int       `json:"quantity"`
	DispensedAt    time.Time `json:"dispensed_at"`
}