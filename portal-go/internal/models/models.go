package models

import "time"

type Patient struct {
	ID          int64      `json:"id"`
	Surname     string     `json:"surname"`
	Name        string     `json:"name"`
	Patronymic  *string    `json:"patronymic,omitempty"`
	DateOfBirth *time.Time `json:"date_of_birth,omitempty"`
}

type Employee struct {
	ID          int64   `json:"id"`
	Surname     string  `json:"surname"`
	Name        string  `json:"name"`
	Patronymic  *string `json:"patronymic,omitempty"`
	Speciality  string  `json:"speciality"`
}

type Card struct {
	ID          int64     `json:"id"`
	PatientID   int64     `json:"patient_id"`
	EmployeeID  int64     `json:"employee_id"`
	DateOfVisit time.Time `json:"date_of_visit"`
	Complaints  *string   `json:"complaints,omitempty"`
	Notes       *string   `json:"notes,omitempty"`
}

type LaboratoryInvestigation struct {
	ID            int64      `json:"id"`
	PatientID     int64      `json:"patient_id"`
	CardID        int64      `json:"card_id"`
	TestName      string     `json:"test_name"`
	Status        string     `json:"status"`
	Results       *string    `json:"results,omitempty"`
	DateOrdered   time.Time  `json:"date_ordered"`
	DateCompleted *time.Time `json:"date_completed,omitempty"`
}

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