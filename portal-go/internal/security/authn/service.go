package authn

import (
	"context"
	"errors"
	"net/http"
	"strings"

	"portal-go/internal/security"
)

type SubjectResolver interface {
	ResolveSubject(ctx context.Context, subjectID string) (security.Subject, error)
}

type Service struct {
	requireIdentity bool
	resolver        SubjectResolver
}

func New(requireIdentity bool, resolver SubjectResolver) *Service {
	return &Service{requireIdentity: requireIdentity, resolver: resolver}
}

func (s *Service) Authenticate(ctx context.Context, r *http.Request) (security.Subject, error) {
	subjectID := strings.TrimSpace(r.Header.Get("X-Subject-ID"))
	rolesRaw := strings.TrimSpace(r.Header.Get("X-Roles"))

	if subjectID == "" {
		if s.requireIdentity {
			return security.Subject{}, errors.New("missing X-Subject-ID")
		}
		subjectID = "anonymous"
	}

	if s.resolver != nil && subjectID != "anonymous" {
		resolved, err := s.resolver.ResolveSubject(ctx, subjectID)
		if err != nil {
			return security.Subject{}, err
		}
		if len(resolved.Roles) == 0 {
			resolved.Roles = []string{"guest"}
		}
		return resolved, nil
	}

	roles := []string{"guest"}
	if rolesRaw != "" {
		parts := strings.Split(rolesRaw, ",")
		roles = roles[:0]
		for _, part := range parts {
			role := strings.TrimSpace(part)
			if role != "" {
				roles = append(roles, role)
			}
		}
		if len(roles) == 0 {
			roles = []string{"guest"}
		}
	}

	return security.Subject{ID: subjectID, Roles: roles}, nil
}
