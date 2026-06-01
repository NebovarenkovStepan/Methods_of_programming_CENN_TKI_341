package db

import "fmt"

// Deprecated: zero-dependency slice does not use external DB drivers.
func NewPool() (any, error) {
	return nil, fmt.Errorf("external database drivers are disabled in zero-dependency mode")
}
