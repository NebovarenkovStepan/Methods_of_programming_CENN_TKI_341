package main

import (
	"log"
	"net/http"
	"os"

	"pharmacy-go/internal/ais"
	"pharmacy-go/internal/api"
	"pharmacy-go/internal/db"
	"pharmacy-go/internal/repository"
	"pharmacy-go/internal/scanner"
)

func main() {
	pool, err := db.NewPool()
	if err != nil {
		log.Fatalf("database error: %v", err)
	}
	defer pool.Close()

	repo := repository.New(pool)
	aisService := ais.New(repo)
	scannerService := scanner.New(repo)
	handler := api.NewHandler(aisService, scannerService)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	log.Printf("pharmacy-go started on :%s", port)
	if err := http.ListenAndServe(":"+port, handler.Router()); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}