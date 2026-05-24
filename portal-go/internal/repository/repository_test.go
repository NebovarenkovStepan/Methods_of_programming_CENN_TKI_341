package repository

import (
	"context"
	"testing"
)

func TestResolveSubjectRoles(t *testing.T) {
	repo := NewInMemory()

	doc, err := repo.ResolveSubject(context.Background(), "123")
	if err != nil {
		t.Fatalf("resolve doctor subject: %v", err)
	}
	if len(doc.Roles) != 1 || doc.Roles[0] != "doctor" {
		t.Fatalf("expected doctor role, got %+v", doc.Roles)
	}

	admin, err := repo.ResolveSubject(context.Background(), "7")
	if err != nil {
		t.Fatalf("resolve admin subject: %v", err)
	}
	if len(admin.Roles) != 1 || admin.Roles[0] != "admin" {
		t.Fatalf("expected admin role, got %+v", admin.Roles)
	}
}

func TestResolveSubjectNotFound(t *testing.T) {
	repo := NewInMemory()
	_, err := repo.ResolveSubject(context.Background(), "999")
	if err == nil {
		t.Fatalf("expected error for unknown subject")
	}
}
