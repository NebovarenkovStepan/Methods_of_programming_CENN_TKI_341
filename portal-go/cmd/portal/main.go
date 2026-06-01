package main

import (
	"log"
	"net/http"
	"os"
	"strings"

	"portal-go/internal/api"
	"portal-go/internal/repository"
	"portal-go/internal/security"
	"portal-go/internal/security/audit"
	"portal-go/internal/security/authn"
	"portal-go/internal/security/authz"
	"portal-go/internal/security/channelguard"
	"portal-go/internal/security/integrity"
)

func loadIntegritySecret() string {
	if path := strings.TrimSpace(os.Getenv("INTEGRITY_SECRET_FILE")); path != "" {
		data, err := os.ReadFile(path)
		if err != nil {
			log.Fatalf("failed to read INTEGRITY_SECRET_FILE: %v", err)
		}
		return strings.TrimSpace(string(data))
	}
	return strings.TrimSpace(os.Getenv("INTEGRITY_SECRET"))
}

func main() {
	repo := repository.NewInMemory()
	integritySecret := loadIntegritySecret()
	if integritySecret == "" {
		log.Fatalf("INTEGRITY_SECRET is required in strict mode")
	}
	guardrails := security.Guardrails{
		Authn:     authn.New(true, repo),
		Authz:     authz.New(true),
		Audit:     audit.New(repo),
		Integrity: integrity.New(true, integritySecret),
		Channel:   channelguard.New(true),
	}
	handler := api.NewHandlerWithGuardrails(repo, guardrails)

	addr := os.Getenv("PORT")
	if addr == "" {
		addr = "8080"
	}

	log.Printf("portal-go started on :%s", addr)
	if err := http.ListenAndServe(":"+addr, handler.Router()); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
