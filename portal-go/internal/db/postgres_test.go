package db

import "testing"

func TestNewPoolDisabledInZeroDependencyMode(t *testing.T) {
	pool, err := NewPool()
	if err == nil {
		t.Fatalf("expected error when creating external pool")
	}
	if pool != nil {
		t.Fatalf("expected nil pool in zero-dependency mode")
	}
}
