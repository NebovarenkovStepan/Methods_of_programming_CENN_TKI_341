package authz

import (
	"context"
	"errors"

	"portal-go/internal/security"
)

type Service struct {
	enforce bool
	policy  map[string]map[string]struct{}
}

func New(enforce bool) *Service {
	return &Service{
		enforce: enforce,
		policy: map[string]map[string]struct{}{
			"patient:create":       set("admin", "doctor", "registrar"),
			"card:create":          set("doctor"),
			"appointment:create":   set("admin", "doctor", "registrar"),
			"investigation:create": set("doctor"),
			"prescription:create":  set("doctor"),
		},
	}
}

func (s *Service) Authorize(_ context.Context, subject security.Subject, action security.Action) error {
	if !s.enforce {
		return nil
	}
	allowed, ok := s.policy[action.Name]
	if !ok {
		return errors.New("action is not allowed by policy")
	}
	for _, role := range subject.Roles {
		if _, exists := allowed[role]; exists {
			return nil
		}
	}
	return errors.New("access denied")
}

func set(roles ...string) map[string]struct{} {
	out := make(map[string]struct{}, len(roles))
	for _, role := range roles {
		out[role] = struct{}{}
	}
	return out
}
