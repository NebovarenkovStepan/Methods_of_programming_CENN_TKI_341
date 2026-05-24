package security

import (
	"context"
	"net/http"
)

type Subject struct {
	ID    string
	Roles []string
}

const (
	ActionReadPrescription  = "prescription:read"
	ActionScanPrescription  = "scanner:prescription"
	ActionScanMedicine      = "scanner:medicine"
	ActionDispensePrescription = "prescription:dispense"
)

type DispenseContext struct {
	PrescriptionID int64
	PatientID      int64
	MedicineID     int64
}

type AuditEvent struct {
	Service string
	Action  string
	Result  string
	Details string
}

type Authenticator interface {
	Authenticate(ctx context.Context, r *http.Request) (Subject, error)
}

type Authorizer interface {
	Authorize(ctx context.Context, subject Subject, action string) error
}

type Auditor interface {
	WriteEvent(ctx context.Context, event AuditEvent) error
}

type IntegrityChecker interface {
	VerifyPrescriptionCode(ctx context.Context, prescriptionID int64, code string) error
	VerifyMedicineCode(ctx context.Context, medicineID int64, code string) error
}

type IdentityChecker interface {
	VerifyPatientForDispense(ctx context.Context, subject Subject, details DispenseContext) error
}

type ChannelGuard interface {
	ValidateSource(ctx context.Context, r *http.Request) error
}

type Guardrails struct {
	Authn        Authenticator
	Authz        Authorizer
	Audit        Auditor
	Integrity    IntegrityChecker
	Identity     IdentityChecker
	ChannelGuard ChannelGuard
}

func (g Guardrails) Ready() bool {
	return g.Authn != nil &&
		g.Authz != nil &&
		g.Audit != nil &&
		g.Integrity != nil &&
		g.Identity != nil &&
		g.ChannelGuard != nil
}
