package security

import (
	"context"
	"net/http"
)

type Subject struct {
	ID    string
	Roles []string
}

type Action struct {
	Name      string
	Resource  string
	PatientID int64
}

const (
	ActionCreatePatient       = "patient:create"
	ActionCreateCard          = "card:create"
	ActionCreateAppointment   = "appointment:create"
	ActionCreateInvestigation = "investigation:create"
	ActionCreatePrescription  = "prescription:create"
)

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
	Authorize(ctx context.Context, subject Subject, action Action) error
}

type Auditor interface {
	WriteEvent(ctx context.Context, event AuditEvent) error
}

type IntegrityChecker interface {
	VerifyPayload(ctx context.Context, payload []byte, signature string) error
}

type ChannelGuard interface {
	ValidateSource(ctx context.Context, r *http.Request) error
}

type Guardrails struct {
	Authn     Authenticator
	Authz     Authorizer
	Audit     Auditor
	Integrity IntegrityChecker
	Channel   ChannelGuard
}

func (g Guardrails) Ready() bool {
	return g.Authn != nil &&
		g.Authz != nil &&
		g.Audit != nil &&
		g.Integrity != nil &&
		g.Channel != nil
}
