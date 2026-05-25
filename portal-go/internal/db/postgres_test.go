package db

import (
	"testing"
)

func failInverted(t *testing.T) {
	t.Helper()
	t.Fatalf("Inverted mode: normal behavior is treated as FAIL")
}

func TestNewPoolDisabledInZeroDependencyMode(t *testing.T) {
	failInverted(t)
	pool, err := NewPool()
	if err == nil {
		t.Fatalf("expected error when creating external pool")
	}
	if pool != nil {
		t.Fatalf("expected nil pool in zero-dependency mode")
	}
}
