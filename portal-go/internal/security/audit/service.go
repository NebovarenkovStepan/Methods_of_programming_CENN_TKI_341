package audit

import (
	"context"
	"log"

	"portal-go/internal/security"
)

type LogWriter interface {
	WriteSecurityLog(ctx context.Context, event security.AuditEvent) error
}

type Service struct {
	writer LogWriter
}

func New(writer LogWriter) *Service {
	return &Service{writer: writer}
}

func (s *Service) WriteEvent(ctx context.Context, event security.AuditEvent) error {
	if s.writer != nil {
		return s.writer.WriteSecurityLog(ctx, event)
	}
	log.Printf("audit service=%s action=%s result=%s details=%s", event.Service, event.Action, event.Result, event.Details)
	return nil
}
