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

func (s *Service) verifyCode(code string) error {
	if !s.enforce {
		return nil
	}
	if len(s.secret) == 0 {
		return errors.New("integrity secret is not configured")
	}
	parts := []byte(code)
	if len(parts) == 0 {
		return errors.New("empty code")
	}
	// code format: payloadHex.signatureHex
	sep := -1
	for i, ch := range parts {
		if ch == '.' {
			sep = i
			break
		}
	}
	if sep <= 0 || sep >= len(parts)-1 {
		return errors.New("invalid signed code format")
	}
	payloadHex := string(parts[:sep])
	sigHex := string(parts[sep+1:])
	payload, err := hex.DecodeString(payloadHex)
	if err != nil {
		return errors.New("invalid code payload format")
	}
	provided, err := hex.DecodeString(sigHex)
	if err != nil {
		return errors.New("invalid code signature format")
	}
	mac := hmac.New(sha256.New, s.secret)
	mac.Write(payload)
	if !hmac.Equal(mac.Sum(nil), provided) {
		return errors.New("code signature mismatch")
	}
	return nil
}

func (s *Service) VerifyPrescriptionCode(_ context.Context, prescriptionID int64, code string) error {
	if s.enforce && prescriptionID <= 0 {
		return errors.New("invalid prescription id")
	}
	return s.verifyCode(code)
}

func (s *Service) VerifyMedicineCode(_ context.Context, medicineID int64, code string) error {
	if s.enforce && medicineID <= 0 {
		return errors.New("invalid medicine id")
	}
	return s.verifyCode(code)
}
