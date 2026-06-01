package main

import (
	"log"
	"net/http"
	"os"
	"strings"

	"pharmacy-go/internal/ais"
	"pharmacy-go/internal/api"
	"pharmacy-go/internal/repository"
	"pharmacy-go/internal/scanner"
	"pharmacy-go/internal/security"
	"pharmacy-go/internal/security/audit"
	"pharmacy-go/internal/security/authn"
	"pharmacy-go/internal/security/authz"
	"pharmacy-go/internal/security/channelguard"
	"pharmacy-go/internal/security/identitycheck"
	"pharmacy-go/internal/security/integrity"
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
	aisService := ais.New(repo)
	scannerService := scanner.New(repo)
	integritySecret := loadIntegritySecret()
	if integritySecret == "" {
		log.Fatalf("INTEGRITY_SECRET is required in strict mode")
	}
	guardrails := security.Guardrails{
		Authn:        authn.New(true, repo),
		Authz:        authz.New(true),
		Audit:        audit.New(repo),
		Integrity:    integrity.New(true, integritySecret),
		Identity:     identitycheck.New(true),
		ChannelGuard: channelguard.New(true),
	}
	handler := api.NewHandlerWithGuardrails(aisService, scannerService, guardrails)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	log.Printf("pharmacy-go started on :%s", port)
	if err := http.ListenAndServe(":"+port, handler.Router()); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
