package security

import (
	"context"
	"net/http"
	"testing"
)

type okAuthn struct{}
type okAuthz struct{}
type okAudit struct{}
type okIntegrity struct{}
type okChannel struct{}

func (okAuthn) Authenticate(context.Context, *http.Request) (Subject, error) {
	return Subject{ID: "1", Roles: []string{"doctor"}}, nil
}
func (okAuthz) Authorize(context.Context, Subject, Action) error { return nil }
func (okAudit) WriteEvent(context.Context, AuditEvent) error      { return nil }
func (okIntegrity) VerifyPayload(context.Context, []byte, string) error {
	return nil
}
func (okChannel) ValidateSource(context.Context, *http.Request) error { return nil }

func TestGuardrailsReady(t *testing.T) {
	g := Guardrails{}
	if g.Ready() {
		t.Fatalf("expected guardrails to be not ready")
	}

	g.Authn = okAuthn{}
	g.Authz = okAuthz{}
	g.Audit = okAudit{}
	g.Integrity = okIntegrity{}
	g.Channel = okChannel{}
	if !g.Ready() {
		t.Fatalf("expected guardrails to be ready")
	}
}
