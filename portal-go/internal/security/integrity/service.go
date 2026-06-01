package integrity

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
)

type Service struct {
	enforce bool
	secret  []byte
}

func New(enforce bool, secret string) *Service {
	return &Service{enforce: enforce, secret: []byte(secret)}
}

func (s *Service) VerifyPayload(_ context.Context, payload []byte, signature string) error {
	if !s.enforce {
		return nil
	}
	if len(s.secret) == 0 {
		return errors.New("integrity secret is not configured")
	}
	if signature == "" {
		return errors.New("missing signature")
	}
	mac := hmac.New(sha256.New, s.secret)
	mac.Write(payload)
	expected := mac.Sum(nil)
	provided, err := hex.DecodeString(signature)
	if err != nil {
		return errors.New("invalid signature format")
	}
	if !hmac.Equal(expected, provided) {
		return errors.New("signature mismatch")
	}
	return nil
}
