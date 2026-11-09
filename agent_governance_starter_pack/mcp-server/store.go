package main

import (
	"errors"
	"fmt"
	"sync"
)

// ErrNotFound is returned when an item ID is not in the store.
var ErrNotFound = errors.New("item not found")

// ErrBadStatus is returned when a status value is not allowed.
var ErrBadStatus = errors.New("status not allowed")

// allowedStatus holds the status values that update_status accepts.
var allowedStatus = map[string]bool{"open": true, "in_progress": true, "closed": true}

// Item is one work item in the sample data.
type Item struct {
	ID     string `json:"item_id"`
	Title  string `json:"title"`
	Status string `json:"status"`
}

// Store keeps the sample items in memory. A new Cloud Run revision starts
// with the seed data again. The "switch policy mode" runbook uses this.
type Store struct {
	mu    sync.Mutex
	items map[string]Item
}

// NewStore returns a store with the seed items.
func NewStore() *Store {
	seed := []Item{
		{ID: "ITEM-001", Title: "Replace the badge reader at gate 2", Status: "open"},
		{ID: "ITEM-002", Title: "Renew the TLS certificate for the intranet", Status: "in_progress"},
		{ID: "ITEM-003", Title: "Review the access list for the finance share", Status: "open"},
	}
	s := &Store{items: make(map[string]Item, len(seed))}
	for _, it := range seed {
		s.items[it.ID] = it
	}
	return s
}

// Get returns the item with the given ID.
func (s *Store) Get(id string) (Item, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	it, ok := s.items[id]
	if !ok {
		return Item{}, fmt.Errorf("%w: %s", ErrNotFound, id)
	}
	return it, nil
}

// Update sets the status of the item with the given ID.
func (s *Store) Update(id, status string) (Item, error) {
	if !allowedStatus[status] {
		return Item{}, fmt.Errorf("%w: %q (use open, in_progress, or closed)", ErrBadStatus, status)
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	it, ok := s.items[id]
	if !ok {
		return Item{}, fmt.Errorf("%w: %s", ErrNotFound, id)
	}
	it.Status = status
	s.items[id] = it
	return it, nil
}
