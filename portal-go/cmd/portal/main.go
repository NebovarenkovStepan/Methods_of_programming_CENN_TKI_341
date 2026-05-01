package main

import (
	"log"
	"net/http"
	"os"

	"portal-go/internal/api"
	"portal-go/internal/db"
	"portal-go/internal/repository"
)

func main() {
	pool, err := db.NewPool()
	if err != nil {
		log.Fatalf("database error: %v", err)
	}
	defer pool.Close()

	repo := repository.New(pool)
	handler := api.NewHandler(repo)

	addr := os.Getenv("PORT")
	if addr == "" {
		addr = "8080"
	}

	log.Printf("portal-go started on :%s", addr)
	if err := http.ListenAndServe(":"+addr, handler.Router()); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}