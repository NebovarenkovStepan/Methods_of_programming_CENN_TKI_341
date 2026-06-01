package channelguard

import (
	"context"
	"errors"
	"net/http"
	"strings"
)

type Service struct {
	enforce bool
}

func New(enforce bool) *Service {
	return &Service{enforce: enforce}
}

func (s *Service) ValidateSource(_ context.Context, r *http.Request) error {
	if !s.enforce {
		return nil
	}
	if strings.TrimSpace(r.Header.Get("X-Trusted-Channel")) != "vpn" {
		return errors.New("untrusted source channel")
	}
	return nil
}
